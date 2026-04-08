from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from math import ceil
from typing import Any, Optional

from tingyun_adapter.domain.models.common import AnalysisContext, TimeWindow


@dataclass(frozen=True)
class PoolLimits:
    collection_limit: int
    ranking_limit: int
    deep_dive_limit: int


@dataclass(frozen=True)
class TimeStrategy:
    mode: str = "single_window"
    shard_count: int = 1
    shard_minutes: Optional[int] = None
    short_window_minutes: Optional[int] = None
    comparison_mode: str = "none"
    degrade_mode: str = "none"


DEFAULT_POOL_LIMITS: dict[str, PoolLimits] = {
    "hotspots": PoolLimits(collection_limit=40, ranking_limit=12, deep_dive_limit=5),
    "slow_sql": PoolLimits(collection_limit=50, ranking_limit=12, deep_dive_limit=6),
    "external_dependencies": PoolLimits(collection_limit=24, ranking_limit=10, deep_dive_limit=6),
    "report_targets": PoolLimits(collection_limit=24, ranking_limit=10, deep_dive_limit=6),
}


def context_signature(context: AnalysisContext) -> tuple[Any, ...]:
    return (
        context.biz_system_id,
        context.time_window.end_time,
        context.time_window.period_minutes,
        context.lang,
        context.timezone,
    )


@dataclass
class BuildSession:
    context: AnalysisContext
    source_mode: str = "auto"
    memo: dict[str, Any] = field(default_factory=dict)
    metrics: dict[str, int] = field(
        default_factory=lambda: {
            "upstream_call_count": 0,
            "cache_hit_count": 0,
        }
    )
    candidate_registry: list[dict[str, Any]] = field(default_factory=list)
    deep_dive_budget: dict[str, int] = field(default_factory=dict)
    time_strategy: TimeStrategy = field(init=False)

    def __post_init__(self) -> None:
        self.time_strategy = choose_time_strategy(self.context)
        for name, limits in DEFAULT_POOL_LIMITS.items():
            self.deep_dive_budget.setdefault(name, limits.deep_dive_limit)

    def _memo_key(self, namespace: str, key: Any) -> str:
        return f"{namespace}:{repr(key)}"

    def lookup(self, namespace: str, key: Any) -> tuple[bool, Any]:
        memo_key = self._memo_key(namespace, key)
        if memo_key not in self.memo:
            return False, None
        self.metrics["cache_hit_count"] += 1
        return True, self.memo[memo_key]

    def store(self, namespace: str, key: Any, value: Any) -> Any:
        memo_key = self._memo_key(namespace, key)
        self.memo[memo_key] = value
        self.metrics["upstream_call_count"] += 1
        return value

    def snapshot_counters(self) -> tuple[int, int]:
        return (
            self.metrics["upstream_call_count"],
            self.metrics["cache_hit_count"],
        )

    def counter_delta(self, snapshot: tuple[int, int]) -> dict[str, int]:
        return {
            "upstream_call_count": self.metrics["upstream_call_count"] - snapshot[0],
            "cache_hit_count": self.metrics["cache_hit_count"] - snapshot[1],
        }

    def get_pool_limits(self, pool_name: str, *, fallback_limit: Optional[int] = None) -> PoolLimits:
        base = DEFAULT_POOL_LIMITS.get(pool_name, PoolLimits(collection_limit=10, ranking_limit=5, deep_dive_limit=3))
        if fallback_limit is None or fallback_limit <= 0:
            return base
        ranking_limit = min(base.ranking_limit, max(1, fallback_limit))
        collection_limit = max(base.collection_limit, fallback_limit)
        deep_dive_limit = min(base.deep_dive_limit, ranking_limit)
        return PoolLimits(
            collection_limit=collection_limit,
            ranking_limit=ranking_limit,
            deep_dive_limit=deep_dive_limit,
        )

    def consume_deep_dive(self, pool_name: str, requested: int) -> int:
        if requested <= 0:
            return 0
        available = self.deep_dive_budget.setdefault(
            pool_name,
            self.get_pool_limits(pool_name).deep_dive_limit,
        )
        granted = min(max(0, requested), max(0, available))
        self.deep_dive_budget[pool_name] = max(0, available - granted)
        return granted

    def attach_candidate_registry(self, items: list[dict[str, Any]]) -> None:
        self.candidate_registry = list(items)

    def build_stats(
        self,
        snapshot: tuple[int, int],
        *,
        collection_count: int,
        ranking_count: int,
        deep_dive_count: int,
        shard_count: Optional[int] = None,
        comparison_mode: Optional[str] = None,
        degrade_mode: Optional[str] = None,
        extra: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        stats = self.counter_delta(snapshot)
        stats.update(
            {
                "collection_count": collection_count,
                "ranking_count": ranking_count,
                "deep_dive_count": deep_dive_count,
                "shard_count": shard_count if shard_count is not None else self.time_strategy.shard_count,
                "degrade_mode": degrade_mode or self.time_strategy.degrade_mode,
            }
        )
        if comparison_mode is not None:
            stats["comparison_mode"] = comparison_mode
        if extra:
            stats.update(extra)
        return stats


def choose_time_strategy(context: AnalysisContext) -> TimeStrategy:
    period_minutes = max(1, int(context.time_window.period_minutes))
    day_minutes = 24 * 60
    if period_minutes >= 90 * day_minutes:
        shard_minutes = 14 * day_minutes
        return TimeStrategy(
            mode="auto_sharded_summary",
            shard_count=max(1, ceil(period_minutes / shard_minutes)),
            shard_minutes=shard_minutes,
            short_window_minutes=30 * day_minutes,
            comparison_mode="summary",
            degrade_mode="long_window_short_comparison",
        )
    if period_minutes >= 60 * day_minutes:
        shard_minutes = 14 * day_minutes
        return TimeStrategy(
            mode="auto_sharded_summary",
            shard_count=max(1, ceil(period_minutes / shard_minutes)),
            shard_minutes=shard_minutes,
            short_window_minutes=30 * day_minutes,
            comparison_mode="summary",
            degrade_mode="long_window_short_comparison",
        )
    if period_minutes >= 30 * day_minutes:
        shard_minutes = 7 * day_minutes
        return TimeStrategy(
            mode="auto_sharded_summary",
            shard_count=max(1, ceil(period_minutes / shard_minutes)),
            shard_minutes=shard_minutes,
            short_window_minutes=14 * day_minutes,
            comparison_mode="summary",
            degrade_mode="medium_window_short_comparison",
        )
    return TimeStrategy()


def shard_contexts(context: AnalysisContext, strategy: Optional[TimeStrategy] = None) -> list[AnalysisContext]:
    strategy = strategy or choose_time_strategy(context)
    if strategy.shard_count <= 1 or not strategy.shard_minutes:
        return [context]
    end_time = parse_time_window_end(context.time_window.end_time)
    if end_time is None:
        return [context]
    contexts: list[AnalysisContext] = []
    remaining = int(context.time_window.period_minutes)
    current_end = end_time
    for _index in range(strategy.shard_count):
        shard_minutes = min(remaining, strategy.shard_minutes)
        contexts.append(
            shift_context_window(
                context,
                end_time=current_end,
                period_minutes=shard_minutes,
            )
        )
        remaining -= shard_minutes
        current_end = current_end - timedelta(minutes=shard_minutes)
        if remaining <= 0:
            break
    contexts.reverse()
    return contexts


def comparison_contexts(
    context: AnalysisContext,
    strategy: Optional[TimeStrategy] = None,
    *,
    requested_mode: str = "summary",
) -> tuple[Optional[AnalysisContext], Optional[AnalysisContext], str]:
    strategy = strategy or choose_time_strategy(context)
    if requested_mode == "none":
        return None, None, "none"
    comparison_minutes = strategy.short_window_minutes if requested_mode == "summary" and strategy.short_window_minutes else context.time_window.period_minutes
    current_end = parse_time_window_end(context.time_window.end_time)
    if current_end is None:
        return None, None, requested_mode
    current_context = shift_context_window(context, end_time=current_end, period_minutes=comparison_minutes)
    previous_context = shift_context_window(
        context,
        end_time=current_end - timedelta(minutes=comparison_minutes),
        period_minutes=comparison_minutes,
    )
    resolved_mode = requested_mode
    if strategy.short_window_minutes and comparison_minutes == strategy.short_window_minutes:
        resolved_mode = "summary"
    elif requested_mode != "none":
        resolved_mode = "full"
    return current_context, previous_context, resolved_mode


def shift_context_window(context: AnalysisContext, *, end_time: datetime, period_minutes: int) -> AnalysisContext:
    return AnalysisContext(
        base_url=context.base_url,
        biz_system_id=context.biz_system_id,
        time_window=TimeWindow(end_time=end_time.strftime("%Y-%m-%d %H:%M"), period_minutes=period_minutes),
        auth=context.auth,
        lang=context.lang,
        timezone=context.timezone,
    )


def parse_time_window_end(value: str) -> Optional[datetime]:
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None
