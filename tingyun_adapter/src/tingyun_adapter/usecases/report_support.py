from __future__ import annotations

from datetime import datetime
from typing import Any, Iterable, Optional
from urllib.parse import urlsplit

from tingyun_adapter.domain.models.common import AnalysisContext


def console_base_url(adapter: Any, context: AnalysisContext) -> str:
    settings = getattr(adapter, "settings", None)
    configured = getattr(settings, "console_public_base_url", None) if settings else None
    return str(configured or context.base_url or "").rstrip("/")


def make_console_link(
    adapter: Any,
    context: AnalysisContext,
    *,
    page_type: str,
    label: str,
    why_relevant: str,
    suggested_report_section: str,
    navigation_path: list[str],
    suggested_filters: Optional[dict[str, Any]] = None,
    target_ref: Optional[dict[str, Any]] = None,
    deep_link_status: str = "fallback_root_navigation",
    url: Optional[str] = None,
) -> dict[str, Any]:
    base = console_base_url(adapter, context)
    resolved = resolve_console_link(
        adapter,
        context,
        page_type=page_type,
        navigation_path=navigation_path,
        suggested_filters=suggested_filters or {},
        target_ref=target_ref or {},
        fallback_url=url or base or None,
    )
    return {
        "page_type": page_type,
        "url": resolved["url"],
        "url_status": resolved["url_status"],
        "direct_url": resolved["direct_url"],
        "fallback_url": resolved["fallback_url"],
        "label": label,
        "why_relevant": why_relevant,
        "suggested_report_section": suggested_report_section,
        "deep_link_status": resolved["deep_link_status"] or deep_link_status,
        "navigation_path": navigation_path,
        "suggested_filters": suggested_filters or {},
        "target_ref": target_ref or {},
        "url_source": resolved["url_source"],
        "related_console_urls": resolved["related_console_urls"],
        "page_context_summary": resolved["page_context_summary"],
    }


def make_screenshot_hint(
    *,
    title: str,
    page_type: str,
    url: str,
    recommended_capture: list[str],
    recommended_annotations: list[str],
    usage_in_report: str,
    suggested_report_section: Optional[str] = None,
    target_ref: Optional[dict[str, Any]] = None,
    priority: str = "medium",
) -> dict[str, Any]:
    return {
        "title": title,
        "page_type": page_type,
        "url": url,
        "recommended_capture": recommended_capture,
        "recommended_annotations": recommended_annotations,
        "usage_in_report": usage_in_report,
        "suggested_report_section": suggested_report_section,
        "target_ref": target_ref or {},
        "priority": priority,
    }


def make_metric_semantic(
    *,
    metric_name: str,
    subject_type: str,
    subject_key: str,
    aggregation: str,
    unit: str,
    time_window: str,
    sample_scope: str,
    confidence: str = "medium",
) -> dict[str, Any]:
    return {
        "metric_name": metric_name,
        "subject_type": subject_type,
        "subject_key": subject_key,
        "aggregation": aggregation,
        "unit": unit,
        "time_window": time_window,
        "sample_scope": sample_scope,
        "confidence": confidence,
    }


def default_coverage_boundary(
    adapter: Any,
    *,
    page_status: str = "partial",
    page_reason: str = "page_experience_pack relies on backend/topology evidence unless dedicated page-side inputs are available.",
    available_page_evidence: Optional[list[str]] = None,
    missing_page_evidence: Optional[list[str]] = None,
) -> dict[str, Any]:
    settings = getattr(adapter, "settings", None)
    has_console_public_base = bool(getattr(settings, "console_public_base_url", None)) if settings else False
    return {
        "page_experience": {
            "status": page_status,
            "reason": page_reason,
            "available_evidence": available_page_evidence
            or [
                "user_to_application_topology",
                "representative_request_urls",
                "external_dependency_edges",
                "backend_action_and_trace_correlation",
            ],
            "missing_evidence": missing_page_evidence
            or [
                "slow_pages",
                "slow_requests",
                "js_errors",
                "browser_breakdown",
                "geo_breakdown",
            ],
        },
        "console_linking": {
            "status": "configured_public_console_url" if has_console_public_base else "base_url_fallback",
            "reason": "Links now prefer captured real page URLs when page context exists; otherwise they still fall back to console root URLs plus navigation hints.",
            "available_evidence": [
                "clickable_console_root_url",
                "captured_page_url_candidates",
                "page_type",
                "navigation_path",
                "suggested_filters",
            ],
            "missing_evidence": [
                "fully_stable_spa_deep_link_for_every_page",
            ],
        },
    }


def time_window_text(context: AnalysisContext) -> str:
    return f"{context.time_window.end_time} / {context.time_window.period_minutes}m window"


def apply_report_support(
    payload: Any,
    *,
    page_links: Optional[list[dict[str, Any]]] = None,
    screenshot_hints: Optional[list[dict[str, Any]]] = None,
    metric_semantics: Optional[list[dict[str, Any]]] = None,
    coverage_boundary: Optional[dict[str, Any]] = None,
    evidence_linkage: Optional[dict[str, Any]] = None,
) -> Any:
    links = page_links or []
    hints = screenshot_hints or []
    semantics = metric_semantics or []
    related_urls: list[str] = []
    for item in links:
        url = item.get("url")
        if url:
            related_urls.append(url)
        related_urls.extend([str(link) for link in item.get("related_console_urls") or [] if link])
    if hasattr(payload, "page_links"):
        payload.page_links = links
    if hasattr(payload, "primary_console_url"):
        payload.primary_console_url = related_urls[0] if related_urls else None
    if hasattr(payload, "related_console_urls"):
        payload.related_console_urls = _unique_preserve_order(related_urls)
    if hasattr(payload, "screenshot_hints"):
        payload.screenshot_hints = hints
    if hasattr(payload, "metric_semantics"):
        payload.metric_semantics = semantics
    if hasattr(payload, "coverage_boundary"):
        payload.coverage_boundary = coverage_boundary or {}
    if hasattr(payload, "evidence_linkage"):
        payload.evidence_linkage = evidence_linkage or {}
    return payload


def collect_screenshot_cards(*groups: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for group in groups:
        for item in group or []:
            key = (str(item.get("title") or ""), str(item.get("url") or ""))
            if key in seen:
                continue
            seen.add(key)
            cards.append(item)
    return cards


def _unique_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def resolve_console_link(
    adapter: Any,
    context: AnalysisContext,
    *,
    page_type: str,
    navigation_path: list[str],
    suggested_filters: dict[str, Any],
    target_ref: dict[str, Any],
    fallback_url: Optional[str],
) -> dict[str, Any]:
    candidates = _collect_page_context_candidates(adapter, context, page_type=page_type, target_ref=target_ref)
    selected = candidates[0] if candidates else None
    direct_url = selected["url"] if selected else None
    url_source = selected["source"] if selected else ("fallback_root_navigation" if fallback_url else "unknown")
    url_status = "direct" if direct_url else ("navigation_only" if fallback_url else "unavailable")
    final_url = direct_url or fallback_url
    related_urls = _unique_preserve_order(
        [item["url"] for item in candidates if item.get("url") and item.get("url") != direct_url]
        + ([fallback_url] if fallback_url and fallback_url != direct_url else [])
    )
    summary = {
        "selection_rule": "object_match>url_source_priority>page_quality>recency",
        "candidate_count": len(candidates),
        "selected_source": url_source,
        "matched_relative_paths": _unique_preserve_order([str(item.get("relative_path") or "") for item in candidates if item.get("relative_path")])[:5],
    }
    if selected:
        summary["selected_seen_at"] = selected.get("seen_at")
        summary["selected_page_title"] = selected.get("page_title")
    return {
        "url": final_url,
        "url_status": url_status,
        "direct_url": direct_url,
        "fallback_url": fallback_url,
        "url_source": url_source,
        "related_console_urls": related_urls,
        "page_context_summary": summary if candidates else {},
        "deep_link_status": "captured_page_context" if direct_url else ("fallback_root_navigation" if fallback_url else "unavailable"),
        "navigation_path": navigation_path,
        "suggested_filters": suggested_filters,
    }


def _collect_page_context_candidates(adapter: Any, context: AnalysisContext, *, page_type: str, target_ref: dict[str, Any]) -> list[dict[str, Any]]:
    repo = getattr(adapter, "captured_api", None)
    if repo is None:
        return []
    records = repo.iter_page_context_records()
    if not records:
        return []

    base = console_base_url(adapter, context)
    target_tokens = _target_match_tokens(context, target_ref)
    candidates: list[dict[str, Any]] = []
    for record in records:
        page_context = record.get("page_context") or {}
        candidate = _page_context_candidate_variants(page_context)
        for source, url in candidate:
            score = _candidate_score(
                url=url,
                source=source,
                record=record,
                page_context=page_context,
                target_tokens=target_tokens,
                base_url=base,
                page_type=page_type,
            )
            if score is None:
                continue
            candidates.append(
                {
                    "url": url,
                    "source": source,
                    "score": score,
                    "relative_path": record.get("relative_path"),
                    "seen_at": record.get("seen_at") or page_context.get("request_timestamp"),
                    "page_title": page_context.get("page_title"),
                }
            )

    candidates.sort(
        key=lambda item: (
            item.get("score", 0),
            _timestamp_sort_key(item.get("seen_at")),
            item.get("url") or "",
        ),
        reverse=True,
    )

    deduped: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    for item in candidates:
        url = str(item.get("url") or "")
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        deduped.append(item)
    return deduped


def _page_context_candidate_variants(page_context: dict[str, Any]) -> list[tuple[str, str]]:
    variants: list[tuple[str, str]] = []
    for source in ("captured_page_url", "document_url", "frame_url"):
        value = page_context.get(source)
        if isinstance(value, str) and value.strip():
            variants.append((source, value.strip()))
    return variants


def _target_match_tokens(context: AnalysisContext, target_ref: dict[str, Any]) -> dict[str, list[str]]:
    tokens: dict[str, list[str]] = {
        "biz_system_id": [str(context.biz_system_id)],
    }
    for key, value in (target_ref or {}).items():
        if value is None or key == "kind":
            continue
        if isinstance(value, list):
            values = [str(item) for item in value if item is not None]
        else:
            values = [str(value)]
        tokens[str(key)] = values
    return tokens


def _candidate_score(
    *,
    url: str,
    source: str,
    record: dict[str, Any],
    page_context: dict[str, Any],
    target_tokens: dict[str, list[str]],
    base_url: str,
    page_type: str,
) -> Optional[int]:
    normalized_url = (url or "").strip()
    if not normalized_url or normalized_url in {"about:blank", "chrome://new-tab-page/"}:
        return None

    request_body = record.get("request_body") or {}
    request_query = record.get("request_query") or {}
    request_values = _flatten_request_values(request_body) | _flatten_request_values(request_query)
    match_score = _object_match_score(target_tokens, request_values)
    if record.get("match_scope") == "method_summary":
        match_score -= 15

    source_score = {
        "captured_page_url": 300,
        "document_url": 200,
        "frame_url": 100,
    }.get(source, 0)

    quality_score = 0
    if _looks_like_home_page(normalized_url, base_url):
        quality_score -= 150
    else:
        quality_score += 40
    if "#" in normalized_url or "?" in normalized_url:
        quality_score += 15
    title = str(page_context.get("page_title") or "")
    if title and page_type.replace("_", "").lower()[:8] in title.replace(" ", "").lower():
        quality_score += 10

    return match_score + source_score + quality_score


def _object_match_score(target_tokens: dict[str, list[str]], request_values: dict[str, set[str]]) -> int:
    alias_groups = {
        "biz_system_id": ["bizSystemId", "systemId", "systemIds"],
        "application_id": ["applicationId", "applicationIds"],
        "action_id": ["actionId", "actionIds"],
        "action_type": ["actionType", "actionTypes"],
        "trace_id_numeric": ["traceId", "traceIds"],
        "component_name": ["componentName", "name"],
        "component_subtype": ["componentSubtype"],
        "instance_id": ["instanceId", "instanceIds"],
        "node_id": ["nodeId"],
        "protocol": ["protocol"],
        "op_name": ["opName"],
    }
    score = 0
    for key, values in target_tokens.items():
        aliases = alias_groups.get(key, [key])
        request_pool: set[str] = set()
        for alias in aliases:
            request_pool.update(request_values.get(alias, set()))
            request_pool.update(request_values.get(_snake_to_camel(alias), set()))
            request_pool.update(request_values.get(_camel_to_snake(alias), set()))
        if not request_pool:
            continue
        if any(value in request_pool for value in values):
            if key.endswith("_id") or key in {"biz_system_id", "protocol", "node_id"}:
                score += 120
            else:
                score += 80
    return score


def _flatten_request_values(payload: Any) -> dict[str, set[str]]:
    values: dict[str, set[str]] = {}
    if not isinstance(payload, dict):
        return values
    for key, raw_value in payload.items():
        bucket = values.setdefault(str(key), set())
        if isinstance(raw_value, list):
            for item in raw_value:
                if item is not None:
                    bucket.add(str(item))
        elif raw_value is not None:
            bucket.add(str(raw_value))
    return values


def _looks_like_home_page(url: str, base_url: str) -> bool:
    parsed = urlsplit(url)
    if not parsed.scheme or not parsed.netloc:
        return True
    path = parsed.path.rstrip("/")
    if parsed.fragment or parsed.query:
        return False
    if not path:
        return True
    if url.rstrip("/") == base_url.rstrip("/"):
        return True
    return path in {"", "/index", "/home", "/dashboard"}


def _timestamp_sort_key(value: Any) -> float:
    if not value:
        return float("-inf")
    text = str(value)
    try:
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        return datetime.fromisoformat(text).timestamp()
    except ValueError:
        return float("-inf")


def _snake_to_camel(value: str) -> str:
    parts = value.split("_")
    return parts[0] + "".join(part.capitalize() for part in parts[1:])


def _camel_to_snake(value: str) -> str:
    result = []
    for char in value:
        if char.isupper():
            result.append("_")
            result.append(char.lower())
        else:
            result.append(char)
    return "".join(result).lstrip("_")
