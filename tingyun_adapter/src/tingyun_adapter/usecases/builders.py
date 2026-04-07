from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from typing import Any, Iterable, Optional

from tingyun_adapter.domain.enums import PackType, TraceSelectionStrategy
from tingyun_adapter.domain.models.common import (
    ActionRef,
    AnalysisContext,
    Evidence,
    HotspotPolicy,
    PackEnvelope,
    PackMeta,
    TimeWindow,
    TraceRef,
    TraceSelectionPolicy,
    WarningMessage,
    dataclass_to_dict,
)
from tingyun_adapter.domain.models.entities import Action, ActionHotspot, BizSystem, Trace
from tingyun_adapter.domain.models.packs import (
    ActionHotspotPackPayload,
    ActionFactSheetPayload,
    DiagnosticCandidatePackPayload,
    ReportFactPackPayload,
    SystemSnapshotPayload,
    TraceFactSheetPayload,
    TraceCasePackPayload,
)
from tingyun_adapter.normalizers.field_normalizer import unwrap_data
from tingyun_adapter.normalizers.metric_normalizer import normalize_metric_fields
from tingyun_adapter.normalizers.trace_key_resolver import resolve_trace_keys
from tingyun_adapter.usecases.report_support import (
    apply_report_support,
    default_coverage_boundary,
    make_console_link,
    make_metric_semantic,
    make_screenshot_hint,
    time_window_text,
)
from tingyun_adapter.usecases.report_fact_enhancements import (
    build_issue_inventory,
    build_report_pack_exports,
    build_template_mapping,
    build_writer_input,
    render_sql_section_markdown,
    render_template_outline_markdown,
    render_writer_input_markdown,
    sql_fingerprint,
    union_sql_candidates,
)


def build_system_snapshot(adapter: Any, context: AnalysisContext, *, source_mode: str = "auto") -> PackEnvelope:
    warnings: list[WarningMessage] = []
    evidence: list[Evidence] = []

    overview_payload = _load_business_overview(adapter, context, source_mode=source_mode)
    health_payload = _load_health_statistics(adapter, context, source_mode=source_mode)
    trends_payload = _load_trends(adapter, context, source_mode=source_mode)

    overview = unwrap_data(overview_payload) or {}
    health = unwrap_data(health_payload) or {}
    trends = {name: _summarize_chart(chart_payload) for name, chart_payload in trends_payload.items()}
    suspect_signals = _system_suspect_signals(overview, health, trends)

    if not overview:
        warnings.append(WarningMessage(code="missing_business_overview", message="Business overview is empty for the requested context.", source_api="application/business/overview"))
    if not health:
        warnings.append(WarningMessage(code="missing_health_statistics", message="Health statistics are empty for the requested context.", source_api="health/healthLevelStatistics"))

    biz_system = BizSystem(
        id=context.biz_system_id,
        name=overview.get("bizSystemName"),
        overview=overview,
        health=health,
        applications=_ensure_int_list(overview.get("applicationIds")),
        instances=_ensure_int_list(overview.get("instanceIds")),
        actions=_ensure_int_list(overview.get("actionIds")),
        evidence=[],
    )

    evidence.extend(
        [
            _evidence(
                evidence_id="system_overview",
                source_api="application/business/overview",
                source_path=f"/server-api/application/business/overview/{context.biz_system_id}",
                source_method="POST",
                request_params={"bizSystemId": context.biz_system_id, "timeWindow": dataclass_to_dict(context.time_window)},
                response_excerpt=_excerpt(overview, ["bizSystemName", "applicationIds", "instanceIds", "response", "throught", "apdex", "slowCount"]),
            ),
            _evidence(
                evidence_id="health_level_statistics",
                source_api="health/healthLevelStatistics",
                source_path="/server-api/health/healthLevelStatistics",
                source_method="POST",
                request_params={"bizSystemId": context.biz_system_id, "timeWindow": dataclass_to_dict(context.time_window)},
                response_excerpt=health,
            ),
            _evidence(
                evidence_id="application_trends",
                source_api="application/charts/*",
                source_path="/server-api/application/charts/{response,throught,error}",
                source_method="POST",
                request_params={"bizSystemId": context.biz_system_id, "timeWindow": dataclass_to_dict(context.time_window)},
                response_excerpt=trends,
            ),
        ]
    )

    payload = SystemSnapshotPayload(
        biz_system=dataclass_to_dict(biz_system),
        overview=overview,
        health=health,
        trends=trends,
        suspect_signals=suspect_signals,
        evidence=[dataclass_to_dict(item) for item in evidence],
    )
    page_links = [
        make_console_link(
            adapter,
            context,
            page_type="business_system_overview",
            label="业务系统总览页",
            why_relevant="用于查看业务系统健康度、响应时间、吞吐率、错误率和 Apdex 趋势。",
            suggested_report_section="3.1 业务系统总体检查",
            navigation_path=["业务系统", str(context.biz_system_id), "总览"],
            suggested_filters={"time_window": dataclass_to_dict(context.time_window)},
            target_ref={"kind": "biz_system", "biz_system_id": context.biz_system_id},
        ),
        make_console_link(
            adapter,
            context,
            page_type="business_system_topology",
            label="业务系统拓扑页",
            why_relevant="用于查看系统级依赖、外部服务和数据库拓扑。",
            suggested_report_section="3.7 运行环境与基础设施关联检查",
            navigation_path=["业务系统", str(context.biz_system_id), "拓扑"],
            suggested_filters={"time_window": dataclass_to_dict(context.time_window)},
            target_ref={"kind": "biz_system", "biz_system_id": context.biz_system_id},
        ),
    ]
    screenshot_hints = [
        make_screenshot_hint(
            title="业务系统总览趋势截图建议",
            page_type="business_system_overview",
            url=page_links[0]["url"],
            recommended_capture=["响应时间趋势图", "错误率趋势图", "Apdex / 健康度摘要"],
            recommended_annotations=["圈出异常时间窗", "标注 P99 抬升时段", "标注 action 告警数量"],
            usage_in_report="适合用于 3.1 业务系统总体检查 的总体判断。",
            suggested_report_section="3.1 业务系统总体检查",
            target_ref={"kind": "biz_system", "biz_system_id": context.biz_system_id},
            priority="high",
        ),
        make_screenshot_hint(
            title="业务系统拓扑截图建议",
            page_type="business_system_topology",
            url=page_links[1]["url"],
            recommended_capture=["业务系统拓扑图", "外部依赖节点", "数据库与应用节点关系"],
            recommended_annotations=["圈出异常依赖方向", "标出关键数据库组件", "标出用户入口应用"],
            usage_in_report="适合用于 3.7 运行环境与基础设施关联检查。",
            suggested_report_section="3.7 运行环境与基础设施关联检查",
            target_ref={"kind": "biz_system", "biz_system_id": context.biz_system_id},
            priority="medium",
        ),
    ]
    metric_semantics = [
        make_metric_semantic(metric_name="avg_response_time", subject_type="business_system", subject_key=f"biz_system:{context.biz_system_id}", aggregation="average", unit="ms", time_window=time_window_text(context), sample_scope="all requests in selected business scope"),
        make_metric_semantic(metric_name="avg_throughput", subject_type="business_system", subject_key=f"biz_system:{context.biz_system_id}", aggregation="average", unit="tps", time_window=time_window_text(context), sample_scope="all requests in selected business scope"),
        make_metric_semantic(metric_name="avg_error_rate", subject_type="business_system", subject_key=f"biz_system:{context.biz_system_id}", aggregation="average", unit="%", time_window=time_window_text(context), sample_scope="all requests in selected business scope"),
        make_metric_semantic(metric_name="apdex", subject_type="business_system", subject_key=f"biz_system:{context.biz_system_id}", aggregation="summary", unit="score", time_window=time_window_text(context), sample_scope="all requests in selected business scope"),
    ]
    payload = apply_report_support(
        payload,
        page_links=page_links,
        screenshot_hints=screenshot_hints,
        metric_semantics=metric_semantics,
        coverage_boundary=default_coverage_boundary(adapter),
        evidence_linkage={
            "related_time_windows": [((trends.get("response") or {}).get("latest_point") or {}).get("startTime"), ((trends.get("response") or {}).get("latest_point") or {}).get("endTime")],
            "related_actions": [],
            "related_traces": [],
            "related_sqls": [],
            "related_dependencies": ["business_system_topology"],
            "recommended_next_pages": ["business_system_overview", "business_system_topology"],
        },
    )
    return _pack(PackType.SYSTEM_SNAPSHOT.value, context, payload, evidence=evidence, warnings=warnings, source_mode=source_mode)


def build_action_hotspot_pack(
    adapter: Any,
    context: AnalysisContext,
    *,
    source_mode: str = "auto",
    policy: Optional[HotspotPolicy] = None,
    application_id: int = 0,
) -> PackEnvelope:
    policy = policy or HotspotPolicy()
    warnings: list[WarningMessage] = []
    evidence: list[Evidence] = []

    actions_payload = _load_action_list(adapter, context, source_mode=source_mode, application_id=application_id)
    action_rows = _extract_action_rows(actions_payload)
    normalized_rows = [normalize_metric_fields(dict(row)) for row in action_rows]
    sorted_rows = sorted(
        normalized_rows,
        key=lambda item: (_numeric(item.get(policy.sort_by)), _numeric(item.get(policy.secondary_sort_by))),
        reverse=True,
    )
    selected_rows = sorted_rows[: policy.limit]

    hotspots: list[dict[str, Any]] = []
    for rank, row in enumerate(selected_rows, start=1):
        action = Action(
            id=_int_or_zero(row.get("actionId")),
            biz_system_id=context.biz_system_id,
            application_id=_int_or_zero(row.get("applicationId")),
            type=str(row.get("actionType") or "TX"),
            name=row.get("actionName"),
            alias=row.get("actionAlias") or row.get("alias"),
            metrics={
                "response_time_ms": row.get("response_time_ms"),
                "total_response_time_ms": row.get("total_response_time_ms"),
                "throughput": row.get("throughput"),
                "error_count": row.get("error_count"),
                "slow_count": row.get("slowCount"),
                "count": row.get("count"),
            },
        )
        hotspot = ActionHotspot(
            action_id=action.id,
            application_id=action.application_id,
            biz_system_id=context.biz_system_id,
            ranking_basis=[policy.sort_by, policy.secondary_sort_by],
            severity_score=_severity_from_action(row),
            why_selected=_why_action_selected(row),
        )
        hotspots.append(
            {
                "rank": rank,
                "action": dataclass_to_dict(action),
                "hotspot": dataclass_to_dict(hotspot),
                "suspect_signals": _action_suspect_signals(row),
                "raw": row,
            }
        )

    top_overview: dict[str, Any] | None = None
    if hotspots:
        top_action = hotspots[0]["action"]
        top_overview = _load_matching_action_overview(
            adapter,
            context,
            source_mode=source_mode,
            action_id=int(top_action["id"]),
            application_id=int(top_action["application_id"]),
            action_type=str(top_action["type"]),
        )
        if top_overview:
            hotspots[0]["overview"] = unwrap_data(top_overview) or {}
        else:
            warnings.append(WarningMessage(code="missing_action_overview", message="No matching action overview was found for the selected hottest action.", source_api="webaction/overview"))

    evidence.append(
        _evidence(
            evidence_id="action_list",
            source_api="webaction/list/actionList",
            source_path="/server-api/webaction/list/actionList",
            source_method="POST",
            request_params={"bizSystemId": context.biz_system_id, "timeWindow": dataclass_to_dict(context.time_window)},
            response_excerpt={"top_rows": hotspots[:3]},
        )
    )
    if top_overview:
        evidence.append(
            _evidence(
                evidence_id="action_overview",
                source_api="webaction/overview",
                source_path="/server-api/webaction/overview",
                source_method="POST",
                request_params={"bizSystemId": context.biz_system_id, "timeWindow": dataclass_to_dict(context.time_window)},
                response_excerpt=unwrap_data(top_overview) or {},
            )
        )

    payload = ActionHotspotPackPayload(
        ranking_policy=dataclass_to_dict(policy),
        hotspots=hotspots,
        suspect_signals=_aggregate_action_signals(hotspots),
        evidence=[dataclass_to_dict(item) for item in evidence],
    )
    top_action = (hotspots[0].get("action") or {}) if hotspots else {}
    page_links = [
        make_console_link(
            adapter,
            context,
            page_type="action_hotspot_list",
            label="事务与接口热点列表页",
            why_relevant="用于查看慢接口 Top、高错误接口和热点事务列表。",
            suggested_report_section="3.3 事务与服务接口检查",
            navigation_path=["应用", str(top_action.get("application_id") or context.biz_system_id), "事务与服务接口", "热点列表"],
            suggested_filters={"time_window": dataclass_to_dict(context.time_window), "sort_by": policy.sort_by},
            target_ref=_action_target_ref_for_support(top_action),
        )
    ]
    if top_action:
        page_links.append(
            make_console_link(
                adapter,
                context,
                page_type="action_overview",
                label="热点接口详情页",
                why_relevant="用于查看重点接口概览、下游组件和 trace 候选。",
                suggested_report_section="3.3 事务与服务接口检查",
                navigation_path=["应用", str(top_action.get("application_id")), "事务与服务接口", str(top_action.get("id"))],
                suggested_filters={"action_type": top_action.get("type"), "time_window": dataclass_to_dict(context.time_window)},
                target_ref=_action_target_ref_for_support(top_action),
            )
        )
    payload = apply_report_support(
        payload,
        page_links=page_links,
        screenshot_hints=[
            make_screenshot_hint(
                title="热点接口列表截图建议",
                page_type="action_hotspot_list",
                url=page_links[0]["url"],
                recommended_capture=["Top 请求列表", "Top 错误列表", "排序列高亮"],
                recommended_annotations=["圈出最慢接口", "标注错误率或 slowCount", "标注对应应用"],
                usage_in_report="适合用于 3.3 事务与服务接口检查 的对象排序说明。",
                suggested_report_section="3.3 事务与服务接口检查",
                target_ref=_action_target_ref_for_support(top_action),
                priority="high",
            )
        ],
        metric_semantics=[
            make_metric_semantic(metric_name="response_time_ms", subject_type="action", subject_key=f"action:{top_action.get('id') or 'hotspots'}", aggregation="average", unit="ms", time_window=time_window_text(context), sample_scope="selected hotspot actions"),
            make_metric_semantic(metric_name="error_count", subject_type="action", subject_key=f"action:{top_action.get('id') or 'hotspots'}", aggregation="count", unit="count", time_window=time_window_text(context), sample_scope="selected hotspot actions"),
        ],
        coverage_boundary=default_coverage_boundary(adapter),
        evidence_linkage={
            "related_time_windows": [],
            "related_actions": [_action_target_ref_for_support(item.get("action") or {}) for item in hotspots[:5]],
            "related_traces": [],
            "related_sqls": [],
            "related_dependencies": [],
            "recommended_next_pages": [item["page_type"] for item in page_links],
        },
    )
    return _pack(PackType.ACTION_HOTSPOT.value, context, payload, evidence=evidence, warnings=warnings, source_mode=source_mode)


def build_trace_case_pack(
    adapter: Any,
    context: AnalysisContext,
    *,
    source_mode: str = "auto",
    action_ref: Optional[ActionRef] = None,
    trace_policy: Optional[TraceSelectionPolicy] = None,
) -> PackEnvelope:
    trace_policy = trace_policy or TraceSelectionPolicy()
    warnings: list[WarningMessage] = []
    evidence: list[Evidence] = []

    selector: dict[str, Any]
    trace_detail_payload: dict[str, Any] | None = None
    call_tree_payload: dict[str, Any] | None = None
    exceptions_payload: Any = None

    if _should_use_sample(adapter, source_mode):
        sample = _load_trace_case_from_samples(adapter, context)
        selector = sample["selector"]
        trace_detail_payload = sample["detail"]
        call_tree_payload = sample.get("call_tree")
        exceptions_payload = sample.get("exceptions")
        if sample.get("warning"):
            warnings.append(sample["warning"])
    else:
        selector, trace_detail_payload, call_tree_payload, exceptions_payload, live_warnings = _load_trace_case_live(
            adapter,
            context,
            action_ref=action_ref,
            trace_policy=trace_policy,
        )
        warnings.extend(live_warnings)

    detail = unwrap_data(trace_detail_payload) or {}
    call_tree = unwrap_data(call_tree_payload) or {}
    exceptions = unwrap_data(exceptions_payload) or []

    if not detail:
        warnings.append(WarningMessage(code="missing_trace_detail", message="Trace detail is empty for the selected trace case.", source_api="action/trace/detail"))

    trace = _trace_from_detail(detail, context.biz_system_id)
    trace.exceptions = exceptions if isinstance(exceptions, list) else []
    trace.timeline_summary = _timeline_summary(detail.get("timeLine") or {})
    trace.service_flow_summary = _service_flow_summary(detail.get("serviceFlow") or {})
    trace.topology_summary = _topology_summary(detail.get("topology") or {})

    trace_case = {
        "trace": dataclass_to_dict(trace),
        "detail_summary": _trace_detail_summary(detail),
        "call_tree_summary": _call_tree_summary(call_tree),
        "exception_summary": _exception_summary(exceptions),
        "key_sqls": _trace_key_sqls(detail),
        "primary_sql_fingerprint": _trace_primary_sql_fingerprint(detail),
        "sql_bottleneck_ratio": _trace_sql_bottleneck_ratio(detail),
        "sql_trace_binding_strength": _trace_sql_binding_strength(detail),
    }
    suspect_signals = _trace_suspect_signals(detail, trace_case["call_tree_summary"], trace_case["exception_summary"])
    drilldown_path = [
        "webaction/list/actionList",
        "graph/query/overview?trace_current_overview",
        "action/trace/detail",
        "action/trace/callTree",
        "action/trace/detail/exceptions",
    ]

    evidence.extend(
        [
            _evidence(
                evidence_id="trace_selector",
                source_api="trace_selection",
                source_path="graph/query/overview?trace_current_overview|sample",
                source_method="POST",
                request_params=selector,
                response_excerpt={"selected_trace_id": selector.get("trace_id_numeric"), "action_id": selector.get("action_id")},
            ),
            _evidence(
                evidence_id="trace_detail",
                source_api="action/trace/detail",
                source_path="/server-api/action/trace/detail",
                source_method="POST",
                request_params=selector,
                response_excerpt=_trace_detail_summary(detail),
            ),
        ]
    )
    if call_tree:
        evidence.append(
            _evidence(
                evidence_id="trace_call_tree",
                source_api="action/trace/callTree",
                source_path="/server-api/action/trace/callTree",
                source_method="POST",
                request_params=selector,
                response_excerpt=_call_tree_summary(call_tree),
            )
        )
    if exceptions:
        evidence.append(
            _evidence(
                evidence_id="trace_exceptions",
                source_api="action/trace/detail/exceptions",
                source_path="/server-api/action/trace/detail/exceptions",
                source_method="POST",
                request_params=selector,
                response_excerpt=_exception_summary(exceptions),
            )
        )

    payload = TraceCasePackPayload(
        selector=selector,
        trace_case=trace_case,
        suspect_signals=suspect_signals,
        drilldown_path=drilldown_path,
        evidence=[dataclass_to_dict(item) for item in evidence],
    )
    trace_info = trace_case.get("trace") or {}
    page_links = [
        make_console_link(
            adapter,
            context,
            page_type="trace_detail",
            label="请求追踪详情页",
            why_relevant="用于查看代表性 trace 的时间线、可疑节点和调用树。",
            suggested_report_section="3.5 请求追踪与根因分析专题",
            navigation_path=["请求追踪", str(trace_info.get("trace_id_numeric") or selector.get("trace_id_numeric") or "")],
            suggested_filters={"trace_guid": trace_info.get("trace_guid") or selector.get("trace_guid"), "time_window": dataclass_to_dict(context.time_window)},
            target_ref={"kind": "trace", "trace_id_numeric": trace_info.get("trace_id_numeric"), "trace_guid": trace_info.get("trace_guid")},
        )
    ]
    payload = apply_report_support(
        payload,
        page_links=page_links,
        screenshot_hints=[
            make_screenshot_hint(
                title="代表性 Trace 详情截图建议",
                page_type="trace_detail",
                url=page_links[0]["url"],
                recommended_capture=["Trace 时间线", "可疑问题节点列表", "调用树摘要"],
                recommended_annotations=["圈出最长耗时段", "标注数据库/外部依赖节点", "标注 trace id"],
                usage_in_report="适合用于 3.5 请求追踪与根因分析专题。",
                suggested_report_section="3.5 请求追踪与根因分析专题",
                target_ref={"kind": "trace", "trace_id_numeric": trace_info.get("trace_id_numeric"), "trace_guid": trace_info.get("trace_guid")},
                priority="high",
            )
        ],
        metric_semantics=[
            make_metric_semantic(metric_name="duration_ms", subject_type="trace", subject_key=f"trace:{trace_info.get('trace_id_numeric') or selector.get('trace_id_numeric')}", aggregation="sample", unit="ms", time_window=time_window_text(context), sample_scope="selected representative trace", confidence="high")
        ],
        coverage_boundary=default_coverage_boundary(adapter),
        evidence_linkage={
            "related_time_windows": [trace_case.get("detail_summary", {}).get("timestamp")],
            "related_actions": [{"kind": "action", "action_id": trace_info.get("action_id"), "application_id": trace_info.get("application_id"), "biz_system_id": trace_info.get("biz_system_id")}],
            "related_traces": [{"kind": "trace", "trace_id_numeric": trace_info.get("trace_id_numeric"), "trace_guid": trace_info.get("trace_guid")}],
            "related_sqls": [],
            "related_dependencies": [item.get("metricName") for item in (trace_info.get("suspected_problems") or []) if item.get("metricType") in {"DATABASE", "EXTERNAL", "NoSQL", "POOL"}],
            "recommended_next_pages": ["trace_detail"],
        },
    )
    return _pack(PackType.TRACE_CASE.value, context, payload, evidence=evidence, warnings=warnings, source_mode=source_mode)


def build_report_fact_pack(adapter: Any, context: AnalysisContext, *, source_mode: str = "auto") -> PackEnvelope:
    warnings: list[WarningMessage] = []
    missing_inputs: list[str] = []

    from tingyun_adapter.domain.models.common import DatabaseComponentRef
    from tingyun_adapter.usecases.enhancement_builders import build_page_experience_pack
    from tingyun_adapter.usecases.extended_builders import build_slow_sql_pack, build_sql_fact_sheet

    system_snapshot = build_system_snapshot(adapter, context, source_mode=source_mode)
    action_hotspots = build_action_hotspot_pack(adapter, context, source_mode=source_mode)
    trace_case_envelope = build_trace_case_pack(adapter, context, source_mode=source_mode)
    slow_sql = build_slow_sql_pack(adapter, context, source_mode=source_mode, limit=20)
    page_pack = build_page_experience_pack(adapter, context, source_mode=source_mode, limit=5)

    for envelope in (system_snapshot, action_hotspots, trace_case_envelope, slow_sql, page_pack):
        warnings.extend(envelope.meta.warnings)
        missing_inputs.extend(envelope.meta.missing_inputs)

    snapshot_payload = system_snapshot.to_dict()["payload"]
    hotspot_payload = action_hotspots.to_dict()["payload"]
    trace_payload = trace_case_envelope.to_dict()["payload"]
    slow_sql_payload = slow_sql.to_dict()["payload"]
    page_payload = page_pack.to_dict()["payload"]

    top_hotspot = (hotspot_payload.get("hotspots") or [{}])[0]
    report_scope = {
        "bizSystemId": context.biz_system_id,
        "endTime": context.time_window.end_time,
        "periodMinutes": context.time_window.period_minutes,
        "sourceMode": source_mode,
    }
    summary = {
        "biz_system_name": snapshot_payload.get("biz_system", {}).get("name"),
        "avg_response_time_ms": snapshot_payload.get("overview", {}).get("response"),
        "avg_throughput": snapshot_payload.get("overview", {}).get("throught"),
        "apdex": snapshot_payload.get("overview", {}).get("apdex"),
        "health_overview": snapshot_payload.get("health", {}),
        "top_action_name": top_hotspot.get("action", {}).get("name"),
        "top_action_response_time_ms": top_hotspot.get("action", {}).get("metrics", {}).get("response_time_ms"),
        "trace_case_action_name": trace_payload.get("trace_case", {}).get("detail_summary", {}).get("actionName"),
        "trace_case_duration_ms": trace_payload.get("trace_case", {}).get("trace", {}).get("duration_ms"),
        "sql_candidate_count": len(slow_sql_payload.get("top_sqls") or []),
        "page_count": len(page_payload.get("pages") or []),
    }

    sql_rows = list(slow_sql_payload.get("top_sqls") or [])
    sql_fact_payloads: dict[str, dict[str, Any]] = {}
    for row in _select_sql_enrichment_rows(sql_rows):
        component_name = row.get("component_name") or row.get("componentName")
        if not component_name:
            continue
        sql_fact = build_sql_fact_sheet(
            adapter,
            context,
            source_mode=source_mode,
            component_ref=DatabaseComponentRef(
                biz_system_id=context.biz_system_id,
                component_name=str(component_name),
                component_subtype=row.get("component_subtype") or row.get("componentSubtype"),
            ),
            op_name=row.get("op_name_decoded") or row.get("opName"),
            limit=5,
        )
        warnings.extend(sql_fact.meta.warnings)
        missing_inputs.extend(sql_fact.meta.missing_inputs)
        sql_fact_payload = sql_fact.to_dict()["payload"]
        fingerprint = sql_fingerprint(
            str(
                (sql_fact_payload.get("sql") or {}).get("op_name_decoded")
                or (sql_fact_payload.get("sql") or {}).get("opName")
                or row.get("op_name_decoded")
                or row.get("opName")
                or ""
            )
        )
        sql_fact_payloads[fingerprint] = sql_fact_payload

    sql_inventory = union_sql_candidates(
        sql_rows,
        trace_case=trace_payload.get("trace_case") or {},
        sql_fact_payloads=sql_fact_payloads,
    )
    enriched_trace_case = _enrich_trace_case_with_sql(trace_payload.get("trace_case") or {}, sql_inventory.get("sql_candidates") or [])
    issue_inventory = build_issue_inventory(
        summary=summary,
        snapshot_payload=snapshot_payload,
        hotspot_payload=hotspot_payload,
        trace_payload={"trace_case": enriched_trace_case},
        sql_main_candidates=sql_inventory.get("sql_main_candidates") or [],
        sql_opportunities=sql_inventory.get("sql_opportunities") or [],
    )
    screenshot_index_rows = _build_screenshot_index_rows(
        snapshot_payload,
        hotspot_payload,
        trace_payload,
        slow_sql_payload,
        page_payload,
    )
    screenshot_index_summary = {
        "card_count": len(screenshot_index_rows),
        "direct_card_count": len([item for item in screenshot_index_rows if item.get("url_status") == "direct"]),
        "navigation_only_count": len([item for item in screenshot_index_rows if item.get("url_status") == "navigation_only"]),
        "sections_with_screenshots": sorted({item.get("suggested_report_section") for item in screenshot_index_rows if item.get("suggested_report_section")}),
    }
    template_mapping = build_template_mapping(
        issues=issue_inventory.get("issues") or [],
        observations=issue_inventory.get("observations") or [],
        sql_main_candidates=sql_inventory.get("sql_main_candidates") or [],
        sql_opportunities=sql_inventory.get("sql_opportunities") or [],
        page_boundary=page_payload.get("coverage_boundary") or snapshot_payload.get("coverage_boundary") or {},
    )
    writer_input = build_writer_input(
        report_scope=report_scope,
        summary=summary,
        coverage_boundary=page_payload.get("coverage_boundary") or snapshot_payload.get("coverage_boundary") or default_coverage_boundary(adapter),
        issues=issue_inventory.get("issues") or [],
        observations=issue_inventory.get("observations") or [],
        sql_main_candidates=sql_inventory.get("sql_main_candidates") or [],
        sql_opportunities=sql_inventory.get("sql_opportunities") or [],
        trace_case=enriched_trace_case,
        page_payload=page_payload,
        screenshot_index_summary=screenshot_index_summary,
        template_mapping=template_mapping,
    )
    writer_markdown = render_writer_input_markdown(writer_input)
    template_outline_markdown = render_template_outline_markdown(template_mapping)
    sql_section_markdown = render_sql_section_markdown(
        summary=summary,
        slow_sql_overview=slow_sql_payload.get("operation_overview") or {},
        sql_main_candidates=sql_inventory.get("sql_main_candidates") or [],
        sql_opportunities=sql_inventory.get("sql_opportunities") or [],
    )
    report_pack_exports = build_report_pack_exports(
        issues=issue_inventory.get("issues") or [],
        observations=issue_inventory.get("observations") or [],
        issue_candidates=issue_inventory.get("issue_candidates") or [],
        sql_candidates=sql_inventory.get("sql_candidates") or [],
        sql_opportunities=sql_inventory.get("sql_opportunities") or [],
        writer_input=writer_input,
        writer_markdown=writer_markdown,
        template_outline_markdown=template_outline_markdown,
        sql_section_markdown=sql_section_markdown,
        screenshot_index_rows=screenshot_index_rows,
    )

    payload = ReportFactPackPayload(
        report_scope=report_scope,
        summary=summary,
        hotspots={
            "actions": hotspot_payload.get("hotspots", []),
            "screenshot_index_summary": screenshot_index_summary,
        },
        components={
            "action_component_summary": top_hotspot.get("overview", {}).get("components", {}),
            "slow_sql_overview": slow_sql_payload.get("operation_overview", {}),
            "page_performance_summary": page_payload.get("performance_summary", {}),
        },
        trace_case=enriched_trace_case,
        issues=issue_inventory.get("legacy_issues") or [],
        observations=issue_inventory.get("observations") or [],
        issue_candidates=issue_inventory.get("issue_candidates") or [],
        sql_main_candidates=sql_inventory.get("sql_main_candidates") or [],
        sql_opportunities=sql_inventory.get("sql_opportunities") or [],
        sql_candidates=sql_inventory.get("sql_candidates") or [],
        report_writer_input=writer_input,
        template_mapping=template_mapping,
        report_pack_exports=report_pack_exports,
        drilldown_paths=trace_payload.get("drilldown_path", []) + ["Database/analysis", "component/database/actionList", "component/database/actionTraceList"],
        evidence=(
            snapshot_payload.get("evidence", [])
            + hotspot_payload.get("evidence", [])
            + trace_payload.get("evidence", [])
            + slow_sql_payload.get("evidence", [])
            + page_payload.get("evidence", [])
            + [entry for item in sql_fact_payloads.values() for entry in (item.get("evidence") or [])]
        ),
    )
    page_links = _aggregate_report_page_links(
        snapshot_payload,
        hotspot_payload,
        trace_payload,
        slow_sql_payload,
        page_payload,
        *sql_fact_payloads.values(),
    )
    screenshot_hints = _aggregate_report_screenshot_hints(
        snapshot_payload,
        hotspot_payload,
        trace_payload,
        slow_sql_payload,
        page_payload,
        *sql_fact_payloads.values(),
    )
    metric_semantics = _aggregate_report_metric_semantics(
        snapshot_payload,
        hotspot_payload,
        trace_payload,
        slow_sql_payload,
        page_payload,
        *sql_fact_payloads.values(),
    )
    payload = apply_report_support(
        payload,
        page_links=page_links,
        screenshot_hints=screenshot_hints,
        metric_semantics=metric_semantics,
        coverage_boundary=page_payload.get("coverage_boundary") or snapshot_payload.get("coverage_boundary") or default_coverage_boundary(adapter),
        evidence_linkage={
            "related_time_windows": [dataclass_to_dict(context.time_window)],
            "related_actions": [item.get("action") for item in hotspot_payload.get("hotspots", [])[:5]],
            "related_traces": [enriched_trace_case.get("trace", {})],
            "related_sqls": (sql_inventory.get("sql_candidates") or [])[:10],
            "related_dependencies": page_payload.get("related_dependencies") or ["business_system_topology"],
            "recommended_next_pages": [item.get("page_type") for item in page_links[:10]],
        },
    )
    all_evidence = [
        *(_coerce_evidence_list(snapshot_payload.get("evidence", []))),
        *(_coerce_evidence_list(hotspot_payload.get("evidence", []))),
        *(_coerce_evidence_list(trace_payload.get("evidence", []))),
        *(_coerce_evidence_list(slow_sql_payload.get("evidence", []))),
        *(_coerce_evidence_list(page_payload.get("evidence", []))),
    ]
    for sql_fact_payload in sql_fact_payloads.values():
        all_evidence.extend(_coerce_evidence_list(sql_fact_payload.get("evidence", [])))
    return _pack(
        PackType.REPORT_FACT.value,
        context,
        payload,
        evidence=all_evidence,
        warnings=warnings,
        source_mode=source_mode,
        missing_inputs=sorted(set(missing_inputs)),
        confidence_notes=[
            "report_fact_pack now expands issue and SQL candidate pools before exporting writer-facing summaries.",
            "report_pack_exports is a materialization-friendly view; downstream writers may still choose custom serialization.",
        ],
        build_stats={
            "issue_count": len(issue_inventory.get("issues") or []),
            "observation_count": len(issue_inventory.get("observations") or []),
            "sql_candidate_count": len(sql_inventory.get("sql_candidates") or []),
            "sql_main_count": len(sql_inventory.get("sql_main_candidates") or []),
            "screenshot_row_count": len(screenshot_index_rows),
        },
    )


def build_diagnostic_candidate_pack(
    adapter: Any,
    context: AnalysisContext,
    *,
    source_mode: str = "auto",
    limit: int = 5,
) -> PackEnvelope:
    warnings: list[WarningMessage] = []
    snapshot = build_system_snapshot(adapter, context, source_mode=source_mode)
    hotspots = build_action_hotspot_pack(adapter, context, source_mode=source_mode)
    warnings.extend(snapshot.meta.warnings)
    warnings.extend(hotspots.meta.warnings)

    snapshot_payload = snapshot.to_dict()["payload"]
    hotspot_payload = hotspots.to_dict()["payload"]
    top_hotspots = (hotspot_payload.get("hotspots") or [])[:limit]
    top_action = top_hotspots[0] if top_hotspots else {}
    action_components = top_action.get("overview", {}).get("components", {}) if isinstance(top_action, dict) else {}

    trace_candidates = []
    if top_action:
        action_ref = ActionRef(
            biz_system_id=context.biz_system_id,
            application_id=int(top_action.get("action", {}).get("application_id") or 0),
            action_id=int(top_action.get("action", {}).get("id") or 0),
            action_type=str(top_action.get("action", {}).get("type") or "TX"),
        )
        trace_rows, trace_warning = _load_trace_candidates_for_action(adapter, context, action_ref, source_mode=source_mode, limit=limit)
        trace_candidates = [_trace_candidate_summary(row) for row in trace_rows[:limit]]
        if trace_warning:
            warnings.append(trace_warning)

    component_candidates = _component_candidates_from_action_components(action_components)
    payload = DiagnosticCandidatePackPayload(
        candidate_policy={"limit": limit, "selection": ["system_signals", "top_action_hotspots", "top_trace_candidates"]},
        system_signals=snapshot_payload.get("suspect_signals", []),
        action_candidates=top_hotspots,
        trace_candidates=trace_candidates,
        component_candidates=component_candidates,
        recommended_next_packs=_recommended_next_packs(top_action, component_candidates, trace_candidates),
        evidence=snapshot_payload.get("evidence", []) + hotspot_payload.get("evidence", []),
    )
    payload = apply_report_support(
        payload,
        page_links=(snapshot_payload.get("page_links") or []) + (hotspot_payload.get("page_links") or []),
        screenshot_hints=(hotspot_payload.get("screenshot_hints") or []),
        metric_semantics=(snapshot_payload.get("metric_semantics") or []) + (hotspot_payload.get("metric_semantics") or []),
        coverage_boundary=default_coverage_boundary(adapter),
        evidence_linkage={
            "related_time_windows": [],
            "related_actions": [item.get("action") for item in top_hotspots],
            "related_traces": trace_candidates[:5],
            "related_sqls": [],
            "related_dependencies": component_candidates,
            "recommended_next_pages": [item.get("page_type") for item in (hotspot_payload.get("page_links") or [])[:5]],
        },
    )
    all_evidence = [
        *(_coerce_evidence_list(snapshot_payload.get("evidence", []))),
        *(_coerce_evidence_list(hotspot_payload.get("evidence", []))),
    ]
    return _pack(PackType.DIAGNOSTIC_CANDIDATE.value, context, payload, evidence=all_evidence, warnings=warnings, source_mode=source_mode)


def build_action_fact_sheet(
    adapter: Any,
    context: AnalysisContext,
    *,
    source_mode: str = "auto",
    action_ref: Optional[ActionRef] = None,
    trace_limit: int = 10,
) -> PackEnvelope:
    warnings: list[WarningMessage] = []
    evidence: list[Evidence] = []

    row, resolved_ref, fallback_warnings = _resolve_action_ref(adapter, context, source_mode=source_mode, action_ref=action_ref)
    warnings.extend(fallback_warnings)
    if resolved_ref is None:
        payload = ActionFactSheetPayload(action_ref={}, evidence=[])
        return _pack(PackType.ACTION_FACT_SHEET.value, context, payload, evidence=evidence, warnings=warnings)

    normalized_row = normalize_metric_fields(dict(row)) if row else {}
    overview_payload = _load_matching_action_overview(
        adapter,
        context,
        source_mode=source_mode,
        action_id=resolved_ref.action_id,
        application_id=resolved_ref.application_id,
        action_type=resolved_ref.action_type,
    )
    overview = unwrap_data(overview_payload) or {}
    trace_rows, trace_warning = _load_trace_candidates_for_action(
        adapter,
        context,
        resolved_ref,
        source_mode=source_mode,
        limit=trace_limit,
    )
    if trace_warning:
        warnings.append(trace_warning)

    action = Action(
        id=resolved_ref.action_id,
        biz_system_id=context.biz_system_id,
        application_id=resolved_ref.application_id,
        type=resolved_ref.action_type,
        name=normalized_row.get("actionName") or overview.get("actionName"),
        alias=normalized_row.get("actionAlias") or normalized_row.get("alias") or overview.get("actionAlias"),
        metrics={
            "response_time_ms": normalized_row.get("response_time_ms"),
            "total_response_time_ms": normalized_row.get("total_response_time_ms"),
            "throughput": normalized_row.get("throughput"),
            "error_count": normalized_row.get("error_count"),
            "slow_count": normalized_row.get("slowCount"),
            "count": normalized_row.get("count"),
        },
        component_summary=overview.get("components") or {},
        trace_summary={"trace_candidate_count": len(trace_rows)},
    )

    evidence.extend(
        [
            _evidence(
                evidence_id="action_fact_action_list",
                source_api="webaction/list/actionList",
                source_path="/server-api/webaction/list/actionList",
                source_method="POST",
                request_params={"bizSystemId": context.biz_system_id, "actionId": resolved_ref.action_id},
                response_excerpt=normalized_row,
            ),
            _evidence(
                evidence_id="action_fact_overview",
                source_api="webaction/overview",
                source_path="/server-api/webaction/overview",
                source_method="POST",
                request_params={"bizSystemId": context.biz_system_id, "actionId": resolved_ref.action_id},
                response_excerpt=overview,
            ),
            _evidence(
                evidence_id="action_fact_trace_candidates",
                source_api="graph/query/overview",
                source_path="/server-api/graph/query/overview?trace_current_overview",
                source_method="POST",
                request_params={"bizSystemId": context.biz_system_id, "actionId": resolved_ref.action_id},
                response_excerpt={"trace_candidates": [_trace_candidate_summary(item) for item in trace_rows[:3]]},
            ),
        ]
    )

    payload = ActionFactSheetPayload(
        action_ref=dataclass_to_dict(resolved_ref),
        action=dataclass_to_dict(action),
        overview=overview,
        suspect_signals=_action_suspect_signals(normalized_row, overview=overview, trace_rows=trace_rows),
        trace_candidates=[_trace_candidate_summary(item) for item in trace_rows[:trace_limit]],
        downstream_components=_summarize_action_components(overview.get("components") or {}),
        drilldown_keys={
            "bizSystemId": context.biz_system_id,
            "applicationId": resolved_ref.application_id,
            "actionId": resolved_ref.action_id,
            "actionType": resolved_ref.action_type,
            "traceCandidateKeys": [_trace_candidate_keys(item) for item in trace_rows[:3]],
        },
        drilldown_path=[
            "webaction/list/actionList",
            "webaction/overview",
            "graph/query/overview?trace_current_overview",
            "action/trace/detail",
        ],
        evidence=[dataclass_to_dict(item) for item in evidence],
    )
    page_links = [
        make_console_link(
            adapter,
            context,
            page_type="action_overview",
            label="接口/事务详情页",
            why_relevant="用于查看接口概览、错误、下游组件和关联 trace。",
            suggested_report_section="3.3 事务与服务接口检查",
            navigation_path=["应用", str(resolved_ref.application_id), "事务与服务接口", str(resolved_ref.action_id)],
            suggested_filters={"action_type": resolved_ref.action_type, "time_window": dataclass_to_dict(context.time_window)},
            target_ref={"kind": "action", "biz_system_id": context.biz_system_id, "application_id": resolved_ref.application_id, "action_id": resolved_ref.action_id, "action_type": resolved_ref.action_type},
        )
    ]
    if trace_rows:
        trace_candidate = _trace_candidate_summary(trace_rows[0])
        page_links.append(
            make_console_link(
                adapter,
                context,
                page_type="trace_detail",
                label="相关 Trace 页",
                why_relevant="用于查看该接口的代表性 trace、瓶颈段和可疑节点。",
                suggested_report_section="3.5 请求追踪与根因分析专题",
                navigation_path=["请求追踪", str(trace_candidate.get("trace_id_numeric") or "")],
                suggested_filters={"trace_guid": trace_candidate.get("trace_guid"), "time_window": dataclass_to_dict(context.time_window)},
                target_ref={"kind": "trace", "trace_id_numeric": trace_candidate.get("trace_id_numeric"), "trace_guid": trace_candidate.get("trace_guid")},
            )
        )
    payload = apply_report_support(
        payload,
        page_links=page_links,
        screenshot_hints=[
            make_screenshot_hint(
                title="接口详情截图建议",
                page_type="action_overview",
                url=page_links[0]["url"],
                recommended_capture=["接口概览卡片", "下游组件分解", "关联 trace 列表"],
                recommended_annotations=["标注接口名称", "标注平均响应时间/错误率", "标注主要下游组件"],
                usage_in_report="适合用于 3.3 事务与服务接口检查。",
                suggested_report_section="3.3 事务与服务接口检查",
                target_ref={"kind": "action", "action_id": resolved_ref.action_id, "application_id": resolved_ref.application_id},
                priority="high",
            )
        ]
        + (
            [
                make_screenshot_hint(
                    title="接口关联 Trace 截图建议",
                    page_type="trace_detail",
                    url=page_links[1]["url"],
                    recommended_capture=["trace 时间线", "可疑节点", "调用树"],
                    recommended_annotations=["圈出最长耗时段", "标注 trace id", "标注数据库/依赖节点"],
                    usage_in_report="适合用于 3.5 请求追踪与根因分析专题 或 3.3 接口章节的样本说明。",
                    suggested_report_section="3.5 请求追踪与根因分析专题",
                    target_ref={"kind": "trace", "trace_id_numeric": (_trace_candidate_summary(trace_rows[0]).get('trace_id_numeric') if trace_rows else None)},
                    priority="high",
                )
            ]
            if len(page_links) > 1
            else []
        ),
        metric_semantics=[
            make_metric_semantic(metric_name="response_time_ms", subject_type="action", subject_key=f"action:{resolved_ref.action_id}", aggregation="average", unit="ms", time_window=time_window_text(context), sample_scope="selected action in requested business scope"),
            make_metric_semantic(metric_name="error_rate", subject_type="action", subject_key=f"action:{resolved_ref.action_id}", aggregation="average", unit="%", time_window=time_window_text(context), sample_scope="selected action in requested business scope"),
            make_metric_semantic(metric_name="throughput", subject_type="action", subject_key=f"action:{resolved_ref.action_id}", aggregation="average", unit="tps", time_window=time_window_text(context), sample_scope="selected action in requested business scope"),
        ],
        coverage_boundary=default_coverage_boundary(adapter),
        evidence_linkage={
            "related_time_windows": [item.get("timestamp") for item in [_trace_candidate_summary(row) for row in trace_rows[:5]]],
            "related_actions": [{"kind": "action", "action_id": resolved_ref.action_id, "application_id": resolved_ref.application_id, "biz_system_id": context.biz_system_id}],
            "related_traces": [_trace_candidate_summary(row) for row in trace_rows[:5]],
            "related_sqls": [],
            "related_dependencies": list((overview.get("components") or {}).keys()) if isinstance(overview.get("components"), dict) else [],
            "recommended_next_pages": [item["page_type"] for item in page_links],
        },
    )
    return _pack(PackType.ACTION_FACT_SHEET.value, context, payload, evidence=evidence, warnings=warnings, source_mode=source_mode)


def build_trace_fact_sheet(
    adapter: Any,
    context: AnalysisContext,
    *,
    source_mode: str = "auto",
    action_ref: Optional[ActionRef] = None,
    trace_ref: Optional[TraceRef] = None,
) -> PackEnvelope:
    warnings: list[WarningMessage] = []
    evidence: list[Evidence] = []

    if trace_ref and trace_ref.trace_id_numeric and trace_ref.query_timestamp and source_mode != "sample":
        detail = adapter.trace.trace_detail(
            biz_system_id=context.biz_system_id,
            trace_id=trace_ref.trace_id_numeric,
            query_timestamp=trace_ref.query_timestamp,
            end_time=context.time_window.end_time,
            time_period=context.time_window.period_minutes,
        )
        call_tree = None
        if trace_ref.action_guid:
            call_tree = adapter.trace.call_tree(
                biz_system_id=context.biz_system_id,
                trace_id=trace_ref.trace_id_numeric,
                action_guid=trace_ref.action_guid,
                query_timestamp=trace_ref.query_timestamp,
                end_time=context.time_window.end_time,
                time_period=context.time_window.period_minutes,
            )
        selector = dataclass_to_dict(trace_ref)
        detail_data = unwrap_data(detail) or {}
        call_tree_data = unwrap_data(call_tree) or {}
        exceptions: list[dict[str, Any]] = []
    else:
        trace_case = build_trace_case_pack(adapter, context, source_mode=source_mode, action_ref=action_ref)
        warnings.extend(trace_case.meta.warnings)
        trace_payload = trace_case.to_dict()["payload"]
        payload = TraceFactSheetPayload(
            selector=trace_payload.get("selector", {}),
            trace=trace_payload.get("trace_case", {}).get("trace", {}),
            detail_summary=trace_payload.get("trace_case", {}).get("detail_summary", {}),
            call_tree_summary=trace_payload.get("trace_case", {}).get("call_tree_summary", {}),
            exception_summary=trace_payload.get("trace_case", {}).get("exception_summary", {}),
            suspect_signals=trace_payload.get("suspect_signals", []),
            drilldown_keys=_trace_fact_drilldown_keys(trace_payload.get("selector", {}), trace_payload.get("trace_case", {}).get("trace", {})),
            drilldown_path=trace_payload.get("drilldown_path", []),
            evidence=trace_payload.get("evidence", []),
        )
        payload = apply_report_support(
            payload,
            page_links=trace_payload.get("page_links", []),
            screenshot_hints=trace_payload.get("screenshot_hints", []),
            metric_semantics=trace_payload.get("metric_semantics", []),
            coverage_boundary=trace_payload.get("coverage_boundary", default_coverage_boundary(adapter)),
            evidence_linkage=trace_payload.get("evidence_linkage", {}),
        )
        evidence.extend(_coerce_evidence_list(trace_payload.get("evidence", [])))
        return _pack(PackType.TRACE_FACT_SHEET.value, context, payload, evidence=evidence, warnings=warnings, source_mode=source_mode)

    trace = _trace_from_detail(detail_data, context.biz_system_id)
    detail_summary = _trace_detail_summary(detail_data)
    call_tree_summary = _call_tree_summary(call_tree_data)
    exception_summary = _exception_summary(exceptions)
    suspect_signals = _trace_suspect_signals(detail_data, call_tree_summary, exception_summary)
    evidence.extend(
        [
            _evidence(
                evidence_id="trace_fact_detail",
                source_api="action/trace/detail",
                source_path="/server-api/action/trace/detail",
                source_method="POST",
                request_params={"bizSystemId": context.biz_system_id, "traceId": trace_ref.trace_id_numeric if trace_ref else None},
                response_excerpt=detail_summary,
            ),
            _evidence(
                evidence_id="trace_fact_call_tree",
                source_api="action/trace/callTree",
                source_path="/server-api/action/trace/callTree",
                source_method="POST",
                request_params={"bizSystemId": context.biz_system_id, "traceId": trace_ref.trace_id_numeric if trace_ref else None},
                response_excerpt=call_tree_summary,
            ),
        ]
    )
    payload = TraceFactSheetPayload(
        selector=selector,
        trace=dataclass_to_dict(trace),
        detail_summary=detail_summary,
        call_tree_summary=call_tree_summary,
        exception_summary=exception_summary,
        suspect_signals=suspect_signals,
        drilldown_keys=_trace_fact_drilldown_keys(selector, dataclass_to_dict(trace)),
        drilldown_path=["action/trace/detail", "action/trace/callTree", "action/trace/detail/exceptions"],
        evidence=[dataclass_to_dict(item) for item in evidence],
    )
    page_links = [
        make_console_link(
            adapter,
            context,
            page_type="trace_detail",
            label="Trace 详情页",
            why_relevant="用于查看时间线、异常节点、调用树与异常详情。",
            suggested_report_section="3.5 请求追踪与根因分析专题",
            navigation_path=["请求追踪", str(trace.trace_id_numeric or selector.get("trace_id_numeric") or "")],
            suggested_filters={"trace_guid": trace.trace_guid, "query_timestamp": selector.get("query_timestamp")},
            target_ref={"kind": "trace", "trace_id_numeric": trace.trace_id_numeric, "trace_guid": trace.trace_guid},
        )
    ]
    payload = apply_report_support(
        payload,
        page_links=page_links,
        screenshot_hints=[
            make_screenshot_hint(
                title="Trace 详情截图建议",
                page_type="trace_detail",
                url=page_links[0]["url"],
                recommended_capture=["trace 时间线", "调用树", "异常或可疑节点区域"],
                recommended_annotations=["圈出最长耗时段", "标注 trace id", "标注可疑组件节点"],
                usage_in_report="适合用于 3.5 请求追踪与根因分析专题。",
                suggested_report_section="3.5 请求追踪与根因分析专题",
                target_ref={"kind": "trace", "trace_id_numeric": trace.trace_id_numeric, "trace_guid": trace.trace_guid},
                priority="high",
            )
        ],
        metric_semantics=[
            make_metric_semantic(metric_name="duration_ms", subject_type="trace", subject_key=f"trace:{trace.trace_id_numeric or 'selected'}", aggregation="sample", unit="ms", time_window=time_window_text(context), sample_scope="selected trace"),
            make_metric_semantic(metric_name="error_count", subject_type="trace", subject_key=f"trace:{trace.trace_id_numeric or 'selected'}", aggregation="count", unit="count", time_window=time_window_text(context), sample_scope="selected trace"),
        ],
        coverage_boundary=default_coverage_boundary(adapter),
        evidence_linkage={
            "related_time_windows": [detail_summary.get("timestamp")],
            "related_actions": [{"kind": "action", "action_id": trace.action_id, "application_id": trace.application_id, "biz_system_id": trace.biz_system_id}],
            "related_traces": [{"kind": "trace", "trace_id_numeric": trace.trace_id_numeric, "trace_guid": trace.trace_guid}],
            "related_sqls": [item.get("metricName") for item in (trace.suspected_problems or []) if item.get("metricType") == "DATABASE"],
            "related_dependencies": [item.get("metricName") for item in (trace.suspected_problems or []) if item.get("metricType") in {"EXTERNAL", "POOL", "NoSQL"}],
            "recommended_next_pages": ["trace_detail"],
        },
    )
    return _pack(PackType.TRACE_FACT_SHEET.value, context, payload, evidence=evidence, warnings=warnings, source_mode=source_mode)


def _action_target_ref_for_support(action: dict[str, Any]) -> dict[str, Any]:
    return {
        "kind": "action",
        "biz_system_id": action.get("biz_system_id"),
        "application_id": action.get("application_id"),
        "action_id": action.get("id"),
        "action_type": action.get("type"),
    }


def _load_business_overview(adapter: Any, context: AnalysisContext, *, source_mode: str) -> Any:
    if _should_use_sample(adapter, source_mode):
        repo = _require_repo(adapter)
        try:
            return repo.load_first_sample_response(f"application/business/overview/{context.biz_system_id}") or {}
        except FileNotFoundError:
            return {}
    return adapter.application.business_overview(
        biz_system_id=context.biz_system_id,
        end_time=context.time_window.end_time,
        time_period=context.time_window.period_minutes,
    )


def _load_health_statistics(adapter: Any, context: AnalysisContext, *, source_mode: str) -> Any:
    if _should_use_sample(adapter, source_mode):
        return _require_repo(adapter).load_first_sample_response("health/healthLevelStatistics") or {}
    return adapter.health.health_level_statistics(
        biz_system_id=context.biz_system_id,
        end_time=context.time_window.end_time,
        time_period=context.time_window.period_minutes,
    )


def _load_trends(adapter: Any, context: AnalysisContext, *, source_mode: str) -> dict[str, Any]:
    if _should_use_sample(adapter, source_mode):
        repo = _require_repo(adapter)
        return {
            "response": repo.load_first_sample_response("application/charts/response") or {},
            "throughput": repo.load_first_sample_response("application/charts/throught") or {},
            "error": repo.load_first_sample_response("application/charts/error") or {},
        }
    return {
        "response": adapter.application.response_chart(
            biz_system_id=context.biz_system_id,
            end_time=context.time_window.end_time,
            time_period=context.time_window.period_minutes,
        ),
        "throughput": adapter.application.throughput_chart(
            biz_system_id=context.biz_system_id,
            end_time=context.time_window.end_time,
            time_period=context.time_window.period_minutes,
        ),
        "error": adapter.application.error_chart(
            biz_system_id=context.biz_system_id,
            end_time=context.time_window.end_time,
            time_period=context.time_window.period_minutes,
        ),
    }


def _load_action_list(adapter: Any, context: AnalysisContext, *, source_mode: str, application_id: int) -> Any:
    if _should_use_sample(adapter, source_mode):
        return _require_repo(adapter).load_first_sample_response("webaction/list/actionList") or {}
    return adapter.webaction.list_actions(
        biz_system_id=context.biz_system_id,
        end_time=context.time_window.end_time,
        time_period=context.time_window.period_minutes,
        application_id=application_id,
    )


def _load_matching_action_overview(
    adapter: Any,
    context: AnalysisContext,
    *,
    source_mode: str,
    action_id: int,
    application_id: int,
    action_type: str,
) -> Optional[dict[str, Any]]:
    if _should_use_sample(adapter, source_mode):
        repo = _require_repo(adapter)
        request = repo.load_first_sample_request("webaction/overview")
        if not request:
            return None
        request_body = request.get("body") or {}
        if str(request_body.get("actionId")) != str(action_id):
            return None
        return repo.load_first_sample_response("webaction/overview")
    return adapter.webaction.action_overview(
        biz_system_id=context.biz_system_id,
        application_id=application_id,
        action_id=action_id,
        action_type=action_type,
        end_time=context.time_window.end_time,
        time_period=context.time_window.period_minutes,
    )


def _load_trace_case_live(
    adapter: Any,
    context: AnalysisContext,
    *,
    action_ref: Optional[ActionRef],
    trace_policy: TraceSelectionPolicy,
) -> tuple[dict[str, Any], Optional[dict[str, Any]], Optional[dict[str, Any]], Any, list[WarningMessage]]:
    warnings: list[WarningMessage] = []
    if action_ref is None:
        actions_payload = adapter.webaction.list_actions(
            biz_system_id=context.biz_system_id,
            end_time=context.time_window.end_time,
            time_period=context.time_window.period_minutes,
        )
        rows = _extract_action_rows(actions_payload)
        if not rows:
            warnings.append(WarningMessage(code="missing_actions_for_trace", message="No actions returned while selecting a trace case.", source_api="webaction/list/actionList"))
            return ({}, None, None, None, warnings)
        top = max([normalize_metric_fields(dict(row)) for row in rows], key=lambda row: _numeric(row.get("response_time_ms")))
        action_ref = ActionRef(
            biz_system_id=context.biz_system_id,
            application_id=_int_or_zero(top.get("applicationId")),
            action_id=_int_or_zero(top.get("actionId")),
            action_type=str(top.get("actionType") or "TX"),
        )

    trace_overview = adapter.graph.query_overview(
        metric="trace_current_overview",
        payload={
            "endTime": context.time_window.end_time,
            "labels": {
                "actionIds": [str(action_ref.action_id)],
                "actionTypes": [action_ref.action_type],
                "applicationIds": [str(action_ref.application_id)],
                "systemIds": [str(context.biz_system_id)],
            },
            "lang": context.lang,
            "metric": "trace_current_overview",
            "order": {"fields": ["timestamp"], "type": "desc"},
            "page": {"number": 1, "size": trace_policy.limit},
            "timePeriod": context.time_window.period_minutes,
        },
    )
    trace_rows = _find_trace_rows(trace_overview)
    if not trace_rows:
        warnings.append(WarningMessage(code="missing_trace_rows", message="trace_current_overview returned no usable rows.", source_api="graph/query/overview"))
        return (
            {
                "biz_system_id": context.biz_system_id,
                "action_id": action_ref.action_id,
                "application_id": action_ref.application_id,
            },
            None,
            None,
            None,
            warnings,
        )

    trace_row = _choose_trace_row(trace_rows, trace_policy.strategy)
    keys = resolve_trace_keys(trace_row)
    selector = {
        "biz_system_id": context.biz_system_id,
        "application_id": action_ref.application_id,
        "action_id": action_ref.action_id,
        "trace_id_numeric": keys.trace_id_numeric,
        "query_timestamp": keys.query_timestamp,
        "trace_guid": keys.trace_guid,
        "action_guid": keys.action_guid,
    }
    if not keys.trace_id_numeric or not keys.query_timestamp:
        warnings.append(WarningMessage(code="trace_keys_incomplete", message="Selected trace row is missing traceId or queryTimestamp.", source_api="graph/query/overview"))
        return (selector, None, None, None, warnings)

    detail = adapter.trace.trace_detail(
        biz_system_id=context.biz_system_id,
        trace_id=keys.trace_id_numeric,
        query_timestamp=keys.query_timestamp,
        end_time=context.time_window.end_time,
        time_period=context.time_window.period_minutes,
    )
    call_tree = None
    if keys.action_guid:
        call_tree = adapter.trace.call_tree(
            biz_system_id=context.biz_system_id,
            trace_id=keys.trace_id_numeric,
            action_guid=keys.action_guid,
            query_timestamp=keys.query_timestamp,
            end_time=context.time_window.end_time,
            time_period=context.time_window.period_minutes,
        )
    else:
        warnings.append(WarningMessage(code="missing_action_guid", message="Selected trace row is missing actionGuid; call tree was skipped.", source_api="action/trace/callTree"))
    return selector, detail, call_tree, None, warnings


def _load_trace_case_from_samples(adapter: Any, context: AnalysisContext) -> dict[str, Any]:
    repo = _require_repo(adapter)
    warning = None
    try:
        detail_request = repo.load_first_sample_request("action/trace/detail") or {}
        detail_response = repo.load_first_sample_response("action/trace/detail") or {}
    except FileNotFoundError:
        return {
            "selector": {"biz_system_id": context.biz_system_id},
            "detail": {},
            "call_tree": {},
            "exceptions": [],
            "warning": WarningMessage(code="missing_trace_detail_sample", message="No captured trace detail sample exists.", source_api="action/trace/detail"),
        }

    request_body = detail_request.get("body") or {}
    sample_biz_system_id = _int_or_zero(request_body.get("bizSystemId") or unwrap_data(detail_response).get("bizSystemId"))
    if sample_biz_system_id != context.biz_system_id:
        warning = WarningMessage(
            code="trace_sample_biz_system_mismatch",
            message=f"Sample trace detail belongs to bizSystemId={sample_biz_system_id}, not the requested bizSystemId={context.biz_system_id}. Using representative sample.",
            source_api="action/trace/detail",
        )
    selector = {
        "biz_system_id": sample_biz_system_id or context.biz_system_id,
        "trace_id_numeric": str(request_body.get("traceId") or ""),
        "query_timestamp": str(request_body.get("queryTimestamp") or ""),
        "action_id": unwrap_data(detail_response).get("actionId"),
        "application_id": unwrap_data(detail_response).get("applicationId"),
        "action_guid": unwrap_data(detail_response).get("actionGuid"),
        "trace_guid": unwrap_data(detail_response).get("traceGuid"),
    }
    call_tree = repo.load_first_sample_response("action/trace/callTree") or {}
    exceptions = repo.load_first_sample_response("action/trace/detail/exceptions") or []
    return {
        "selector": selector,
        "detail": detail_response,
        "call_tree": call_tree,
        "exceptions": exceptions,
        "warning": warning,
    }


def _trace_from_detail(detail: dict[str, Any], fallback_biz_system_id: int) -> Trace:
    keys = resolve_trace_keys(detail)
    return Trace(
        biz_system_id=_int_or_zero(detail.get("bizSystemId")) or fallback_biz_system_id,
        trace_id_numeric=keys.trace_id_numeric,
        trace_guid=keys.trace_guid,
        action_guid=keys.action_guid,
        request_id=keys.request_id,
        timestamp=detail.get("timestamp"),
        application_id=detail.get("applicationId"),
        instance_id=detail.get("instanceId"),
        action_id=detail.get("actionId"),
        status=str(detail.get("status")) if detail.get("status") is not None else None,
        duration_ms=_numeric(detail.get("duration") or detail.get("respTime") or detail.get("actionDuration")),
        error_count=_int_or_none(detail.get("errorCount")),
        is_slow_trace=bool(detail.get("isSlowTrace")) if detail.get("isSlowTrace") is not None else None,
        suspected_problems=detail.get("suspectedProblemList") or [],
        topology_summary=_topology_summary(detail.get("topology") or {}),
        service_flow_summary=_service_flow_summary(detail.get("serviceFlow") or {}),
        timeline_summary=_timeline_summary(detail.get("timeLine") or {}),
    )


def _trace_detail_summary(detail: dict[str, Any]) -> dict[str, Any]:
    if not detail:
        return {}
    return {
        "requestId": detail.get("requestId"),
        "traceGuid": detail.get("traceGuid"),
        "actionGuid": detail.get("actionGuid"),
        "bizSystemId": detail.get("bizSystemId"),
        "bizSystemName": detail.get("bizSystemName"),
        "applicationId": detail.get("applicationId"),
        "applicationName": detail.get("applicationName"),
        "actionId": detail.get("actionId"),
        "actionName": detail.get("actionName"),
        "instanceId": detail.get("instanceId"),
        "instanceName": detail.get("instanceName"),
        "timestamp": detail.get("timestamp"),
        "respTime": detail.get("respTime"),
        "duration": detail.get("duration"),
        "status": detail.get("status"),
        "method": detail.get("method"),
        "uri": detail.get("uri"),
        "url": detail.get("url"),
        "threadName": detail.get("threadName"),
        "suspectedProblemList": detail.get("suspectedProblemList") or [],
        "topologySummary": _topology_summary(detail.get("topology") or {}),
        "serviceFlowSummary": _service_flow_summary(detail.get("serviceFlow") or {}),
        "timeLineSummary": _timeline_summary(detail.get("timeLine") or {}),
    }


def _call_tree_summary(call_tree: dict[str, Any]) -> dict[str, Any]:
    if not call_tree:
        return {}
    data = unwrap_data(call_tree) or {}
    node_map = data.get("nodeMap") if isinstance(data, dict) else {}
    return {
        "node_count": len(node_map) if isinstance(node_map, dict) else 0,
        "action_count": len(data.get("actions", [])) if isinstance(data.get("actions"), list) else 0,
        "application_count": len(data.get("applications", [])) if isinstance(data.get("applications"), list) else 0,
        "instance_count": len(data.get("instances", [])) if isinstance(data.get("instances"), list) else 0,
    }


def _exception_summary(exceptions: Any) -> dict[str, Any]:
    if not isinstance(exceptions, list):
        return {}
    return {
        "count": len(exceptions),
        "top_exception": exceptions[0] if exceptions else None,
    }


def _timeline_summary(timeline: dict[str, Any]) -> dict[str, Any]:
    return {
        "metricType": timeline.get("metricType"),
        "metricName": timeline.get("metricName"),
        "exclusiveTime": timeline.get("exclusiveTime"),
        "method": timeline.get("method"),
        "methodStack": timeline.get("methodStack"),
    }


def _service_flow_summary(flow: dict[str, Any]) -> dict[str, Any]:
    return {
        "serviceName": flow.get("serviceName"),
        "serviceType": flow.get("serviceType"),
        "durationTotal": flow.get("durationTotal"),
        "requestTotalCount": flow.get("requestTotalCount"),
    }


def _topology_summary(topology: dict[str, Any]) -> dict[str, Any]:
    nodes = topology.get("nodes")
    lines = topology.get("lines")
    return {
        "nodeCount": len(nodes) if isinstance(nodes, list) else 0,
        "lineCount": len(lines) if isinstance(lines, list) else 0,
    }


def _summarize_chart(chart_payload: Any) -> dict[str, Any]:
    data = unwrap_data(chart_payload) or {}
    overview = data.get("overviews") if isinstance(data, dict) else {}
    series = data.get("series") if isinstance(data, dict) else []
    points: list[dict[str, Any]] = []
    if isinstance(series, list):
        for series_item in series:
            if isinstance(series_item, dict) and isinstance(series_item.get("data"), list):
                points.extend([item for item in series_item["data"] if isinstance(item, dict)])
    ys = [_numeric(point.get("y")) for point in points if point.get("y") is not None]
    valid_ys = [value for value in ys if value is not None]
    latest = points[-1] if points else None
    return {
        "overview": overview,
        "point_count": len(points),
        "min_y": min(valid_ys) if valid_ys else None,
        "max_y": max(valid_ys) if valid_ys else None,
        "avg_y": (sum(valid_ys) / len(valid_ys)) if valid_ys else None,
        "latest_point": latest,
    }


def _extract_action_rows(actions_payload: Any) -> list[dict[str, Any]]:
    data = unwrap_data(actions_payload) or {}
    if isinstance(data, dict) and isinstance(data.get("content"), list):
        return [item for item in data["content"] if isinstance(item, dict)]
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    return []


def _find_trace_rows(node: Any) -> list[dict[str, Any]]:
    found: list[list[dict[str, Any]]] = []

    def visit(value: Any) -> None:
        if isinstance(value, list):
            if value and all(isinstance(item, dict) for item in value):
                candidates = [item for item in value if _looks_like_trace_row(item)]
                if candidates:
                    found.append(candidates)
            for item in value:
                visit(item)
        elif isinstance(value, dict):
            for child in value.values():
                visit(child)

    visit(unwrap_data(node))
    if not found:
        return []
    return max(found, key=len)


def _choose_trace_row(rows: list[dict[str, Any]], strategy: str) -> dict[str, Any]:
    if strategy == TraceSelectionStrategy.NEWEST.value:
        key_func = lambda row: _numeric(row.get("timestamp")) or float("-inf")
    elif strategy == TraceSelectionStrategy.HIGHEST_ERROR.value:
        key_func = lambda row: _numeric(row.get("errorCount")) or float("-inf")
    else:
        key_func = lambda row: _first_metric_value(row, ["respTime", "response", "responseTime", "duration", "totalTime"])
    return max(rows, key=key_func)


def _looks_like_trace_row(item: Any) -> bool:
    if not isinstance(item, dict):
        return False
    has_identity = any(key in item for key in ("id", "traceId", "requestId", "traceGuid"))
    has_context = any(key in item for key in ("actionId", "applicationId", "bizSystemId", "timestamp"))
    return has_identity and has_context


def _why_action_selected(row: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    response_time = _numeric(row.get("response_time_ms"))
    if response_time and response_time >= 1000:
        reasons.append(f"response_time_ms={response_time}")
    slow_count = _numeric(row.get("slowCount"))
    if slow_count and slow_count > 0:
        reasons.append(f"slowCount={int(slow_count)}")
    error_count = _numeric(row.get("errorCount"))
    if error_count and error_count > 0:
        reasons.append(f"errorCount={int(error_count)}")
    if not reasons:
        reasons.append("ranked_by_response_time")
    return reasons


def _severity_from_action(row: dict[str, Any]) -> float:
    response = _numeric(row.get("response_time_ms")) or 0.0
    slow = _numeric(row.get("slowCount")) or 0.0
    errors = _numeric(row.get("errorCount")) or 0.0
    return round(response + slow * 100 + errors * 200, 3)


def _first_metric_value(record: dict[str, Any], keys: Iterable[str]) -> float:
    for key in keys:
        value = _numeric(record.get(key))
        if value is not None:
            return value
    return float("-inf")


def _excerpt(value: dict[str, Any], keys: list[str]) -> dict[str, Any]:
    return {key: value.get(key) for key in keys if key in value}


def _evidence(
    *,
    evidence_id: str,
    source_api: str,
    source_path: str,
    source_method: str,
    request_params: dict[str, Any],
    response_excerpt: Any,
) -> Evidence:
    return Evidence(
        id=evidence_id,
        source_api=source_api,
        source_path=source_path,
        source_method=source_method,
        request_signature={"source_api": source_api, "request_params": request_params},
        request_params=request_params,
        response_excerpt=response_excerpt,
    )


def _pack(
    pack_type: str,
    context: AnalysisContext,
    payload: Any,
    *,
    evidence: list[Evidence],
    warnings: list[WarningMessage],
    source_mode: str = "unknown",
    missing_inputs: Optional[list[str]] = None,
    confidence_notes: Optional[list[str]] = None,
    build_stats: Optional[dict[str, Any]] = None,
) -> PackEnvelope:
    meta = PackMeta(
        source_mode=source_mode,
        source_count=len(evidence),
        evidence_count=len(evidence),
        missing_inputs=missing_inputs or [],
        warnings=warnings,
        confidence_notes=confidence_notes or [],
        build_stats=build_stats or {},
    )
    return PackEnvelope(pack_type=pack_type, context=context, payload=payload, meta=meta)


def _coerce_evidence_list(items: list[Any]) -> list[Evidence]:
    coerced: list[Evidence] = []
    for item in items:
        if isinstance(item, Evidence):
            coerced.append(item)
        elif isinstance(item, dict):
            coerced.append(
                Evidence(
                    id=str(item.get("id") or "evidence"),
                    source_api=str(item.get("source_api") or item.get("sourceApi") or "unknown"),
                    source_path=str(item.get("source_path") or item.get("sourcePath") or "unknown"),
                    source_method=str(item.get("source_method") or item.get("sourceMethod") or "POST"),
                    request_signature=item.get("request_signature") or {},
                    request_params=item.get("request_params") or {},
                    response_excerpt=item.get("response_excerpt"),
                    extracted_fields=item.get("extracted_fields") or {},
                    captured_at=item.get("captured_at"),
                    confidence=float(item.get("confidence", 1.0)),
                )
            )
    return coerced


def _trace_key_sqls(detail: dict[str, Any]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for item in detail.get("suspectedProblemList") or []:
        metric_type = str(item.get("metricType") or "")
        metric_name = str(item.get("metricName") or "")
        if metric_type.upper() == "DATABASE" or any(token in metric_name.upper() for token in ("SELECT ", "UPDATE ", "DELETE ", "INSERT ")):
            candidates.append(
                {
                    "source": "suspected_problem",
                    "label": metric_name,
                    "metric_type": metric_type,
                    "exclusive_time": item.get("exclusiveTime"),
                }
            )
    return candidates[:5]


def _trace_primary_sql_fingerprint(detail: dict[str, Any]) -> str | None:
    key_sqls = _trace_key_sqls(detail)
    if not key_sqls:
        return None
    return sql_fingerprint(str(key_sqls[0].get("label") or ""))


def _trace_sql_bottleneck_ratio(detail: dict[str, Any]) -> float | None:
    suspects = detail.get("suspectedProblemList") or []
    if not suspects:
        return None
    database_time = sum(_numeric(item.get("exclusiveTime")) or 0.0 for item in suspects if str(item.get("metricType") or "").upper() == "DATABASE")
    duration = _numeric(detail.get("respTime") or detail.get("duration"))
    if not duration or database_time <= 0:
        return None
    return round(database_time / duration, 4)


def _trace_sql_binding_strength(detail: dict[str, Any]) -> str:
    ratio = _trace_sql_bottleneck_ratio(detail)
    if ratio is None:
        return "none"
    if ratio >= 0.3:
        return "strong"
    if ratio >= 0.1:
        return "medium"
    return "weak"


def _select_sql_enrichment_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    seen: set[str] = set()
    for sort_key in (
        lambda row: _numeric(row.get("response_time_ms")) or 0.0,
        lambda row: _numeric(row.get("total_response_time_ms") or row.get("totalResptime")) or 0.0,
        lambda row: _numeric(row.get("traceCount")) or 0.0,
    ):
        for row in sorted(rows, key=sort_key, reverse=True)[:3]:
            fingerprint = sql_fingerprint(str(row.get("op_name_decoded") or row.get("opName") or ""))
            if fingerprint in seen:
                continue
            seen.add(fingerprint)
            selected.append(row)
    return selected


def _enrich_trace_case_with_sql(trace_case: dict[str, Any], sql_candidates: list[dict[str, Any]]) -> dict[str, Any]:
    enriched = dict(trace_case)
    trace = enriched.get("trace") or {}
    trace_id = trace.get("trace_id_numeric")
    trace_action_id = trace.get("action_id")
    matched: list[dict[str, Any]] = []
    for candidate in sql_candidates:
        caller_objects = candidate.get("caller_objects") or []
        impact_objects = candidate.get("impact_objects") or []
        if trace_id and str(trace_id) in {str(item) for item in candidate.get("trace_case_ids") or []}:
            matched.append(candidate)
            continue
        action_ids = {str(item.get("action_id")) for item in caller_objects + impact_objects if item.get("action_id") is not None}
        if trace_action_id is not None and str(trace_action_id) in action_ids:
            matched.append(candidate)
    matched = matched[:5]
    if matched:
        enriched["key_sqls"] = [
            {
                "sql_fingerprint": item.get("sql_fingerprint"),
                "trace_binding_strength": item.get("trace_binding_strength"),
                "candidate_source": item.get("candidate_source"),
                "metrics": item.get("metrics"),
            }
            for item in matched
        ]
        enriched["primary_sql_fingerprint"] = matched[0].get("sql_fingerprint")
        enriched["sql_bottleneck_ratio"] = matched[0].get("metrics", {}).get("response_time_ms")
        enriched["sql_trace_binding_strength"] = matched[0].get("trace_binding_strength")
    return enriched


def _aggregate_report_page_links(*payloads: dict[str, Any]) -> list[dict[str, Any]]:
    links: list[dict[str, Any]] = []
    for payload in payloads:
        links.extend(payload.get("page_links") or [])
    return links


def _aggregate_report_screenshot_hints(*payloads: dict[str, Any]) -> list[dict[str, Any]]:
    hints: list[dict[str, Any]] = []
    for payload in payloads:
        hints.extend(payload.get("screenshot_hints") or [])
    return hints


def _aggregate_report_metric_semantics(*payloads: dict[str, Any]) -> list[dict[str, Any]]:
    semantics: list[dict[str, Any]] = []
    for payload in payloads:
        semantics.extend(payload.get("metric_semantics") or [])
    return semantics


def _build_screenshot_index_rows(*payloads: dict[str, Any]) -> list[dict[str, Any]]:
    links = _aggregate_report_page_links(*payloads)
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    figure_index = 1
    for payload in payloads:
        for hint in payload.get("screenshot_hints") or []:
            key = (str(hint.get("title") or ""), str(hint.get("url") or ""))
            if key in seen:
                continue
            seen.add(key)
            matched_link = _match_report_link(hint, links)
            rows.append(
                {
                    "figure_id": f"FIG-{figure_index:02d}",
                    "title": hint.get("title"),
                    "page_type": hint.get("page_type"),
                    "suggested_report_section": hint.get("suggested_report_section"),
                    "priority": hint.get("priority", "medium"),
                    "url": hint.get("url"),
                    "url_status": matched_link.get("url_status") or "unknown",
                    "writer_summary": _report_screenshot_summary(hint, matched_link),
                }
            )
            figure_index += 1
    return rows


def _match_report_link(hint: dict[str, Any], links: list[dict[str, Any]]) -> dict[str, Any]:
    page_type = hint.get("page_type")
    target_ref = hint.get("target_ref") or {}
    best: dict[str, Any] = {}
    best_score = -1
    for link in links:
        score = 0
        if page_type and link.get("page_type") == page_type:
            score += 4
        if target_ref and json.dumps(link.get("target_ref") or {}, ensure_ascii=False, sort_keys=True) == json.dumps(target_ref, ensure_ascii=False, sort_keys=True):
            score += 5
        if hint.get("url") and link.get("url") == hint.get("url"):
            score += 3
        if score > best_score:
            best = link
            best_score = score
    return best if best_score > 0 else {}


def _report_screenshot_summary(hint: dict[str, Any], matched_link: dict[str, Any]) -> str:
    section = hint.get("suggested_report_section") or "未指定章节"
    title = hint.get("title") or hint.get("page_type") or "未命名截图"
    url_status = matched_link.get("url_status") or "unknown"
    usage = hint.get("usage_in_report") or ""
    return f"{section} | {title} | 链接状态={url_status} | 用途={usage}"


def _should_use_sample(adapter: Any, source_mode: str) -> bool:
    if source_mode == "sample":
        return True
    if source_mode == "live":
        return False
    return bool(getattr(adapter, "captured_api", None))


def _require_repo(adapter: Any) -> Any:
    repo = getattr(adapter, "captured_api", None)
    if repo is None:
        raise RuntimeError("CapturedApiRepository is not attached. Pass --captured-api-dir or set TINGYUN_CAPTURED_API_DIR.")
    return repo


def _ensure_int_list(value: Any) -> list[int]:
    if not isinstance(value, list):
        return []
    result: list[int] = []
    for item in value:
        converted = _int_or_none(item)
        if converted is not None:
            result.append(converted)
    return result


def _int_or_none(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return None


def _int_or_zero(value: Any) -> int:
    return _int_or_none(value) or 0


def _numeric(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return None


def _signal(kind: str, value: Any, *, level: str = "info", reason: Optional[str] = None, source: Optional[str] = None) -> dict[str, Any]:
    payload = {"type": kind, "value": value, "level": level}
    if reason:
        payload["reason"] = reason
    if source:
        payload["source_api"] = source
    return payload


def _system_suspect_signals(overview: dict[str, Any], health: dict[str, Any], trends: dict[str, Any]) -> list[dict[str, Any]]:
    signals: list[dict[str, Any]] = []
    if _numeric((health.get("action") or {}).get("warn")) and _numeric((health.get("action") or {}).get("warn")) > 0:
        signals.append(_signal("action_health_warn", (health.get("action") or {}).get("warn"), level="high", source="health/healthLevelStatistics"))
    latest_response = ((trends.get("response") or {}).get("latest_point") or {}).get("y")
    if _numeric(latest_response) and _numeric(latest_response) >= 1000:
        signals.append(_signal("latest_response_p99_high", _numeric(latest_response), level="medium", source="application/charts/response"))
    if _numeric(overview.get("slowCount")) and _numeric(overview.get("slowCount")) > 0:
        signals.append(_signal("slow_request_count_present", overview.get("slowCount"), level="medium", source="application/business/overview"))
    return signals


def _action_suspect_signals(row: dict[str, Any], *, overview: Optional[dict[str, Any]] = None, trace_rows: Optional[list[dict[str, Any]]] = None) -> list[dict[str, Any]]:
    signals: list[dict[str, Any]] = []
    response_time = _numeric(row.get("response_time_ms"))
    if response_time and response_time >= 1000:
        level = "high" if response_time >= 5000 else "medium"
        signals.append(_signal("high_response_time_ms", response_time, level=level, source="webaction/list/actionList"))
    slow_count = _numeric(row.get("slowCount"))
    if slow_count and slow_count > 0:
        signals.append(_signal("slow_count_present", int(slow_count), level="medium", source="webaction/list/actionList"))
    error_count = _numeric(row.get("errorCount"))
    if error_count and error_count > 0:
        signals.append(_signal("error_count_present", int(error_count), level="high", source="webaction/list/actionList"))
    components = (overview or {}).get("components") or {}
    if isinstance(components, dict):
        for component_type, rows in components.items():
            if rows:
                signals.append(_signal("downstream_component_present", component_type, level="info", source="webaction/overview"))
    if trace_rows:
        trace_durations = [_numeric(row.get("respTime") or row.get("duration")) for row in trace_rows]
        trace_durations = [item for item in trace_durations if item is not None]
        if trace_durations and max(trace_durations) >= 1000:
            signals.append(_signal("slow_trace_candidate_present", max(trace_durations), level="medium", source="graph/query/overview"))
    return signals


def _aggregate_action_signals(hotspots: list[dict[str, Any]]) -> list[dict[str, Any]]:
    aggregate: list[dict[str, Any]] = []
    if hotspots:
        aggregate.append(_signal("hotspot_count", len(hotspots), level="info"))
        aggregate.extend(hotspots[0].get("suspect_signals", [])[:3])
    return aggregate


def _trace_suspect_signals(detail: dict[str, Any], call_tree_summary: dict[str, Any], exception_summary: dict[str, Any]) -> list[dict[str, Any]]:
    signals: list[dict[str, Any]] = []
    duration = _numeric(detail.get("duration") or detail.get("respTime") or detail.get("actionDuration"))
    if duration and duration >= 1000:
        level = "high" if duration >= 5000 else "medium"
        signals.append(_signal("trace_duration_high_ms", duration, level=level, source="action/trace/detail"))
    suspected = detail.get("suspectedProblemList") or []
    if suspected:
        signals.append(_signal("suspected_problem_count", len(suspected), level="high", source="action/trace/detail"))
    if _numeric(exception_summary.get("count")) and _numeric(exception_summary.get("count")) > 0:
        signals.append(_signal("trace_exception_count", exception_summary.get("count"), level="high", source="action/trace/detail/exceptions"))
    if _numeric(call_tree_summary.get("node_count")) and _numeric(call_tree_summary.get("node_count")) > 0:
        signals.append(_signal("call_tree_available", call_tree_summary.get("node_count"), level="info", source="action/trace/callTree"))
    return signals


def _resolve_action_ref(
    adapter: Any,
    context: AnalysisContext,
    *,
    source_mode: str,
    action_ref: Optional[ActionRef],
) -> tuple[dict[str, Any], Optional[ActionRef], list[WarningMessage]]:
    warnings: list[WarningMessage] = []
    actions_payload = _load_action_list(adapter, context, source_mode=source_mode, application_id=action_ref.application_id if action_ref else 0)
    rows = [normalize_metric_fields(dict(row)) for row in _extract_action_rows(actions_payload)]
    if not rows:
        warnings.append(WarningMessage(code="missing_actions", message="没有找到可用的 action 列表。", source_api="webaction/list/actionList"))
        return {}, None, warnings
    if action_ref:
        for row in rows:
            if str(row.get("actionId")) == str(action_ref.action_id) and str(row.get("applicationId")) == str(action_ref.application_id):
                return row, action_ref, warnings
        warnings.append(WarningMessage(code="action_ref_partial_match", message="未找到指定 action 的完整列表行，将保留传入的 action_ref 并继续补充 overview / trace 信息。", source_api="webaction/list/actionList"))
        return {}, action_ref, warnings
    top = max(rows, key=lambda row: _numeric(row.get("response_time_ms")) or float("-inf"))
    return top, ActionRef(
        biz_system_id=context.biz_system_id,
        application_id=_int_or_zero(top.get("applicationId")),
        action_id=_int_or_zero(top.get("actionId")),
        action_type=str(top.get("actionType") or "TX"),
    ), warnings


def _load_trace_candidates_for_action(
    adapter: Any,
    context: AnalysisContext,
    action_ref: ActionRef,
    *,
    source_mode: str,
    limit: int,
) -> tuple[list[dict[str, Any]], Optional[WarningMessage]]:
    if _should_use_sample(adapter, source_mode):
        from tingyun_adapter.usecases.component_builders import _find_sample_pair

        _req, resp, warning = _find_sample_pair(
            adapter,
            "graph/query/overview",
            matcher=lambda body, _resp: body.get("metric") == "trace_current_overview"
            and str(((body.get("labels") or {}).get("actionIds") or [""])[0]) == str(action_ref.action_id),
        )
        return _find_trace_rows(resp)[:limit], warning

    trace_overview = adapter.graph.query_overview(
        metric="trace_current_overview",
        payload={
            "endTime": context.time_window.end_time,
            "labels": {
                "actionIds": [str(action_ref.action_id)],
                "actionTypes": [action_ref.action_type],
                "applicationIds": [str(action_ref.application_id)],
                "systemIds": [str(context.biz_system_id)],
            },
            "lang": context.lang,
            "metric": "trace_current_overview",
            "order": {"fields": ["timestamp"], "type": "desc"},
            "page": {"number": 1, "size": limit},
            "timePeriod": context.time_window.period_minutes,
        },
    )
    rows = _find_trace_rows(trace_overview)[:limit]
    if not rows:
        return [], WarningMessage(code="missing_trace_candidates", message="未找到 action 对应的 trace 候选。", source_api="graph/query/overview")
    return rows, None


def _trace_candidate_summary(row: dict[str, Any]) -> dict[str, Any]:
    keys = resolve_trace_keys(row)
    return {
        "trace_id_numeric": keys.trace_id_numeric,
        "trace_guid": keys.trace_guid,
        "action_guid": keys.action_guid,
        "query_timestamp": keys.query_timestamp,
        "timestamp": row.get("timestamp"),
        "duration_ms": _numeric(row.get("respTime") or row.get("duration") or row.get("responseTime")),
        "error_count": _int_or_none(row.get("errorCount")),
        "status": row.get("status"),
        "suspect_signals": _trace_row_suspect_signals(row),
    }


def _trace_row_suspect_signals(row: dict[str, Any]) -> list[dict[str, Any]]:
    signals: list[dict[str, Any]] = []
    duration = _numeric(row.get("respTime") or row.get("duration") or row.get("responseTime"))
    if duration and duration >= 1000:
        signals.append(_signal("trace_candidate_duration_high_ms", duration, level="medium", source="graph/query/overview"))
    if _numeric(row.get("errorCount")) and _numeric(row.get("errorCount")) > 0:
        signals.append(_signal("trace_candidate_error_count", int(_numeric(row.get("errorCount")) or 0), level="high", source="graph/query/overview"))
    if row.get("isSlowTrace"):
        signals.append(_signal("trace_candidate_marked_slow", True, level="medium", source="graph/query/overview"))
    return signals


def _trace_candidate_keys(row: dict[str, Any]) -> dict[str, Any]:
    keys = resolve_trace_keys(row)
    return {
        "traceId": keys.trace_id_numeric,
        "queryTimestamp": keys.query_timestamp,
        "traceGuid": keys.trace_guid,
        "actionGuid": keys.action_guid,
    }


def _summarize_action_components(components: dict[str, Any]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    if not isinstance(components, dict):
        return summary
    for component_type, rows in components.items():
        if not isinstance(rows, list):
            continue
        summary[component_type] = {
            "component_count": len(rows),
            "top_rows": rows[:3],
        }
    return summary


def _component_candidates_from_action_components(components: dict[str, Any]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    if not isinstance(components, dict):
        return candidates
    for component_type, rows in components.items():
        if not isinstance(rows, list):
            continue
        for row in rows[:3]:
            candidates.append(
                {
                    "component_type": component_type,
                    "component_subtype": row.get("componentSubtype"),
                    "count": row.get("count"),
                    "response_time_ms": row.get("respTime"),
                    "component_name_size": row.get("componentNameSize"),
                    "suspect_signals": [
                        _signal("component_present_in_action_overview", component_type, level="info", source="webaction/overview")
                    ],
                }
            )
    return candidates


def _recommended_next_packs(top_action: dict[str, Any], component_candidates: list[dict[str, Any]], trace_candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    recommendations: list[dict[str, Any]] = []
    if top_action:
        action = top_action.get("action", {})
        recommendations.append(
            {
                "pack_type": PackType.ACTION_FACT_SHEET.value,
                "reason": "对当前最热点 action 做进一步事实聚合",
                "keys": {
                    "actionId": action.get("id"),
                    "applicationId": action.get("application_id"),
                    "actionType": action.get("type"),
                },
            }
        )
    if trace_candidates:
        recommendations.append(
            {
                "pack_type": PackType.TRACE_FACT_SHEET.value,
                "reason": "基于热点 action 的 trace 候选继续下钻",
                "keys": trace_candidates[0],
            }
        )
    for candidate in component_candidates[:2]:
        component_type = candidate.get("component_type")
        if component_type == "Database":
            recommendations.append({"pack_type": PackType.DATABASE_COMPONENT.value, "reason": "热点 action 涉及 Database 组件", "keys": candidate})
        elif component_type == "NoSQL":
            recommendations.append({"pack_type": PackType.NOSQL_COMPONENT.value, "reason": "热点 action 涉及 NoSQL 组件", "keys": candidate})
    return recommendations


def _trace_fact_drilldown_keys(selector: dict[str, Any], trace: dict[str, Any]) -> dict[str, Any]:
    return {
        "bizSystemId": selector.get("biz_system_id") or trace.get("biz_system_id"),
        "traceId": selector.get("trace_id_numeric") or trace.get("trace_id_numeric"),
        "queryTimestamp": selector.get("query_timestamp"),
        "traceGuid": selector.get("trace_guid") or trace.get("trace_guid"),
        "actionGuid": selector.get("action_guid") or trace.get("action_guid"),
        "requestId": trace.get("request_id"),
        "instanceId": trace.get("instance_id"),
        "actionId": trace.get("action_id"),
    }
