from __future__ import annotations

from tingyun_adapter.clients.application_client import ApplicationClient
from tingyun_adapter.clients.connection_client import ConnectionClient
from tingyun_adapter.clients.database_client import DatabaseClient
from tingyun_adapter.clients.graph_client import GraphClient
from tingyun_adapter.clients.health_client import HealthClient
from tingyun_adapter.clients.logtrace_client import LogTraceClient
from tingyun_adapter.clients.nosql_client import NoSQLClient
from tingyun_adapter.clients.trace_client import TraceClient
from tingyun_adapter.clients.webaction_client import WebActionClient
from tingyun_adapter.config.settings import AdapterSettings
from tingyun_adapter.domain.models.common import AnalysisContext, TimeWindow
from tingyun_adapter.sources.captured_api_repository import CapturedApiRepository
from tingyun_adapter.usecases.builders import (
    build_action_hotspot_pack,
    build_report_fact_pack,
    build_system_snapshot,
    build_trace_case_pack,
)


class Adapter:
    def __init__(self, settings: AdapterSettings) -> None:
        self.settings = settings
        kwargs = {
            "base_url": settings.base_url,
            "token_env": settings.token_env,
            "lang": settings.lang,
            "timeout": settings.timeout_seconds,
        }
        self.application = ApplicationClient(**kwargs)
        self.webaction = WebActionClient(**kwargs)
        self.graph = GraphClient(**kwargs)
        self.trace = TraceClient(**kwargs)
        self.database = DatabaseClient(**kwargs)
        self.nosql = NoSQLClient(**kwargs)
        self.connection = ConnectionClient(**kwargs)
        self.health = HealthClient(**kwargs)
        self.logtrace = LogTraceClient(**kwargs)
        self.captured_api: CapturedApiRepository | None = None
        if settings.captured_api_dir:
            self.captured_api = CapturedApiRepository(settings.captured_api_dir)

    @classmethod
    def from_env(cls, **overrides) -> "Adapter":
        settings = AdapterSettings.from_env()
        merged = AdapterSettings(
            base_url=overrides.get("base_url", settings.base_url),
            token_env=overrides.get("token_env", settings.token_env),
            lang=overrides.get("lang", settings.lang),
            timezone=overrides.get("timezone", settings.timezone),
            timeout_seconds=overrides.get("timeout_seconds", settings.timeout_seconds),
            captured_api_dir=overrides.get("captured_api_dir", settings.captured_api_dir),
        )
        return cls(merged)

    def build_context(self, *, biz_system_id: int, end_time: str, period_minutes: int) -> AnalysisContext:
        return AnalysisContext(
            base_url=self.settings.base_url,
            biz_system_id=biz_system_id,
            time_window=TimeWindow(end_time=end_time, period_minutes=period_minutes),
            lang=self.settings.lang,
            timezone=self.settings.timezone,
        )

    def build_system_snapshot(self, context: AnalysisContext, *, source_mode: str = "auto"):
        return build_system_snapshot(self, context, source_mode=source_mode)

    def build_action_hotspot_pack(self, context: AnalysisContext, *, source_mode: str = "auto"):
        return build_action_hotspot_pack(self, context, source_mode=source_mode)

    def build_trace_case_pack(self, context: AnalysisContext, *, source_mode: str = "auto"):
        return build_trace_case_pack(self, context, source_mode=source_mode)

    def build_report_fact_pack(self, context: AnalysisContext, *, source_mode: str = "auto"):
        return build_report_fact_pack(self, context, source_mode=source_mode)
