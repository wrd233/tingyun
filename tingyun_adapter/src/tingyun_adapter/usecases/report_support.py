from __future__ import annotations

from typing import Any, Iterable, Optional

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
    return {
        "page_type": page_type,
        "url": url or base,
        "label": label,
        "why_relevant": why_relevant,
        "suggested_report_section": suggested_report_section,
        "deep_link_status": deep_link_status,
        "navigation_path": navigation_path,
        "suggested_filters": suggested_filters or {},
        "target_ref": target_ref or {},
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
            "reason": "Direct SPA route templates are not fully reverse-engineered; links currently prefer root console URLs plus navigation hints.",
            "available_evidence": [
                "clickable_console_root_url",
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
    related_urls = [item.get("url") for item in links if item.get("url")]
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
