from __future__ import annotations

import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Any, Optional

from tingyun_adapter.domain.enums import PackType
from tingyun_adapter.domain.models.common import AnalysisContext, DatabaseComponentRef, Evidence, PackEnvelope, WarningMessage, dataclass_to_dict
from tingyun_adapter.domain.models.packs import (
    BusinessLabelsPackPayload,
    ComparisonSignalsPackPayload,
    ImpactSignalsPackPayload,
    PageExperiencePackPayload,
    ScreenshotIndexPackPayload,
    StabilitySignalsPackPayload,
)
from tingyun_adapter.usecases.analysis_rules import (
    BACKGROUND_KEYWORDS,
    COMPARISON_THRESHOLDS,
    CORE_BUSINESS_KEYWORDS,
    ENTRY_KEYWORDS,
    FRAMEWORK_NOISE_KEYWORDS,
    IMPACT_WEIGHTS,
    MAINTENANCE_KEYWORDS,
    SUPPORT_KEYWORDS,
)
from tingyun_adapter.usecases.builders import (
    _coerce_evidence_list,
    _evidence,
    _numeric,
    _pack,
    build_action_fact_sheet,
    build_action_hotspot_pack,
    build_system_snapshot,
)
from tingyun_adapter.usecases.extended_builders import build_sql_fact_sheet
from tingyun_adapter.usecases.extended_builders import (
    build_external_dependency_pack,
    build_slow_sql_pack,
    build_topology_dependency_pack,
)
from tingyun_adapter.usecases.report_support import (
    apply_report_support,
    collect_screenshot_cards,
    default_coverage_boundary,
    make_console_link,
    make_metric_semantic,
    make_screenshot_hint,
    time_window_text,
)


def build_business_labels_pack(
    adapter: Any,
    context: AnalysisContext,
    *,
    source_mode: str = "auto",
    limit: int = 10,
) -> PackEnvelope:
    warnings: list[WarningMessage] = []
    missing_inputs: list[str] = []

    hotspots = build_action_hotspot_pack(adapter, context, source_mode=source_mode)
    topology = build_topology_dependency_pack(adapter, context, source_mode=source_mode)
    external = build_external_dependency_pack(adapter, context, source_mode=source_mode)

    warnings.extend(hotspots.meta.warnings)
    warnings.extend(topology.meta.warnings)
    warnings.extend(external.meta.warnings)

    hotspot_payload = hotspots.to_dict()["payload"]
    topology_payload = topology.to_dict()["payload"]
    external_payload = external.to_dict()["payload"]

    hotspot_rows = (hotspot_payload.get("hotspots") or [])[:limit]
    dependencies = external_payload.get("external_dependencies") or []
    topology_dependencies = topology_payload.get("dependencies") or []
    if not dependencies:
        missing_inputs.append("external_dependency_objects")
    if not topology_dependencies:
        missing_inputs.append("topology_user_edges")
    missing_inputs.append("page_objects")

    duplicate_action_names = Counter((row.get("action") or {}).get("name") for row in hotspot_rows if (row.get("action") or {}).get("name"))
    user_entry_apps = {edge.get("to") for edge in topology_dependencies if edge.get("from_category") == "user" and edge.get("to")}

    objects: list[dict[str, Any]] = []
    for row in hotspot_rows:
        action = row.get("action") or {}
        raw = row.get("raw") or {}
        name = str(action.get("name") or "")
        labels, label_groups, review_flags, derivation_notes = _derive_action_labels(name, raw, user_entry_apps)
        if duplicate_action_names.get(name, 0) > 1:
            review_flags.append("cross_application_name_reused")
        confidence = _label_confidence(labels, review_flags)
        objects.append(
            {
                "target_ref": _action_target_ref(action),
                "target_type": "action",
                "display_name": name,
                "target_metrics": dataclass_to_dict(action.get("metrics") or {}),
                "labels": labels,
                "label_groups": label_groups,
                "confidence": confidence,
                "source_basis": [
                    {"kind": "pack", "value": "action_hotspot_pack"},
                    {"kind": "rule", "value": "action_name_keyword_rules"},
                    {"kind": "rule", "value": "topology_user_entry_app_names"},
                ],
                "evidence_refs": ["action_list", "action_overview"],
                "review_flags": review_flags,
                "derivation_notes": derivation_notes,
            }
        )

    for dep in dependencies[:limit]:
        labels, label_groups, review_flags, derivation_notes = _derive_dependency_labels(dep, user_entry_apps)
        objects.append(
            {
                "target_ref": _dependency_target_ref(dep),
                "target_type": "external_dependency",
                "display_name": dep.get("node_id") or dep.get("protocol") or "external_dependency",
                "target_metrics": {
                    "response_time_ms": dep.get("response_time_ms"),
                    "error_rate": dep.get("error_rate"),
                    "throughput": dep.get("throughput"),
                    "link_count": dep.get("link_count"),
                },
                "labels": labels,
                "label_groups": label_groups,
                "confidence": _label_confidence(labels, review_flags),
                "source_basis": [
                    {"kind": "pack", "value": "external_dependency_pack"},
                    {"kind": "rule", "value": "dependency_protocol_and_upstream_rules"},
                ],
                "evidence_refs": ["biz_detail_graph", "graph_health"],
                "review_flags": review_flags,
                "derivation_notes": derivation_notes,
            }
        )

    payload = BusinessLabelsPackPayload(
        scope=_pack_scope(context, source_mode, limit),
        objects=objects,
        summaries=_label_summaries(objects),
        input_dependencies=["action_hotspot_pack", "topology_dependency_pack", "external_dependency_pack"],
        derivation_notes=[
            "Labels are lightweight heuristics derived from names, topology context, and external dependency structure.",
            "No final business criticality conclusion is made inside the adapter.",
        ],
        evidence=_merge_evidence(
            hotspot_payload.get("evidence", []),
            topology_payload.get("evidence", []),
            external_payload.get("evidence", []),
        ),
    )
    build_stats = {"object_count": len(objects), "action_count": len(hotspot_rows), "dependency_count": min(len(dependencies), limit)}
    return _pack(
        PackType.BUSINESS_LABELS.value,
        context,
        payload,
        evidence=_merge_evidence_objects(payload.evidence),
        warnings=warnings,
        source_mode=source_mode,
        missing_inputs=sorted(set(missing_inputs)),
        confidence_notes=["Rules are intentionally lightweight and designed for ranking support, not final business judgment."],
        build_stats=build_stats,
    )


def build_stability_signals_pack(
    adapter: Any,
    context: AnalysisContext,
    *,
    source_mode: str = "auto",
    limit: int = 10,
) -> PackEnvelope:
    warnings: list[WarningMessage] = []
    missing_inputs: list[str] = []

    hotspots = build_action_hotspot_pack(adapter, context, source_mode=source_mode)
    external = build_external_dependency_pack(adapter, context, source_mode=source_mode)
    slow_sql = build_slow_sql_pack(adapter, context, source_mode=source_mode, limit=limit)

    warnings.extend(hotspots.meta.warnings)
    warnings.extend(external.meta.warnings)
    warnings.extend(slow_sql.meta.warnings)

    hotspot_payload = hotspots.to_dict()["payload"]
    external_payload = external.to_dict()["payload"]
    sql_payload = slow_sql.to_dict()["payload"]

    hotspot_rows = (hotspot_payload.get("hotspots") or [])[:limit]
    action_name_counts = Counter((row.get("action") or {}).get("name") for row in hotspot_rows if (row.get("action") or {}).get("name"))

    objects: list[dict[str, Any]] = []
    for row in hotspot_rows:
        action = row.get("action") or {}
        fact = build_action_fact_sheet(
            adapter,
            context,
            source_mode=source_mode,
            action_ref=_action_ref_from_target(action),
            trace_limit=min(limit, 5),
        )
        warnings.extend(fact.meta.warnings)
        fact_payload = fact.to_dict()["payload"]
        trace_candidates = fact_payload.get("trace_candidates") or []
        timestamps = [item.get("timestamp") for item in trace_candidates if item.get("timestamp") is not None]
        if not timestamps:
            missing_inputs.append(f"trace_candidates:{action.get('id')}")
        repeatability_score = _repeatability_score(
            count=_numeric((action.get("metrics") or {}).get("count")),
            slow_count=_numeric((action.get("metrics") or {}).get("slow_count")),
            trace_count=len(trace_candidates),
        )
        spread_scope = _action_spread_scope(
            action_name=action.get("name"),
            instance_count=_numeric((fact_payload.get("overview") or {}).get("instanceCount")),
            duplicate_name_count=action_name_counts.get(action.get("name"), 0),
        )
        objects.append(
            {
                "target_ref": _action_target_ref(action),
                "target_type": "action",
                "display_name": action.get("name"),
                "metrics": dataclass_to_dict(action.get("metrics") or {}),
                "stability_class": _stability_class(repeatability_score),
                "repeatability_score": repeatability_score,
                "spread_scope": spread_scope,
                "time_distribution": _time_distribution(timestamps),
                "instance_distribution": {
                    "instance_count": (fact_payload.get("overview") or {}).get("instanceCount"),
                    "trace_candidate_count": len(trace_candidates),
                },
                "burstiness": _burstiness(
                    response_time_ms=_numeric((action.get("metrics") or {}).get("response_time_ms")),
                    count=_numeric((action.get("metrics") or {}).get("count")),
                    timestamps=timestamps,
                ),
                "confidence": "medium" if trace_candidates else "low",
                "source_basis": [
                    {"kind": "pack", "value": "action_hotspot_pack"},
                    {"kind": "pack", "value": "action_fact_sheet"},
                ],
                "evidence_refs": ["action_list", "action_fact_trace_candidates"],
                "review_flags": ["trace_candidates_missing"] if not trace_candidates else [],
            }
        )

    for dep in (external_payload.get("external_dependencies") or [])[:limit]:
        upstream_count = len(dep.get("upstream_nodes") or [])
        repeatability_score = _dependency_repeatability_score(dep)
        objects.append(
            {
                "target_ref": _dependency_target_ref(dep),
                "target_type": "external_dependency",
                "display_name": dep.get("node_id") or dep.get("protocol") or "external_dependency",
                "metrics": {
                    "response_time_ms": dep.get("response_time_ms"),
                    "error_rate": dep.get("error_rate"),
                    "throughput": dep.get("throughput"),
                    "upstream_count": upstream_count,
                },
                "stability_class": _stability_class(repeatability_score),
                "repeatability_score": repeatability_score,
                "spread_scope": _dependency_spread_scope(upstream_count),
                "time_distribution": "uniformly_distributed",
                "instance_distribution": {"upstream_count": upstream_count},
                "burstiness": "stable_bad" if _numeric(dep.get("response_time_ms")) and _numeric(dep.get("response_time_ms")) >= 1000 else "unstable_spiky",
                "confidence": "medium",
                "source_basis": [{"kind": "pack", "value": "external_dependency_pack"}],
                "evidence_refs": ["biz_detail_graph", "graph_health"],
                "review_flags": [],
            }
        )

    for sql_row in (sql_payload.get("top_sqls") or [])[:limit]:
        response_time_ms = _numeric(sql_row.get("response_time_ms") or sql_row.get("respTime"))
        count = _numeric(sql_row.get("count"))
        error_count = _numeric(sql_row.get("error_count") or sql_row.get("errorCount"))
        trace_count = _numeric(sql_row.get("traceCount"))
        repeatability_score = _repeatability_score(count=count, slow_count=error_count, trace_count=trace_count)
        objects.append(
            {
                "target_ref": _sql_target_ref(sql_row),
                "target_type": "sql",
                "display_name": _sql_display_name(sql_row),
                "metrics": {
                    "response_time_ms": response_time_ms,
                    "count": count,
                    "error_count": error_count,
                    "trace_count": trace_count,
                },
                "stability_class": _stability_class(repeatability_score),
                "repeatability_score": repeatability_score,
                "spread_scope": _sql_spread_scope(trace_count),
                "time_distribution": "uniformly_distributed",
                "instance_distribution": {"trace_count": trace_count},
                "burstiness": "stable_bad" if response_time_ms and response_time_ms >= 1000 else "unstable_spiky",
                "confidence": "medium",
                "source_basis": [{"kind": "pack", "value": "slow_sql_pack"}],
                "evidence_refs": ["database_analysis", "database_operate_analysis"],
                "review_flags": ["time_distribution_inferred"],
            }
        )

    payload = StabilitySignalsPackPayload(
        scope=_pack_scope(context, source_mode, limit),
        objects=objects,
        summaries=_stability_summaries(objects),
        input_dependencies=["action_hotspot_pack", "action_fact_sheet", "external_dependency_pack", "slow_sql_pack"],
        derivation_notes=[
            "Stability signals describe recurrence and spread, not final root cause.",
            "When trace timestamps are absent, time distribution falls back to a low-confidence heuristic.",
        ],
        evidence=_merge_evidence(
            hotspot_payload.get("evidence", []),
            external_payload.get("evidence", []),
            sql_payload.get("evidence", []),
        ),
    )
    return _pack(
        PackType.STABILITY_SIGNALS.value,
        context,
        payload,
        evidence=_merge_evidence_objects(payload.evidence),
        warnings=warnings,
        source_mode=source_mode,
        missing_inputs=sorted(set(missing_inputs)),
        confidence_notes=["Repeatability and spread use simple heuristics so the output stays explainable and stable."],
        build_stats={"object_count": len(objects)},
    )


def build_impact_signals_pack(
    adapter: Any,
    context: AnalysisContext,
    *,
    source_mode: str = "auto",
    limit: int = 10,
) -> PackEnvelope:
    warnings: list[WarningMessage] = []

    labels_envelope = build_business_labels_pack(adapter, context, source_mode=source_mode, limit=limit)
    stability_envelope = build_stability_signals_pack(adapter, context, source_mode=source_mode, limit=limit)

    warnings.extend(labels_envelope.meta.warnings)
    warnings.extend(stability_envelope.meta.warnings)

    labels_payload = labels_envelope.to_dict()["payload"]
    stability_payload = stability_envelope.to_dict()["payload"]
    label_map = {_ref_key(item.get("target_ref")): item for item in labels_payload.get("objects") or []}

    objects: list[dict[str, Any]] = []
    for item in stability_payload.get("objects") or []:
        ref_key = _ref_key(item.get("target_ref"))
        label_item = label_map.get(ref_key, {})
        labels = set(label_item.get("labels") or [])
        metrics = item.get("metrics") or {}
        impact_dimensions = _impact_dimensions(labels, item, metrics)
        impact_reasons = _impact_reasons(labels, item, metrics)
        score = _impact_score(impact_dimensions, metrics)
        tier = _impact_tier(labels, impact_dimensions, metrics)
        objects.append(
            {
                "target_ref": item.get("target_ref"),
                "target_type": item.get("target_type"),
                "display_name": item.get("display_name"),
                "impact_tier": tier,
                "impact_score": score,
                "impact_dimensions": impact_dimensions,
                "impact_reasons": impact_reasons,
                "evidence_strength": impact_dimensions.get("evidence_strength"),
                "confidence": "medium" if item.get("confidence") != "low" else "low",
                "review_flags": _impact_review_flags(metrics, item),
                "evidence_refs": sorted(set((item.get("evidence_refs") or []) + (label_item.get("evidence_refs") or []))),
                "source_basis": [
                    {"kind": "pack", "value": "business_labels_pack"},
                    {"kind": "pack", "value": "stability_signals_pack"},
                ],
            }
        )

    objects.sort(key=lambda item: (item.get("impact_score") or 0, item.get("impact_tier") == "P1_user_failure"), reverse=True)
    payload = ImpactSignalsPackPayload(
        scope=_pack_scope(context, source_mode, limit),
        objects=objects,
        summaries={
            "tier_counts": dict(Counter(item.get("impact_tier") for item in objects)),
            "top_reasons": dict(Counter(reason for item in objects for reason in item.get("impact_reasons") or []).most_common(10)),
        },
        input_dependencies=["business_labels_pack", "stability_signals_pack"],
        derivation_notes=[
            "Impact signals are ranking aids, not final priority conclusions.",
            "Scores are configurable heuristics composed from business labels, stability, failures, and evidence strength.",
        ],
        evidence=_merge_evidence(labels_payload.get("evidence", []), stability_payload.get("evidence", [])),
    )
    return _pack(
        PackType.IMPACT_SIGNALS.value,
        context,
        payload,
        evidence=_merge_evidence_objects(payload.evidence),
        warnings=warnings,
        source_mode=source_mode,
        missing_inputs=sorted(set(labels_envelope.meta.missing_inputs + stability_envelope.meta.missing_inputs)),
        confidence_notes=["Impact tiers are intentionally conservative and require human review before final prioritization."],
        build_stats={"object_count": len(objects)},
    )


def build_comparison_signals_pack(
    adapter: Any,
    context: AnalysisContext,
    *,
    source_mode: str = "auto",
    limit: int = 10,
) -> PackEnvelope:
    warnings: list[WarningMessage] = []
    missing_inputs: list[str] = []

    previous_context = _previous_window_context(context)
    if previous_context is None:
        missing_inputs.append("previous_window_context")

    current_hotspots = build_action_hotspot_pack(adapter, context, source_mode=source_mode)
    current_external = build_external_dependency_pack(adapter, context, source_mode=source_mode)
    current_sql = build_slow_sql_pack(adapter, context, source_mode=source_mode, limit=limit)

    warnings.extend(current_hotspots.meta.warnings)
    warnings.extend(current_external.meta.warnings)
    warnings.extend(current_sql.meta.warnings)

    previous_hotspot_payload: dict[str, Any] = {}
    previous_external_payload: dict[str, Any] = {}
    previous_sql_payload: dict[str, Any] = {}
    if previous_context is not None:
        previous_hotspots = build_action_hotspot_pack(adapter, previous_context, source_mode=source_mode)
        previous_external = build_external_dependency_pack(adapter, previous_context, source_mode=source_mode)
        previous_sql = build_slow_sql_pack(adapter, previous_context, source_mode=source_mode, limit=limit)
        warnings.extend(previous_hotspots.meta.warnings)
        warnings.extend(previous_external.meta.warnings)
        warnings.extend(previous_sql.meta.warnings)
        previous_hotspot_payload = previous_hotspots.to_dict()["payload"]
        previous_external_payload = previous_external.to_dict()["payload"]
        previous_sql_payload = previous_sql.to_dict()["payload"]

    current_objects = _comparison_source_objects(
        current_hotspots.to_dict()["payload"],
        current_external.to_dict()["payload"],
        current_sql.to_dict()["payload"],
        limit=limit,
    )
    previous_objects = _comparison_source_objects(previous_hotspot_payload, previous_external_payload, previous_sql_payload, limit=limit)
    previous_map = {_ref_key(item.get("target_ref")): item for item in previous_objects}
    current_map = {_ref_key(item.get("target_ref")): item for item in current_objects}
    all_keys = list(dict.fromkeys([*current_map.keys(), *previous_map.keys()]))

    objects: list[dict[str, Any]] = []
    for key in all_keys:
        current_item = current_map.get(key)
        previous_item = previous_map.get(key)
        change_class, delta_metrics, summary, trend_confidence = _comparison_result(current_item, previous_item)
        objects.append(
            {
                "target_ref": (current_item or previous_item or {}).get("target_ref"),
                "target_type": (current_item or previous_item or {}).get("target_type"),
                "display_name": (current_item or previous_item or {}).get("display_name"),
                "comparison_baseline": {
                    "mode": "previous_window",
                    "current_end_time": context.time_window.end_time,
                    "previous_end_time": previous_context.time_window.end_time if previous_context else None,
                },
                "change_class": change_class,
                "change_summary": summary,
                "delta_metrics": delta_metrics,
                "new_or_disappeared": change_class in {"new_risk", "disappeared"},
                "trend_confidence": trend_confidence,
                "evidence_refs": (current_item or previous_item or {}).get("evidence_refs") or [],
                "source_basis": [{"kind": "baseline", "value": "previous_window"}],
            }
        )

    payload = ComparisonSignalsPackPayload(
        scope=_pack_scope(context, source_mode, limit),
        comparison_baseline={
            "mode": "previous_window",
            "current_window": dataclass_to_dict(context.time_window),
            "previous_window": dataclass_to_dict(previous_context.time_window) if previous_context else {},
        },
        objects=objects,
        summaries={"change_class_counts": dict(Counter(item.get("change_class") for item in objects))},
        input_dependencies=["action_hotspot_pack", "external_dependency_pack", "slow_sql_pack"],
        derivation_notes=[
            "Comparison uses previous_window first and keeps the baseline explicit in output.",
            "No long-term forecast is performed inside the adapter.",
        ],
        evidence=_merge_evidence(
            current_hotspots.to_dict()["payload"].get("evidence", []),
            current_external.to_dict()["payload"].get("evidence", []),
            current_sql.to_dict()["payload"].get("evidence", []),
        ),
    )
    return _pack(
        PackType.COMPARISON_SIGNALS.value,
        context,
        payload,
        evidence=_merge_evidence_objects(payload.evidence),
        warnings=warnings,
        source_mode=source_mode,
        missing_inputs=sorted(set(missing_inputs)),
        confidence_notes=["If the previous window has sparse data, comparison falls back to low-confidence deltas instead of failing."],
        build_stats={"object_count": len(objects)},
    )


def build_page_experience_pack(
    adapter: Any,
    context: AnalysisContext,
    *,
    source_mode: str = "auto",
    limit: int = 10,
) -> PackEnvelope:
    warnings: list[WarningMessage] = []
    missing_inputs = ["js_error_summary", "browser_distribution", "geo_distribution", "platform_distribution"]

    hotspots = build_action_hotspot_pack(adapter, context, source_mode=source_mode)
    topology = build_topology_dependency_pack(adapter, context, source_mode=source_mode)
    external = build_external_dependency_pack(adapter, context, source_mode=source_mode)

    warnings.extend(hotspots.meta.warnings)
    warnings.extend(topology.meta.warnings)
    warnings.extend(external.meta.warnings)

    hotspot_payload = hotspots.to_dict()["payload"]
    topology_payload = topology.to_dict()["payload"]
    external_payload = external.to_dict()["payload"]
    hotspot_rows = (hotspot_payload.get("hotspots") or [])[:limit]
    topology_dependencies = topology_payload.get("dependencies") or []
    external_dependencies = external_payload.get("external_dependencies") or []

    app_to_external: dict[str, list[dict[str, Any]]] = defaultdict(list)
    user_edges: dict[str, dict[str, Any]] = {}
    for edge in topology_dependencies:
        if edge.get("from_category") == "application" and edge.get("to_category") == "external" and edge.get("from"):
            app_to_external[str(edge.get("from"))].append(edge)
        if edge.get("from_category") == "user" and edge.get("to"):
            user_edges[str(edge.get("to"))] = edge

    pages: list[dict[str, Any]] = []
    related_action_refs: list[dict[str, Any]] = []
    related_dependency_refs: list[dict[str, Any]] = []
    for row in hotspot_rows:
        action = row.get("action") or {}
        raw = row.get("raw") or {}
        action_name = str(action.get("name") or "")
        route = _route_pattern_from_action_name(action_name)
        if not route:
            continue
        app_name = str(raw.get("applicationName") or "")
        user_edge = user_edges.get(app_name, {})
        page_dependencies = app_to_external.get(app_name, [])
        page = {
            "page_ref": {"kind": "page", "route": route, "application_name": app_name},
            "page_name": _page_name_from_route(route),
            "route_or_url_pattern": route,
            "traffic_summary": {
                "throughput": (action.get("metrics") or {}).get("throughput"),
                "user_edge_throughput": user_edge.get("throughput"),
            },
            "performance_summary": {
                "avg_response_time_ms": (action.get("metrics") or {}).get("response_time_ms"),
                "slow_count": (action.get("metrics") or {}).get("slow_count"),
                "user_edge_response_time_ms": user_edge.get("response_time_ms"),
            },
            "js_error_summary": {"status": "unavailable"},
            "browser_distribution": [],
            "geo_distribution": [],
            "related_actions": [_action_target_ref(action)],
            "related_dependencies": [_dependency_target_ref(dep) for dep in page_dependencies[:3]],
            "likely_backend_hotspots": row.get("suspect_signals") or [],
            "page_signals": _page_signals(action, user_edge, page_dependencies),
            "page_impact_hints": _page_impact_hints(action, user_edge, page_dependencies),
            "source_basis": [
                {"kind": "pack", "value": "action_hotspot_pack"},
                {"kind": "pack", "value": "topology_dependency_pack"},
                {"kind": "pack", "value": "external_dependency_pack"},
            ],
            "confidence": "low",
            "review_flags": ["backend_route_proxy"],
        }
        pages.append(page)
        related_action_refs.extend(page["related_actions"])
        related_dependency_refs.extend(page["related_dependencies"])

    if not pages:
        for app_name, user_edge in list(user_edges.items())[:limit]:
            pages.append(
                {
                    "page_ref": {"kind": "page", "route": f"user-entry::{app_name}", "application_name": app_name},
                    "page_name": f"{app_name} user entry",
                    "route_or_url_pattern": None,
                    "traffic_summary": {"user_edge_throughput": user_edge.get("throughput")},
                    "performance_summary": {"user_edge_response_time_ms": user_edge.get("response_time_ms")},
                    "js_error_summary": {"status": "unavailable"},
                    "browser_distribution": [],
                    "geo_distribution": [],
                    "related_actions": [],
                    "related_dependencies": [_dependency_target_ref(dep) for dep in app_to_external.get(app_name, [])[:3]],
                    "likely_backend_hotspots": [],
                    "page_signals": _page_signals({}, user_edge, app_to_external.get(app_name, [])),
                    "page_impact_hints": ["derived_from_user_entry_edge_only"],
                    "source_basis": [{"kind": "pack", "value": "topology_dependency_pack"}],
                    "confidence": "low",
                    "review_flags": ["no_page_api_dataset"],
                }
            )

    performance_summary = {
        "page_count": len(pages),
        "slow_page_count": len([page for page in pages if _numeric((page.get("performance_summary") or {}).get("avg_response_time_ms")) and _numeric((page.get("performance_summary") or {}).get("avg_response_time_ms")) >= 1000]),
        "user_entry_count": len(user_edges),
        "max_user_entry_response_ms": max([_numeric(edge.get("response_time_ms")) or 0.0 for edge in user_edges.values()] or [0.0]),
        "max_page_response_ms": max([_numeric((page.get("performance_summary") or {}).get("avg_response_time_ms")) or 0.0 for page in pages] or [0.0]),
    }
    payload = PageExperiencePackPayload(
        scope=_pack_scope(context, source_mode, limit),
        pages=pages,
        performance_summary=performance_summary,
        js_error_summary={"status": "missing_input", "count": None},
        browser_distribution=[],
        geo_distribution=[],
        platform_distribution=[],
        related_actions=_unique_refs(related_action_refs),
        related_dependencies=_unique_refs(related_dependency_refs),
        input_dependencies=["action_hotspot_pack", "topology_dependency_pack", "external_dependency_pack"],
        derivation_notes=[
            "Current project does not yet ship dedicated page-side clients, so page objects are inferred from user-entry topology and URI-style actions.",
            "This pack remains a fact layer and does not claim full RUM coverage.",
        ],
        evidence=_merge_evidence(
            hotspot_payload.get("evidence", []),
            topology_payload.get("evidence", []),
            external_payload.get("evidence", []),
        ),
    )
    page_links = [
        make_console_link(
            adapter,
            context,
            page_type="page_experience_proxy",
            label="页面体验代理视图",
            why_relevant="用于从用户入口拓扑和代表性后端请求代理查看页面体验证据。",
            suggested_report_section="3.5 页面用户体验检查",
            navigation_path=["业务系统", "拓扑", "用户入口", "代表性接口"],
            suggested_filters={"bizSystemId": context.biz_system_id},
            target_ref={"kind": "biz_system", "biz_system_id": context.biz_system_id},
        )
    ]
    screenshot_hints = [
        make_screenshot_hint(
            title="页面体验代理证据截图建议",
            page_type="page_experience_proxy",
            url=page_links[0]["url"],
            recommended_capture=["用户入口到应用拓扑", "代表性后端接口列表", "外部依赖列表"],
            recommended_annotations=["标注页面代理对象", "标注对应后端接口", "标注页面侧缺失能力范围"],
            usage_in_report="可用于页面章节的保守举证，并明确说明当前仅为代理证据。",
            suggested_report_section="3.5 页面用户体验检查",
            target_ref=page_links[0]["target_ref"],
            priority="medium",
        )
    ]
    metric_semantics = [
        make_metric_semantic(
            metric_name="avg_response_time_ms",
            subject_type="page_proxy",
            subject_key=f"biz_system:{context.biz_system_id}:page_proxy",
            aggregation="average",
            unit="ms",
            time_window=time_window_text(context),
            sample_scope="proxy pages inferred from user-entry topology and URI-style backend actions",
            confidence="low",
        )
    ]
    coverage_boundary = default_coverage_boundary(
        adapter,
        page_status="partial",
        page_reason="Dedicated page-side APIs are not exposed yet; page objects are inferred from topology and backend request evidence.",
        available_page_evidence=[
            "user_to_application_topology",
            "representative_request_urls",
            "external_dependency_edges",
            "backend_action_and_trace_correlation",
        ],
        missing_page_evidence=[
            "slow_pages",
            "slow_requests",
            "js_errors",
            "browser_breakdown",
            "geo_breakdown",
            "frontend_resource_timing",
        ],
    )
    evidence_linkage = {
        "related_time_windows": [dataclass_to_dict(context.time_window)],
        "related_actions": _unique_refs(related_action_refs),
        "related_traces": [],
        "related_sqls": [],
        "related_dependencies": _unique_refs(related_dependency_refs),
        "recommended_next_pages": page_links,
    }
    payload = apply_report_support(
        payload,
        page_links=page_links,
        screenshot_hints=screenshot_hints,
        metric_semantics=metric_semantics,
        coverage_boundary=coverage_boundary,
        evidence_linkage=evidence_linkage,
    )
    return _pack(
        PackType.PAGE_EXPERIENCE.value,
        context,
        payload,
        evidence=_merge_evidence_objects(payload.evidence),
        warnings=warnings,
        source_mode=source_mode,
        missing_inputs=sorted(set(missing_inputs)),
        confidence_notes=["Page objects are inferred proxies until dedicated page-side APIs are added."],
        build_stats={"page_count": len(pages), "user_entry_count": len(user_edges)},
    )


def build_screenshot_index_pack(
    adapter: Any,
    context: AnalysisContext,
    *,
    source_mode: str = "auto",
    limit: int = 10,
) -> PackEnvelope:
    warnings: list[WarningMessage] = []
    missing_inputs: list[str] = []

    snapshot = build_system_snapshot(adapter, context, source_mode=source_mode)
    action_hotspots = build_action_hotspot_pack(adapter, context, source_mode=source_mode)
    page_pack = build_page_experience_pack(adapter, context, source_mode=source_mode, limit=limit)
    slow_sql = build_slow_sql_pack(adapter, context, source_mode=source_mode, limit=limit)

    warnings.extend(snapshot.meta.warnings)
    warnings.extend(action_hotspots.meta.warnings)
    warnings.extend(page_pack.meta.warnings)
    warnings.extend(slow_sql.meta.warnings)
    missing_inputs.extend(snapshot.meta.missing_inputs)
    missing_inputs.extend(action_hotspots.meta.missing_inputs)
    missing_inputs.extend(page_pack.meta.missing_inputs)
    missing_inputs.extend(slow_sql.meta.missing_inputs)

    snapshot_payload = snapshot.to_dict()["payload"]
    hotspot_payload = action_hotspots.to_dict()["payload"]
    page_payload = page_pack.to_dict()["payload"]
    slow_sql_payload = slow_sql.to_dict()["payload"]

    cards = collect_screenshot_cards(
        snapshot_payload.get("screenshot_hints", []),
        hotspot_payload.get("screenshot_hints", []),
        page_payload.get("screenshot_hints", []),
        slow_sql_payload.get("screenshot_hints", []),
    )

    hotspot_rows = hotspot_payload.get("hotspots") or []
    if hotspot_rows:
        top_action = hotspot_rows[0].get("action") or {}
        if top_action.get("id") and top_action.get("application_id"):
            action_fact = build_action_fact_sheet(
                adapter,
                context,
                source_mode=source_mode,
                action_ref=_action_ref_from_target(top_action),
                trace_limit=min(limit, 5),
            )
            warnings.extend(action_fact.meta.warnings)
            missing_inputs.extend(action_fact.meta.missing_inputs)
            action_payload = action_fact.to_dict()["payload"]
            cards = collect_screenshot_cards(cards, action_payload.get("screenshot_hints", []))
        else:
            action_payload = {}
    else:
        action_payload = {}

    top_sqls = slow_sql_payload.get("top_sqls") or []
    if top_sqls:
        top_sql = top_sqls[0]
        component_name = top_sql.get("component_name") or top_sql.get("componentName")
        if component_name:
            sql_fact = build_sql_fact_sheet(
                adapter,
                context,
                source_mode=source_mode,
                component_ref=DatabaseComponentRef(
                    biz_system_id=context.biz_system_id,
                    component_name=str(component_name),
                    component_subtype=top_sql.get("component_subtype") or top_sql.get("componentSubtype"),
                ),
                op_name=top_sql.get("op_name_decoded") or top_sql.get("opName"),
                limit=min(limit, 5),
            )
            warnings.extend(sql_fact.meta.warnings)
            missing_inputs.extend(sql_fact.meta.missing_inputs)
            sql_payload = sql_fact.to_dict()["payload"]
            cards = collect_screenshot_cards(cards, sql_payload.get("screenshot_hints", []))
        else:
            sql_payload = {}
    else:
        sql_payload = {}

    page_links = []
    for payload in (snapshot_payload, hotspot_payload, action_payload, slow_sql_payload, sql_payload, page_payload):
        page_links.extend(payload.get("page_links") or [])

    screenshot_cards = []
    for index, card in enumerate(cards, start=1):
        screenshot_cards.append(
            {
                "figure_id": f"FIG-{index:02d}",
                "title": card.get("title"),
                "page_type": card.get("page_type"),
                "url": card.get("url"),
                "recommended_capture": card.get("recommended_capture") or [],
                "recommended_annotations": card.get("recommended_annotations") or [],
                "usage_in_report": card.get("usage_in_report"),
                "suggested_report_section": card.get("suggested_report_section"),
                "priority": card.get("priority", "medium"),
                "target_ref": card.get("target_ref") or {},
            }
        )

    payload = ScreenshotIndexPackPayload(
        scope=_pack_scope(context, source_mode, limit),
        screenshot_cards=screenshot_cards,
        input_dependencies=[
            "system_snapshot",
            "action_hotspot_pack",
            "action_fact_sheet",
            "slow_sql_pack",
            "sql_fact_sheet",
            "page_experience_pack",
        ],
        derivation_notes=[
            "This pack indexes screenshot candidates and console links for report evidence collection.",
            "It does not assert final conclusions; it only organizes capture candidates and navigation hints.",
        ],
        evidence=_merge_evidence(
            snapshot_payload.get("evidence", []),
            hotspot_payload.get("evidence", []),
            action_payload.get("evidence", []),
            slow_sql_payload.get("evidence", []),
            sql_payload.get("evidence", []),
            page_payload.get("evidence", []),
        ),
    )
    payload = apply_report_support(
        payload,
        page_links=page_links,
        screenshot_hints=screenshot_cards,
        metric_semantics=[],
        coverage_boundary=default_coverage_boundary(adapter),
        evidence_linkage={
            "related_time_windows": [dataclass_to_dict(context.time_window)],
            "related_actions": action_payload.get("evidence_linkage", {}).get("related_actions", []),
            "related_traces": action_payload.get("evidence_linkage", {}).get("related_traces", []),
            "related_sqls": sql_payload.get("evidence_linkage", {}).get("related_sqls", []) or slow_sql_payload.get("top_sqls", [])[:5],
            "related_dependencies": page_payload.get("evidence_linkage", {}).get("related_dependencies", []),
            "recommended_next_pages": page_links[:10],
        },
    )
    return _pack(
        PackType.SCREENSHOT_INDEX.value,
        context,
        payload,
        evidence=_merge_evidence_objects(payload.evidence),
        warnings=warnings,
        source_mode=source_mode,
        missing_inputs=sorted(set(missing_inputs)),
        confidence_notes=["Screenshot index organizes capture candidates and links; human review is still required before report insertion."],
        build_stats={"card_count": len(screenshot_cards)},
    )


def _pack_scope(context: AnalysisContext, source_mode: str, limit: int) -> dict[str, Any]:
    return {
        "bizSystemId": context.biz_system_id,
        "endTime": context.time_window.end_time,
        "periodMinutes": context.time_window.period_minutes,
        "sourceMode": source_mode,
        "limit": limit,
    }


def _action_target_ref(action: dict[str, Any]) -> dict[str, Any]:
    return {
        "kind": "action",
        "biz_system_id": action.get("biz_system_id"),
        "application_id": action.get("application_id"),
        "action_id": action.get("id"),
        "action_type": action.get("type"),
    }


def _action_ref_from_target(action: dict[str, Any]) -> Any:
    from tingyun_adapter.domain.models.common import ActionRef

    return ActionRef(
        biz_system_id=int(action.get("biz_system_id") or 0),
        application_id=int(action.get("application_id") or 0),
        action_id=int(action.get("id") or 0),
        action_type=str(action.get("type") or "TX"),
    )


def _dependency_target_ref(dep: dict[str, Any]) -> dict[str, Any]:
    return {
        "kind": "external_dependency",
        "protocol": dep.get("protocol"),
        "node_id": dep.get("node_id"),
    }


def _sql_target_ref(sql_row: dict[str, Any]) -> dict[str, Any]:
    return {
        "kind": "sql",
        "component_name": sql_row.get("component_name") or sql_row.get("componentName"),
        "fingerprint": _sql_fingerprint(sql_row.get("op_name_decoded") or sql_row.get("opName") or sql_row.get("op_name_raw")),
    }


def _label_summaries(objects: list[dict[str, Any]]) -> dict[str, Any]:
    label_counts: Counter[str] = Counter()
    type_counts: Counter[str] = Counter()
    for item in objects:
        type_counts.update([str(item.get("target_type") or "unknown")])
        label_counts.update(item.get("labels") or [])
    return {
        "object_count": len(objects),
        "target_type_counts": dict(type_counts),
        "label_counts": dict(label_counts),
    }


def _stability_summaries(objects: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "object_count": len(objects),
        "stability_class_counts": dict(Counter(item.get("stability_class") for item in objects)),
        "spread_scope_counts": dict(Counter(item.get("spread_scope") for item in objects)),
    }


def _derive_action_labels(name: str, raw: dict[str, Any], user_entry_apps: set[str]) -> tuple[list[str], dict[str, str], list[str], list[str]]:
    labels: list[str] = []
    review_flags: list[str] = []
    derivation_notes: list[str] = []
    lower_name = name.lower()
    app_name = str(raw.get("applicationName") or "")

    entry_label = "unknown_entry"
    if any(keyword in lower_name for keyword in ENTRY_KEYWORDS["user_entry"]):
        entry_label = "user_entry"
        labels.append("interactive_request")
        labels.append("real_user_visible")
        derivation_notes.append("Matched URI/API style action naming.")
    elif any(keyword in lower_name for keyword in ENTRY_KEYWORDS["internal_entry"]):
        entry_label = "internal_entry"
    if app_name and app_name in user_entry_apps and "user_entry" not in labels:
        entry_label = "user_entry"
        labels.append("real_user_visible")
        derivation_notes.append("Application appears behind a user entry edge in topology.")
    labels.append(entry_label)

    criticality = "unknown_business_criticality"
    if any(keyword in lower_name for keyword in CORE_BUSINESS_KEYWORDS):
        criticality = "core_business_path"
    elif any(keyword in lower_name for keyword in SUPPORT_KEYWORDS):
        criticality = "important_support_path"
    elif any(keyword in lower_name for keyword in MAINTENANCE_KEYWORDS):
        criticality = "non_core_path"
    labels.append(criticality)

    if any(keyword in lower_name for keyword in BACKGROUND_KEYWORDS):
        if "afterpropertiesset" in lower_name or "warmup" in lower_name or "init" in lower_name:
            labels.append("init_or_warmup")
        elif any(keyword in lower_name for keyword in ("schedule", "cron", "scheduled")):
            labels.append("scheduled_stat_job")
        elif any(keyword in lower_name for keyword in ("batch", "job")):
            labels.append("batch_job")
        else:
            labels.append("async_task")
        labels.append("likely_background_only")
    elif "interactive_request" not in labels:
        labels.append("interactive_request" if entry_label == "user_entry" else "likely_maintenance_path")

    if any(keyword in lower_name for keyword in SUPPORT_KEYWORDS) and "real_user_visible" not in labels:
        labels.append("real_user_visible")

    naming_health = "well_named"
    if any(keyword in lower_name for keyword in FRAMEWORK_NOISE_KEYWORDS):
        naming_health = "framework_noise_named"
    elif len(name) < 12 or name.count("/") < 1:
        naming_health = "ambiguous_named"
    labels.append(naming_health)
    if naming_health != "well_named":
        review_flags.append("naming_review_recommended")

    label_groups = {
        "entry": entry_label,
        "business_criticality": criticality,
        "request_nature": _first_label(labels, ("interactive_request", "async_task", "batch_job", "init_or_warmup", "scheduled_stat_job")),
        "risk_semantics": _first_label(labels, ("real_user_visible", "likely_background_only", "likely_maintenance_path")),
        "naming_health": naming_health,
    }
    return _unique_list(labels), label_groups, _unique_list(review_flags), derivation_notes


def _derive_dependency_labels(dep: dict[str, Any], user_entry_apps: set[str]) -> tuple[list[str], dict[str, str], list[str], list[str]]:
    labels = ["important_support_path", "well_named"]
    review_flags: list[str] = []
    derivation_notes: list[str] = []
    upstream_names = {str(item.get("name") or "") for item in dep.get("upstream_nodes") or []}
    if upstream_names & user_entry_apps:
        labels.extend(["real_user_visible", "user_entry"])
        derivation_notes.append("Dependency is downstream of an app that also receives direct user traffic.")
    else:
        labels.append("internal_entry")
    if _numeric(dep.get("throughput")) and _numeric(dep.get("throughput")) >= 1:
        labels.append("core_business_path")
    else:
        labels.append("important_support_path")
    if _numeric(dep.get("response_time_ms")) and _numeric(dep.get("response_time_ms")) >= 1000:
        review_flags.append("high_latency_dependency")
    label_groups = {
        "entry": _first_label(labels, ("user_entry", "internal_entry", "unknown_entry")),
        "business_criticality": _first_label(labels, ("core_business_path", "important_support_path", "non_core_path", "unknown_business_criticality")),
        "request_nature": "interactive_request",
        "risk_semantics": _first_label(labels, ("real_user_visible", "likely_background_only", "likely_maintenance_path")),
        "naming_health": "well_named",
    }
    return _unique_list(labels), label_groups, _unique_list(review_flags), derivation_notes


def _label_confidence(labels: list[str], review_flags: list[str]) -> str:
    if review_flags:
        return "medium" if len(labels) >= 4 else "low"
    return "high" if len(labels) >= 4 else "medium"


def _repeatability_score(count: Optional[float], slow_count: Optional[float], trace_count: Optional[float]) -> int:
    count_score = min(int((count or 0) * 2), 40)
    slow_score = min(int((slow_count or 0) * 4), 35)
    trace_score = min(int((trace_count or 0) * 5), 25)
    return min(count_score + slow_score + trace_score, 100)


def _stability_class(score: int) -> str:
    if score <= 10:
        return "one_off"
    if score <= 35:
        return "sporadic"
    if score <= 70:
        return "recurring"
    return "persistent"


def _action_spread_scope(action_name: Any, instance_count: Optional[float], duplicate_name_count: int) -> str:
    if duplicate_name_count > 1:
        return "cross_application_pattern"
    if (instance_count or 0) > 1:
        return "multi_instance_localized"
    return "single_instance_local"


def _dependency_spread_scope(upstream_count: int) -> str:
    if upstream_count >= 3:
        return "systemic_pattern"
    if upstream_count == 2:
        return "cross_application_pattern"
    return "single_instance_local"


def _sql_spread_scope(trace_count: Optional[float]) -> str:
    if (trace_count or 0) >= 100:
        return "systemic_pattern"
    if (trace_count or 0) >= 20:
        return "cross_application_pattern"
    return "single_instance_local"


def _time_distribution(timestamps: list[Any]) -> str:
    parsed = [_parse_timestamp(item) for item in timestamps]
    parsed = [item for item in parsed if item is not None]
    if len(parsed) <= 1:
        return "time_window_clustered"
    hours = [item.hour for item in parsed]
    if all(hour < 6 for hour in hours):
        return "nightly_batch_related"
    if all(8 <= hour <= 20 for hour in hours):
        if len({item.date() for item in parsed}) > 1 and len({item.hour for item in parsed}) <= 3:
            return "daily_recurring"
        return "workhour_sensitive"
    if len({item.date() for item in parsed}) > 1 and len({item.hour for item in parsed}) > 6:
        return "uniformly_distributed"
    return "time_window_clustered"


def _burstiness(response_time_ms: Optional[float], count: Optional[float], timestamps: list[Any]) -> str:
    if response_time_ms and response_time_ms >= 1000 and (count or 0) >= 10:
        return "stable_bad"
    if response_time_ms and response_time_ms >= 1000 and (count or 0) <= 3:
        return "unstable_spiky"
    if len(timestamps) >= 3:
        return "stable_bad"
    return "unstable_spiky"


def _dependency_repeatability_score(dep: dict[str, Any]) -> int:
    score = 0
    if _numeric(dep.get("throughput")):
        score += min(int((_numeric(dep.get("throughput")) or 0) * 10), 40)
    if _numeric(dep.get("error_rate")):
        score += min(int((_numeric(dep.get("error_rate")) or 0) * 5), 30)
    score += min(int(len(dep.get("upstream_nodes") or []) * 10), 30)
    return min(score, 100)


def _impact_dimensions(labels: set[str], stability_item: dict[str, Any], metrics: dict[str, Any]) -> dict[str, int]:
    business_score = 0
    for label, weight in IMPACT_WEIGHTS["business"].items():
        if label in labels:
            business_score += weight

    error_rate = _numeric(metrics.get("error_rate"))
    error_count = _numeric(metrics.get("error_count"))
    failure_score = 0
    if error_rate is not None and error_rate >= 50:
        failure_score += IMPACT_WEIGHTS["failure"]["error_rate_high"]
    elif error_rate is not None and error_rate >= 1:
        failure_score += IMPACT_WEIGHTS["failure"]["error_rate_medium"]
    if error_count and error_count > 0:
        failure_score += IMPACT_WEIGHTS["failure"]["error_count_present"]

    response_time = _numeric(metrics.get("response_time_ms"))
    slow_count = _numeric(metrics.get("slow_count"))
    performance_score = 0
    if response_time is not None and response_time >= 5000:
        performance_score += IMPACT_WEIGHTS["performance"]["response_very_high"]
    elif response_time is not None and response_time >= 1000:
        performance_score += IMPACT_WEIGHTS["performance"]["response_high"]
    elif response_time is not None and response_time >= 300:
        performance_score += IMPACT_WEIGHTS["performance"]["response_medium"]
    if slow_count and slow_count >= 10:
        performance_score += IMPACT_WEIGHTS["performance"]["slow_count_high"]

    repeatability_score = 0
    stability_class = str(stability_item.get("stability_class") or "")
    spread_scope = str(stability_item.get("spread_scope") or "")
    if stability_class in IMPACT_WEIGHTS["repeatability"]:
        repeatability_score += IMPACT_WEIGHTS["repeatability"][stability_class]
    if spread_scope in IMPACT_WEIGHTS["repeatability"]:
        repeatability_score += IMPACT_WEIGHTS["repeatability"][spread_scope]

    evidence_strength = 0
    evidence_refs = stability_item.get("evidence_refs") or []
    if any("trace" in ref for ref in evidence_refs):
        evidence_strength += IMPACT_WEIGHTS["evidence"]["trace_present"]
    if stability_item.get("target_type") == "sql":
        evidence_strength += IMPACT_WEIGHTS["evidence"]["sql_present"]
    if stability_item.get("target_type") == "external_dependency":
        evidence_strength += IMPACT_WEIGHTS["evidence"]["dependency_present"]

    return {
        "business_impact": min(business_score, 40),
        "failure_severity": min(failure_score, 40),
        "performance_cost": min(performance_score, 35),
        "repeatability_scope": min(repeatability_score, 30),
        "evidence_strength": min(evidence_strength, 20),
    }


def _impact_score(dimensions: dict[str, int], metrics: dict[str, Any]) -> int:
    score = sum(dimensions.values())
    count = _numeric(metrics.get("count"))
    error_count = _numeric(metrics.get("error_count"))
    if (count or 0) <= 3 and (error_count or 0) <= 0:
        score -= IMPACT_WEIGHTS["penalty"]["low_frequency"]
    return max(0, min(score, 100))


def _impact_tier(labels: set[str], dimensions: dict[str, int], metrics: dict[str, Any]) -> str:
    if dimensions["failure_severity"] >= 28 and "real_user_visible" in labels:
        return "P1_user_failure"
    if dimensions["performance_cost"] >= 18 and (dimensions["business_impact"] >= 10 or dimensions["repeatability_scope"] >= 10):
        return "P2_high_impact_performance"
    if dimensions["repeatability_scope"] >= 12 or dimensions["evidence_strength"] >= 10:
        return "P3_structural_risk"
    return "P4_observation_only"


def _impact_reasons(labels: set[str], stability_item: dict[str, Any], metrics: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    if "real_user_visible" in labels:
        reasons.append("real_user_visible")
    if "core_business_path" in labels:
        reasons.append("core_business_path")
    error_rate = _numeric(metrics.get("error_rate"))
    error_count = _numeric(metrics.get("error_count"))
    if (error_rate is not None and error_rate >= 1) or (error_count or 0) > 0:
        reasons.append("high_error_rate")
    if str(stability_item.get("spread_scope")) in {"cross_application_pattern", "systemic_pattern", "multi_instance_localized"}:
        reasons.append("multi_instance_recurring")
    if any("trace" in ref for ref in stability_item.get("evidence_refs") or []) and stability_item.get("target_type") == "sql":
        reasons.append("trace_and_sql_evidence_present")
    elif any("trace" in ref for ref in stability_item.get("evidence_refs") or []):
        reasons.append("trace_evidence_present")
    count = _numeric(metrics.get("count"))
    if (count or 0) <= 3 and (error_count or 0) <= 0:
        reasons.append("low_frequency_penalty_applied")
    return _unique_list(reasons)


def _impact_review_flags(metrics: dict[str, Any], stability_item: dict[str, Any]) -> list[str]:
    flags: list[str] = []
    if stability_item.get("confidence") == "low":
        flags.append("confidence_review_recommended")
    if _numeric(metrics.get("count")) is None and _numeric(metrics.get("throughput")) is None:
        flags.append("missing_volume_metric")
    return flags


def _comparison_source_objects(
    hotspot_payload: dict[str, Any],
    external_payload: dict[str, Any],
    sql_payload: dict[str, Any],
    *,
    limit: int,
) -> list[dict[str, Any]]:
    objects: list[dict[str, Any]] = []
    for row in (hotspot_payload.get("hotspots") or [])[:limit]:
        action = row.get("action") or {}
        objects.append(
            {
                "target_ref": _action_target_ref(action),
                "target_type": "action",
                "display_name": action.get("name"),
                "metrics": dataclass_to_dict(action.get("metrics") or {}),
                "evidence_refs": ["action_list"],
            }
        )
    for dep in (external_payload.get("external_dependencies") or [])[:limit]:
        objects.append(
            {
                "target_ref": _dependency_target_ref(dep),
                "target_type": "external_dependency",
                "display_name": dep.get("node_id") or dep.get("protocol"),
                "metrics": {
                    "response_time_ms": dep.get("response_time_ms"),
                    "error_rate": dep.get("error_rate"),
                    "throughput": dep.get("throughput"),
                },
                "evidence_refs": ["biz_detail_graph"],
            }
        )
    for sql_row in (sql_payload.get("top_sqls") or [])[:limit]:
        objects.append(
            {
                "target_ref": _sql_target_ref(sql_row),
                "target_type": "sql",
                "display_name": _sql_display_name(sql_row),
                "metrics": {
                    "response_time_ms": sql_row.get("response_time_ms") or sql_row.get("respTime"),
                    "error_count": sql_row.get("error_count") or sql_row.get("errorCount"),
                    "count": sql_row.get("count"),
                },
                "evidence_refs": ["database_analysis"],
            }
        )
    return objects


def _comparison_result(current_item: Optional[dict[str, Any]], previous_item: Optional[dict[str, Any]]) -> tuple[str, dict[str, Any], str, str]:
    if current_item and not previous_item:
        return "new_risk", _metrics_only(current_item), "Object appears in current window but not in baseline.", "medium"
    if previous_item and not current_item:
        return "disappeared", _metrics_only(previous_item), "Object disappeared from current window.", "medium"
    if not current_item or not previous_item:
        return "insufficient_baseline", {}, "Baseline is unavailable.", "low"

    current_metrics = current_item.get("metrics") or {}
    previous_metrics = previous_item.get("metrics") or {}
    delta_metrics = {}
    regressed = False
    improved = False
    for key, threshold in COMPARISON_THRESHOLDS.items():
        current_value = _numeric(current_metrics.get(key))
        previous_value = _numeric(previous_metrics.get(key))
        if current_value is None or previous_value is None:
            continue
        delta = round(current_value - previous_value, 3)
        ratio = delta / previous_value if previous_value not in (0, None) else None
        delta_metrics[key] = {"current": current_value, "previous": previous_value, "delta": delta, "ratio": ratio}
        if delta >= threshold["min_delta"] and (ratio is None or ratio >= threshold["ratio"]):
            regressed = True
        if delta <= -threshold["min_delta"] and (ratio is None or ratio <= -threshold["ratio"]):
            improved = True

    if regressed and not improved:
        return "regressed", delta_metrics, "Current window is worse than the previous window on the same object key.", "medium"
    if improved and not regressed:
        return "improved", delta_metrics, "Current window improved compared with the previous window.", "medium"
    return "stable_risk", delta_metrics, "Object exists in both windows without a strong directional change.", "low"


def _previous_window_context(context: AnalysisContext) -> Optional[AnalysisContext]:
    parsed = _parse_end_time(context.time_window.end_time)
    if parsed is None:
        return None
    shifted_end = parsed - timedelta(minutes=context.time_window.period_minutes)
    return AnalysisContext(
        base_url=context.base_url,
        biz_system_id=context.biz_system_id,
        time_window=type(context.time_window)(end_time=shifted_end.strftime("%Y-%m-%d %H:%M"), period_minutes=context.time_window.period_minutes),
        auth=context.auth,
        lang=context.lang,
        timezone=context.timezone,
    )


def _metrics_only(item: dict[str, Any]) -> dict[str, Any]:
    return dataclass_to_dict(item.get("metrics") or {})


def _route_pattern_from_action_name(action_name: str) -> Optional[str]:
    if not action_name.lower().startswith("uri/"):
        return None
    route = "/" + action_name[4:].lstrip("/")
    return route if route else None


def _page_name_from_route(route: str) -> str:
    return route.strip("/").split("/")[-1] or route


def _page_signals(action: dict[str, Any], user_edge: dict[str, Any], dependencies: list[dict[str, Any]]) -> list[dict[str, Any]]:
    signals: list[dict[str, Any]] = []
    response_time = _numeric((action.get("metrics") or {}).get("response_time_ms"))
    error_count = _numeric((action.get("metrics") or {}).get("error_count"))
    user_response = _numeric(user_edge.get("response_time_ms"))
    if response_time is not None and response_time >= 1000:
        signals.append({"type": "page_backend_response_high_ms", "value": response_time, "level": "high"})
    if user_response is not None and user_response >= 1000:
        signals.append({"type": "user_entry_response_high_ms", "value": user_response, "level": "high"})
    if error_count and error_count > 0:
        signals.append({"type": "backend_error_count_present", "value": int(error_count), "level": "high"})
    if any((_numeric(dep.get("response_time_ms")) or 0) >= 1000 for dep in dependencies):
        signals.append({"type": "external_dependency_pressure", "value": True, "level": "medium"})
    return signals


def _page_impact_hints(action: dict[str, Any], user_edge: dict[str, Any], dependencies: list[dict[str, Any]]) -> list[str]:
    hints: list[str] = []
    if _numeric(user_edge.get("response_time_ms")) and _numeric(user_edge.get("response_time_ms")) >= 1000:
        hints.append("real_user_entry_slow")
    if _numeric((action.get("metrics") or {}).get("error_count")) and _numeric((action.get("metrics") or {}).get("error_count")) > 0:
        hints.append("backend_errors_visible_to_user")
    if dependencies:
        hints.append("possible_backend_or_dependency_contribution")
    return hints


def _sql_display_name(sql_row: dict[str, Any]) -> str:
    text = sql_row.get("op_name_decoded") or sql_row.get("opName") or sql_row.get("op_name_raw") or "sql"
    text = re.sub(r"\s+", " ", str(text)).strip()
    return text[:160]


def _sql_fingerprint(value: Any) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip().lower()
    return text[:200]


def _ref_key(target_ref: Any) -> str:
    if not isinstance(target_ref, dict):
        return str(target_ref)
    kind = str(target_ref.get("kind") or "unknown")
    ordered = [f"{key}={target_ref[key]}" for key in sorted(target_ref.keys()) if key != "kind"]
    return f"{kind}|" + "|".join(ordered)


def _merge_evidence(*groups: list[Any]) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for group in groups:
        for item in group or []:
            if not isinstance(item, dict):
                continue
            key = (str(item.get("id") or ""), str(item.get("source_api") or item.get("sourceApi") or ""))
            if key in seen:
                continue
            seen.add(key)
            merged.append(item)
    return merged


def _merge_evidence_objects(items: list[Any]) -> list[Evidence]:
    return _coerce_evidence_list(items)


def _unique_refs(refs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    result: list[dict[str, Any]] = []
    for ref in refs:
        key = _ref_key(ref)
        if key in seen:
            continue
        seen.add(key)
        result.append(ref)
    return result


def _unique_list(items: list[str]) -> list[str]:
    return list(dict.fromkeys(item for item in items if item))


def _first_label(labels: list[str], candidates: tuple[str, ...]) -> str:
    for candidate in candidates:
        if candidate in labels:
            return candidate
    return "unknown"


def _parse_timestamp(value: Any) -> Optional[datetime]:
    numeric = _numeric(value)
    if numeric is None:
        return None
    try:
        return datetime.fromtimestamp(numeric / 1000.0)
    except Exception:
        return None


def _parse_end_time(value: str) -> Optional[datetime]:
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None
