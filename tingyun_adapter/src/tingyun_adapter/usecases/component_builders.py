from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any, Callable, Optional

from tingyun_adapter.domain.enums import PackType
from tingyun_adapter.domain.models.common import (
    AnalysisContext,
    ConnectionPoolRef,
    DatabaseComponentRef,
    Evidence,
    NoSQLComponentRef,
    PackEnvelope,
    WarningMessage,
    dataclass_to_dict,
)
from tingyun_adapter.domain.models.entities import ConnectionPool, DatabaseComponent, NoSQLComponent
from tingyun_adapter.domain.models.packs import (
    ConnectionPoolPackPayload,
    DatabaseComponentPackPayload,
    NoSQLComponentPackPayload,
)
from tingyun_adapter.normalizers.field_normalizer import unwrap_data
from tingyun_adapter.normalizers.metric_normalizer import normalize_metric_fields
from tingyun_adapter.normalizers.op_name_decoder import decode_op_name, encode_op_name
from tingyun_adapter.usecases.builders import (
    _coerce_evidence_list,
    _evidence,
    _numeric,
    _pack,
    _signal,
    _require_repo,
    _summarize_action_components,
    _should_use_sample,
    _summarize_chart,
    _trace_candidate_summary,
    _topology_summary,
)
from tingyun_adapter.usecases.report_support import (
    apply_report_support,
    default_coverage_boundary,
    make_console_link,
    make_metric_semantic,
    make_screenshot_hint,
    time_window_text,
)


def build_database_component_pack(
    adapter: Any,
    context: AnalysisContext,
    *,
    source_mode: str = "auto",
    component_ref: Optional[DatabaseComponentRef] = None,
) -> PackEnvelope:
    warnings: list[WarningMessage] = []
    evidence: list[Evidence] = []

    list_payload, list_request = _load_database_list(adapter, context, source_mode=source_mode)
    list_rows = _extract_content_rows(list_payload)
    component_row = _match_or_choose_component_row(list_rows, component_ref)
    if component_row is None:
        warnings.append(WarningMessage(code="missing_database_component", message="没有找到可用的 Database 组件样本。", source_api="Database/list"))
        payload = DatabaseComponentPackPayload(component={}, evidence=[])
        return _pack(PackType.DATABASE_COMPONENT.value, context, payload, evidence=evidence, warnings=warnings)

    selected_ref = DatabaseComponentRef(
        biz_system_id=context.biz_system_id,
        component_name=str(component_row.get("componentName") or ""),
        component_subtype=component_row.get("componentSubtype"),
    )
    if component_ref and (
        component_ref.component_name != selected_ref.component_name
        or component_ref.component_subtype != selected_ref.component_subtype
    ):
        warnings.append(WarningMessage(code="database_component_fallback", message="未找到指定的 Database 组件，已回退到当前最热点的组件。", source_api="Database/list"))

    info_payload = _load_database_info(adapter, context, selected_ref, source_mode=source_mode, data_type="COMP")
    analysis_payload = _load_database_analysis(adapter, context, selected_ref, source_mode=source_mode)
    graph_payload = _load_database_graph(adapter, context, selected_ref, source_mode=source_mode)
    connection_chart_payload = _load_connection_database_chart(adapter, context, selected_ref, source_mode=source_mode)

    operation_rows = _decoded_operation_rows(_extract_content_rows(analysis_payload))
    top_operation = operation_rows[0] if operation_rows else None

    impacted_actions_payload = _load_database_impacted_actions(
        adapter,
        context,
        selected_ref,
        source_mode=source_mode,
        op_name=top_operation.get("op_name_raw") if top_operation else "",
    )
    impacted_action_rows = _extract_content_rows(impacted_actions_payload)
    top_action = impacted_action_rows[0] if impacted_action_rows else None

    related_traces_payload = _load_database_related_traces(
        adapter,
        context,
        selected_ref,
        source_mode=source_mode,
        top_action=top_action,
        op_name=top_operation.get("op_name_raw") if top_operation else "",
    )
    related_traces = _normalize_component_trace_rows(_extract_content_rows(related_traces_payload))

    info = unwrap_data(info_payload) or {}
    component = DatabaseComponent(
        biz_system_id=context.biz_system_id,
        component_name=selected_ref.component_name,
        component_subtype=selected_ref.component_subtype,
        metrics={
            "response_time_ms": _first_non_none(info.get("respTime"), component_row.get("respTime")),
            "total_response_time_ms": _first_non_none(info.get("totalRespTime"), component_row.get("totalResptime")),
            "throughput": _first_non_none(info.get("throught"), component_row.get("throught")),
            "error_count": _first_non_none(info.get("errorCount"), component_row.get("errorCount")),
            "error_rate": _first_non_none(info.get("errorRate"), component_row.get("errorRate")),
            "trace_count": _first_non_none(info.get("traceCount"), component_row.get("traceCount")),
            "current_pool_used": info.get("currentPoolUsed"),
            "max_pool": info.get("maxPool"),
            "avg_conn_time": info.get("avgConnTime"),
        },
        top_actions=impacted_action_rows[:10],
        top_operations=operation_rows[:10],
        top_traces=related_traces[:10],
        topology=_summarize_component_graph(graph_payload),
        connection_pool=_summarize_chart(connection_chart_payload),
    )

    summary = {
        "component_name": selected_ref.component_name,
        "component_subtype": selected_ref.component_subtype,
        "database_type": selected_ref.component_subtype,
        "response_time_ms": component.metrics.get("response_time_ms"),
        "total_response_time_ms": component.metrics.get("total_response_time_ms"),
        "throughput": component.metrics.get("throughput"),
        "trace_count": component.metrics.get("trace_count"),
        "operation_count": len(operation_rows),
        "impacted_action_count": len(impacted_action_rows),
        "related_trace_count": len(related_traces),
    }
    topology_summary = component.topology
    connection_pool_summary = {
        "current_pool_used": component.metrics.get("current_pool_used"),
        "max_pool": component.metrics.get("max_pool"),
        "avg_conn_time_ms": component.metrics.get("avg_conn_time"),
        "connection_time_chart": component.connection_pool,
    }

    evidence.extend(
        [
            _evidence(
                evidence_id="database_list",
                source_api="Database/list",
                source_path="/server-api/Database/list",
                source_method="POST",
                request_params={"bizSystemId": context.biz_system_id, "componentName": selected_ref.component_name},
                response_excerpt=component_row,
            ),
            _evidence(
                evidence_id="database_info",
                source_api="Database/info",
                source_path="/server-api/Database/info",
                source_method="POST",
                request_params={"bizSystemId": context.biz_system_id, "componentName": selected_ref.component_name, "dataType": "COMP"},
                response_excerpt=info,
            ),
            _evidence(
                evidence_id="database_analysis",
                source_api="Database/analysis",
                source_path="/server-api/Database/analysis",
                source_method="POST",
                request_params={"bizSystemId": context.biz_system_id, "componentName": selected_ref.component_name, "dataType": "OP"},
                response_excerpt={"top_operations": operation_rows[:3]},
            ),
            _evidence(
                evidence_id="database_impacted_actions",
                source_api="component/database/actionList",
                source_path="/server-api/component/database/actionList",
                source_method="POST",
                request_params={"bizSystemId": context.biz_system_id, "componentName": selected_ref.component_name},
                response_excerpt={"top_actions": impacted_action_rows[:3]},
            ),
            _evidence(
                evidence_id="database_related_traces",
                source_api="component/database/actionTraceList",
                source_path="/server-api/component/database/actionTraceList",
                source_method="POST",
                request_params={"bizSystemId": context.biz_system_id, "componentName": selected_ref.component_name},
                response_excerpt={"top_traces": related_traces[:3]},
            ),
            _evidence(
                evidence_id="database_topology",
                source_api="graph/component/queryDataBaseGraph",
                source_path="/server-api/graph/component/queryDataBaseGraph",
                source_method="POST",
                request_params={"bizSystemId": context.biz_system_id, "componentName": selected_ref.component_name},
                response_excerpt=topology_summary,
            ),
        ]
    )

    payload = DatabaseComponentPackPayload(
        component=dataclass_to_dict(component),
        summary=summary,
        top_operations=operation_rows[:10],
        top_impacted_actions=impacted_action_rows[:10],
        top_related_traces=related_traces[:10],
        topology_summary=topology_summary,
        connection_pool_summary=connection_pool_summary,
        suspect_signals=_database_component_signals(component, related_traces, impacted_action_rows),
        evidence=[dataclass_to_dict(item) for item in evidence],
    )
    page_links = [
        make_console_link(
            adapter,
            context,
            page_type="database_component_overview",
            label="数据库组件总览页",
            why_relevant="用于查看数据库组件总体响应、吞吐、错误和连接情况。",
            suggested_report_section="3.4 SQL 检查",
            navigation_path=["业务系统", "数据库组件", selected_ref.component_name],
            suggested_filters={"componentName": selected_ref.component_name, "componentSubtype": selected_ref.component_subtype},
            target_ref={"kind": "database_component", "component_name": selected_ref.component_name, "component_subtype": selected_ref.component_subtype},
        ),
        make_console_link(
            adapter,
            context,
            page_type="database_sql_analysis",
            label="数据库 SQL 分析页",
            why_relevant="用于查看慢 SQL、异常 SQL 和影响事务。",
            suggested_report_section="3.4 SQL 检查",
            navigation_path=["业务系统", "数据库组件", selected_ref.component_name, "SQL 分析"],
            suggested_filters={"componentName": selected_ref.component_name, "componentSubtype": selected_ref.component_subtype},
            target_ref={"kind": "database_component", "component_name": selected_ref.component_name, "component_subtype": selected_ref.component_subtype},
        ),
        make_console_link(
            adapter,
            context,
            page_type="database_topology",
            label="数据库拓扑页",
            why_relevant="用于查看数据库与上游应用、事务之间的拓扑关系。",
            suggested_report_section="3.4 SQL 检查",
            navigation_path=["业务系统", "数据库组件", selected_ref.component_name, "拓扑"],
            suggested_filters={"componentName": selected_ref.component_name},
            target_ref={"kind": "database_component", "component_name": selected_ref.component_name, "component_subtype": selected_ref.component_subtype},
        ),
    ]
    screenshot_hints = [
        make_screenshot_hint(
            title="数据库组件总览截图建议",
            page_type="database_component_overview",
            url=page_links[0]["url"],
            recommended_capture=["组件响应时间趋势", "错误率或错误数趋势", "组件摘要指标卡"],
            recommended_annotations=["圈出异常时间窗", "标注组件名称", "标注响应时间或错误率异常点"],
            usage_in_report="可用于 SQL 检查章节说明数据库侧整体风险。",
            suggested_report_section="3.4 SQL 检查",
            target_ref=page_links[0]["target_ref"],
            priority="high",
        ),
        make_screenshot_hint(
            title="数据库慢 SQL 列表截图建议",
            page_type="database_sql_analysis",
            url=page_links[1]["url"],
            recommended_capture=["慢 SQL Top 列表", "错误 SQL 列表", "受影响事务列表"],
            recommended_annotations=["标出最慢 SQL", "标出错误次数高的 SQL", "标出关联事务名称"],
            usage_in_report="可用于 SQL Top 问题举证与影响面说明。",
            suggested_report_section="3.4 SQL 检查",
            target_ref=page_links[1]["target_ref"],
            priority="high",
        ),
    ]
    metric_semantics = [
        make_metric_semantic(
            metric_name="response_time_ms",
            subject_type="database_component",
            subject_key=f"database_component:{selected_ref.component_name}",
            aggregation="average",
            unit="ms",
            time_window=time_window_text(context),
            sample_scope="all database component calls in selected business scope",
        ),
        make_metric_semantic(
            metric_name="throughput",
            subject_type="database_component",
            subject_key=f"database_component:{selected_ref.component_name}",
            aggregation="rate",
            unit="rpm",
            time_window=time_window_text(context),
            sample_scope="all database component calls in selected business scope",
        ),
        make_metric_semantic(
            metric_name="error_rate",
            subject_type="database_component",
            subject_key=f"database_component:{selected_ref.component_name}",
            aggregation="ratio",
            unit="percent",
            time_window=time_window_text(context),
            sample_scope="all database component calls in selected business scope",
        ),
    ]
    evidence_linkage = {
        "related_time_windows": [dataclass_to_dict(context.time_window)],
        "related_actions": impacted_action_rows[:5],
        "related_traces": related_traces[:5],
        "related_sqls": operation_rows[:5],
        "related_dependencies": topology_summary.get("key_edges") if isinstance(topology_summary, dict) else [],
        "recommended_next_pages": page_links,
    }
    payload = apply_report_support(
        payload,
        page_links=page_links,
        screenshot_hints=screenshot_hints,
        metric_semantics=metric_semantics,
        coverage_boundary=default_coverage_boundary(adapter),
        evidence_linkage=evidence_linkage,
    )
    return _pack(
        PackType.DATABASE_COMPONENT.value,
        context,
        payload,
        evidence=evidence,
        warnings=warnings,
        source_mode=source_mode,
    )


def build_nosql_component_pack(
    adapter: Any,
    context: AnalysisContext,
    *,
    source_mode: str = "auto",
    component_ref: Optional[NoSQLComponentRef] = None,
) -> PackEnvelope:
    warnings: list[WarningMessage] = []
    evidence: list[Evidence] = []

    list_payload, _ = _load_nosql_list(adapter, context, source_mode=source_mode)
    list_rows = _extract_content_rows(list_payload)
    component_row = _match_or_choose_component_row(list_rows, component_ref)
    if _should_use_sample(adapter, source_mode) and component_ref is None:
        sample_component = _preferred_component_from_sample(
            adapter,
            "NoSQL/analysis",
            biz_system_id=context.biz_system_id,
        )
        if sample_component:
            component_row = _match_or_choose_component_row(
                list_rows,
                NoSQLComponentRef(
                    biz_system_id=context.biz_system_id,
                    component_name=sample_component["component_name"],
                    component_subtype=sample_component["component_subtype"],
                ),
            )
    if component_row is None:
        warnings.append(WarningMessage(code="missing_nosql_component", message="没有找到可用的 NoSQL 组件样本。", source_api="NoSQL/list"))
        payload = NoSQLComponentPackPayload(component={}, evidence=[])
        return _pack(PackType.NOSQL_COMPONENT.value, context, payload, evidence=evidence, warnings=warnings)

    selected_ref = NoSQLComponentRef(
        biz_system_id=context.biz_system_id,
        component_name=str(component_row.get("componentName") or ""),
        component_subtype=component_row.get("componentSubtype"),
    )
    if component_ref and (
        component_ref.component_name != selected_ref.component_name
        or component_ref.component_subtype != selected_ref.component_subtype
    ):
        warnings.append(WarningMessage(code="nosql_component_fallback", message="未找到指定的 NoSQL 组件，已回退到当前最热点的组件。", source_api="NoSQL/list"))

    overview_payload = _load_nosql_overview(adapter, context, selected_ref, source_mode=source_mode)
    analysis_payload = _load_nosql_analysis(adapter, context, selected_ref, source_mode=source_mode)
    graph_payload = _load_nosql_graph(adapter, context, selected_ref, source_mode=source_mode)
    error_payload = _load_nosql_error_types(adapter, context, selected_ref, source_mode=source_mode)

    operation_rows = _decoded_operation_rows(_extract_content_rows(analysis_payload))
    top_operation = operation_rows[0] if operation_rows else None
    impacted_actions_payload = _load_nosql_action_names(
        adapter,
        context,
        selected_ref,
        source_mode=source_mode,
    )
    impacted_actions = _extract_content_rows(impacted_actions_payload)
    trace_payload = _load_nosql_traces(
        adapter,
        context,
        selected_ref,
        source_mode=source_mode,
        op_name=top_operation.get("op_name_raw") if top_operation else "",
    )
    trace_rows = _normalize_component_trace_rows(_extract_content_rows(trace_payload))
    if not trace_rows:
        warnings.append(WarningMessage(code="nosql_trace_empty", message="NoSQL trace 列表为空，当前仅能提供操作与影响动作信息。", source_api="NoSQL/trace"))

    overview_rows = _extract_content_rows(overview_payload)
    overview_row = overview_rows[0] if overview_rows else component_row
    error_summary = _summarize_nosql_error_payload(error_payload)

    component = NoSQLComponent(
        biz_system_id=context.biz_system_id,
        component_name=selected_ref.component_name,
        component_subtype=selected_ref.component_subtype,
        metrics={
            "response_time_ms": _first_non_none(overview_row.get("respTime"), component_row.get("respTime")),
            "total_response_time_ms": _first_non_none(overview_row.get("totalResptime"), component_row.get("totalResptime")),
            "throughput": _first_non_none(overview_row.get("throught"), component_row.get("throught")),
            "error_count": _first_non_none(overview_row.get("errorCount"), component_row.get("errorCount")),
            "trace_count": _first_non_none(overview_row.get("traceCount"), component_row.get("traceCount")),
        },
        top_operations=operation_rows[:10],
        top_traces=trace_rows[:10],
        topology=_summarize_component_graph(graph_payload),
    )

    summary = {
        "component_name": selected_ref.component_name,
        "component_subtype": selected_ref.component_subtype,
        "response_time_ms": component.metrics.get("response_time_ms"),
        "throughput": component.metrics.get("throughput"),
        "operation_count": len(operation_rows),
        "trace_count": len(trace_rows),
        "impacted_action_count": len(impacted_actions),
        "top_impacted_actions": impacted_actions[:10],
    }

    evidence.extend(
        [
            _evidence(
                evidence_id="nosql_list",
                source_api="NoSQL/list",
                source_path="/server-api/NoSQL/list",
                source_method="POST",
                request_params={"bizSystemId": context.biz_system_id, "componentName": selected_ref.component_name},
                response_excerpt=component_row,
            ),
            _evidence(
                evidence_id="nosql_overview",
                source_api="NoSQL/overview",
                source_path="/server-api/NoSQL/overview",
                source_method="POST",
                request_params={"bizSystemId": context.biz_system_id, "componentName": selected_ref.component_name},
                response_excerpt=overview_row,
            ),
            _evidence(
                evidence_id="nosql_analysis",
                source_api="NoSQL/analysis",
                source_path="/server-api/NoSQL/analysis",
                source_method="POST",
                request_params={"bizSystemId": context.biz_system_id, "componentName": selected_ref.component_name},
                response_excerpt={"top_operations": operation_rows[:3]},
            ),
            _evidence(
                evidence_id="nosql_action_name_list",
                source_api="NoSQL/actionName/list",
                source_path="/server-api/NoSQL/actionName/list",
                source_method="POST",
                request_params={"bizSystemId": context.biz_system_id, "componentName": selected_ref.component_name},
                response_excerpt={"top_actions": impacted_actions[:3]},
            ),
            _evidence(
                evidence_id="nosql_trace",
                source_api="NoSQL/trace",
                source_path="/server-api/NoSQL/trace",
                source_method="POST",
                request_params={"bizSystemId": context.biz_system_id, "componentName": selected_ref.component_name},
                response_excerpt={"top_traces": trace_rows[:3]},
            ),
            _evidence(
                evidence_id="nosql_graph",
                source_api="graph/component/queryNosqlGraph",
                source_path="/server-api/graph/component/queryNosqlGraph",
                source_method="POST",
                request_params={"bizSystemId": context.biz_system_id, "componentName": selected_ref.component_name},
                response_excerpt=component.topology,
            ),
        ]
    )

    payload = NoSQLComponentPackPayload(
        component=dataclass_to_dict(component),
        summary=summary,
        top_operations=operation_rows[:10],
        top_related_traces=trace_rows[:10],
        error_summary=error_summary,
        topology_summary=component.topology,
        suspect_signals=_nosql_component_signals(component, impacted_actions, trace_rows),
        evidence=[dataclass_to_dict(item) for item in evidence],
    )
    page_links = [
        make_console_link(
            adapter,
            context,
            page_type="nosql_component_overview",
            label="NoSQL 组件总览页",
            why_relevant="用于查看 NoSQL 组件的响应、吞吐和错误概况。",
            suggested_report_section="3.4 SQL 检查",
            navigation_path=["业务系统", "NoSQL 组件", selected_ref.component_name],
            suggested_filters={"componentName": selected_ref.component_name, "componentSubtype": selected_ref.component_subtype},
            target_ref={"kind": "nosql_component", "component_name": selected_ref.component_name, "component_subtype": selected_ref.component_subtype},
        ),
        make_console_link(
            adapter,
            context,
            page_type="nosql_topology",
            label="NoSQL 拓扑页",
            why_relevant="用于查看 NoSQL 与上游动作和依赖关系。",
            suggested_report_section="3.4 SQL 检查",
            navigation_path=["业务系统", "NoSQL 组件", selected_ref.component_name, "拓扑"],
            suggested_filters={"componentName": selected_ref.component_name},
            target_ref={"kind": "nosql_component", "component_name": selected_ref.component_name, "component_subtype": selected_ref.component_subtype},
        ),
    ]
    screenshot_hints = [
        make_screenshot_hint(
            title="NoSQL 组件概览截图建议",
            page_type="nosql_component_overview",
            url=page_links[0]["url"],
            recommended_capture=["组件性能摘要", "Top 操作列表", "错误摘要"],
            recommended_annotations=["标注最慢操作", "标注错误类型", "标注组件名称"],
            usage_in_report="可用于说明 Redis/NoSQL 侧热点操作和异常。",
            suggested_report_section="3.4 SQL 检查",
            target_ref=page_links[0]["target_ref"],
            priority="medium",
        )
    ]
    metric_semantics = [
        make_metric_semantic(
            metric_name="response_time_ms",
            subject_type="nosql_component",
            subject_key=f"nosql_component:{selected_ref.component_name}",
            aggregation="average",
            unit="ms",
            time_window=time_window_text(context),
            sample_scope="all NoSQL component calls in selected business scope",
        ),
        make_metric_semantic(
            metric_name="throughput",
            subject_type="nosql_component",
            subject_key=f"nosql_component:{selected_ref.component_name}",
            aggregation="rate",
            unit="rpm",
            time_window=time_window_text(context),
            sample_scope="all NoSQL component calls in selected business scope",
        ),
    ]
    evidence_linkage = {
        "related_time_windows": [dataclass_to_dict(context.time_window)],
        "related_actions": impacted_actions[:5],
        "related_traces": trace_rows[:5],
        "related_sqls": [],
        "related_dependencies": component.topology.get("key_edges") if isinstance(component.topology, dict) else [],
        "recommended_next_pages": page_links,
    }
    payload = apply_report_support(
        payload,
        page_links=page_links,
        screenshot_hints=screenshot_hints,
        metric_semantics=metric_semantics,
        coverage_boundary=default_coverage_boundary(adapter),
        evidence_linkage=evidence_linkage,
    )
    return _pack(
        PackType.NOSQL_COMPONENT.value,
        context,
        payload,
        evidence=evidence,
        warnings=warnings,
        source_mode=source_mode,
    )


def build_connection_pool_pack(
    adapter: Any,
    context: AnalysisContext,
    *,
    source_mode: str = "auto",
    pool_ref: Optional[ConnectionPoolRef] = None,
) -> PackEnvelope:
    warnings: list[WarningMessage] = []
    evidence: list[Evidence] = []

    list_payload, _ = _load_connection_list(adapter, context, source_mode=source_mode)
    list_rows = _extract_content_rows(list_payload)
    pool_row = _match_or_choose_connection_row(list_rows, pool_ref)
    if pool_row is None:
        warnings.append(WarningMessage(code="missing_connection_pool", message="没有找到可用的连接池样本。", source_api="connection/list"))
        payload = ConnectionPoolPackPayload(pool={}, evidence=[])
        return _pack(PackType.CONNECTION_POOL.value, context, payload, evidence=evidence, warnings=warnings)

    selected_ref = ConnectionPoolRef(
        biz_system_id=context.biz_system_id,
        metric_category=pool_row.get("metricCategory"),
        application_id=_int_or_none(pool_row.get("applicationId")),
        instance_id=_int_or_none(pool_row.get("instanceId")),
    )
    chart_payload = _load_connection_chart(adapter, context, selected_ref, pool_row, source_mode=source_mode)
    db_chart_payload = _load_connection_database_chart_from_pool(adapter, context, pool_row, source_mode=source_mode)
    chart_summary = _summarize_connection_chart(chart_payload)
    db_chart_summary = _summarize_chart(db_chart_payload)

    pool = ConnectionPool(
        biz_system_id=context.biz_system_id,
        metric_category=pool_row.get("metricCategory"),
        database_type=pool_row.get("databaseType"),
        framework=pool_row.get("framework"),
        current_used=_int_or_none(pool_row.get("currentUsed")),
        current_idle=_int_or_none(pool_row.get("currentIdle")),
        max_active=_int_or_none(pool_row.get("maxActive") or pool_row.get("initActive")),
        min_idle=_int_or_none(pool_row.get("minIdle")),
        waiter_connections=_int_or_none(chart_summary.get("latest_waiter_connections")),
        connection_time_series=db_chart_summary,
        pools=pool_row.get("pools") or [],
    )

    usage_ratio = None
    if pool.current_used is not None and pool.max_active not in (None, 0):
        usage_ratio = round(pool.current_used / pool.max_active, 4)

    waiter_risk = {
        "latest_waiter_connections": chart_summary.get("latest_waiter_connections"),
        "max_waiter_connections": chart_summary.get("max_waiter_connections"),
        "latest_usage_ratio_pct": chart_summary.get("latest_usage_ratio_pct"),
        "risk_level": _classify_connection_risk(chart_summary),
    }
    summary = {
        "framework": pool.framework,
        "database_type": pool.database_type,
        "metric_category": pool.metric_category,
        "current_used": pool.current_used,
        "current_idle": pool.current_idle,
        "max_active": pool.max_active,
        "usage_ratio": usage_ratio,
        "avg_time_ms": pool_row.get("avgTime"),
        "database_connection_time_avg_ms": db_chart_summary.get("overview", {}).get("avg"),
        "pool_instance_count": len(pool.pools),
    }
    time_series = {
        "used_connections": chart_summary,
        "database_connection_time": db_chart_summary,
    }

    evidence.extend(
        [
            _evidence(
                evidence_id="connection_list",
                source_api="connection/list",
                source_path="/server-api/connection/list",
                source_method="POST",
                request_params={"bizSystemId": context.biz_system_id, "metricCategory": pool.metric_category},
                response_excerpt=pool_row,
            ),
            _evidence(
                evidence_id="connection_chart",
                source_api="connection/chart",
                source_path="/server-api/connection/chart",
                source_method="POST",
                request_params={"bizSystemId": context.biz_system_id, "metricCategory": pool.metric_category},
                response_excerpt=chart_summary,
            ),
            _evidence(
                evidence_id="connection_database_chart",
                source_api="connection/database/chart",
                source_path="/server-api/connection/database/chart",
                source_method="POST",
                request_params={"bizSystemId": context.biz_system_id, "metricCategory": pool.metric_category},
                response_excerpt=db_chart_summary,
            ),
        ]
    )

    payload = ConnectionPoolPackPayload(
        pool=dataclass_to_dict(pool),
        summary=summary,
        time_series=time_series,
        waiter_risk=waiter_risk,
        suspect_signals=_connection_pool_signals(pool_row, chart_summary, db_chart_summary),
        evidence=[dataclass_to_dict(item) for item in evidence],
    )
    pool_ref_dict = {
        "kind": "connection_pool",
        "metric_category": pool.metric_category,
        "application_id": selected_ref.application_id,
        "instance_id": selected_ref.instance_id,
    }
    page_links = [
        make_console_link(
            adapter,
            context,
            page_type="connection_pool_overview",
            label="连接池概览页",
            why_relevant="用于查看池使用率、等待连接和连接时间趋势。",
            suggested_report_section="3.4 SQL 检查",
            navigation_path=["业务系统", "连接池", str(pool.metric_category or pool.framework or "连接池")],
            suggested_filters={"metricCategory": pool.metric_category, "applicationId": selected_ref.application_id, "instanceId": selected_ref.instance_id},
            target_ref=pool_ref_dict,
        )
    ]
    screenshot_hints = [
        make_screenshot_hint(
            title="连接池趋势截图建议",
            page_type="connection_pool_overview",
            url=page_links[0]["url"],
            recommended_capture=["已用连接数趋势", "等待连接数趋势", "数据库连接时间趋势"],
            recommended_annotations=["标出等待连接峰值", "标出高使用率时段", "标出连接时间升高时段"],
            usage_in_report="可用于说明连接池拥塞或连接耗时风险。",
            suggested_report_section="3.4 SQL 检查",
            target_ref=pool_ref_dict,
            priority="medium",
        )
    ]
    metric_semantics = [
        make_metric_semantic(
            metric_name="used_connections",
            subject_type="connection_pool",
            subject_key=f"connection_pool:{pool.metric_category or pool.framework or 'pool'}",
            aggregation="timeseries_latest",
            unit="count",
            time_window=time_window_text(context),
            sample_scope="selected connection pool within business scope",
        ),
        make_metric_semantic(
            metric_name="database_connection_time",
            subject_type="connection_pool",
            subject_key=f"connection_pool:{pool.metric_category or pool.framework or 'pool'}",
            aggregation="timeseries_average",
            unit="ms",
            time_window=time_window_text(context),
            sample_scope="selected connection pool within business scope",
        ),
    ]
    evidence_linkage = {
        "related_time_windows": [dataclass_to_dict(context.time_window)],
        "related_actions": [],
        "related_traces": [],
        "related_sqls": [],
        "related_dependencies": [],
        "recommended_next_pages": page_links,
    }
    payload = apply_report_support(
        payload,
        page_links=page_links,
        screenshot_hints=screenshot_hints,
        metric_semantics=metric_semantics,
        coverage_boundary=default_coverage_boundary(adapter),
        evidence_linkage=evidence_linkage,
    )
    return _pack(
        PackType.CONNECTION_POOL.value,
        context,
        payload,
        evidence=evidence,
        warnings=warnings,
        source_mode=source_mode,
    )


def _load_database_list(adapter: Any, context: AnalysisContext, *, source_mode: str) -> tuple[Any, dict[str, Any]]:
    if _should_use_sample(adapter, source_mode):
        req, resp, warning = _find_sample_pair(
            adapter,
            "Database/list",
            matcher=lambda body, _resp: str(body.get("bizSystemId")) == str(context.biz_system_id),
        )
        return resp, {"warning": warning, "request": req}
    return (
        adapter.database.list_components(
            biz_system_id=context.biz_system_id,
            end_time=context.time_window.end_time,
            time_period=context.time_window.period_minutes,
        ),
        {},
    )


def _load_database_info(adapter: Any, context: AnalysisContext, ref: DatabaseComponentRef, *, source_mode: str, data_type: str) -> Any:
    if _should_use_sample(adapter, source_mode):
        _req, resp, _warning = _find_sample_pair(
            adapter,
            "Database/info",
            matcher=lambda body, _resp: str(body.get("bizSystemId")) == str(context.biz_system_id)
            and body.get("componentName") == ref.component_name
            and body.get("componentSubtype") == ref.component_subtype
            and body.get("dataType") == data_type,
        )
        return resp
    return adapter.database.component_info(
        biz_system_id=context.biz_system_id,
        component_name=ref.component_name,
        component_subtype=ref.component_subtype or "",
        end_time=context.time_window.end_time,
        time_period=context.time_window.period_minutes,
        data_type=data_type,
    )


def _load_database_analysis(adapter: Any, context: AnalysisContext, ref: DatabaseComponentRef, *, source_mode: str) -> Any:
    if _should_use_sample(adapter, source_mode):
        _req, resp, _warning = _find_sample_pair(
            adapter,
            "Database/analysis",
            matcher=lambda body, _resp: str(body.get("bizSystemId")) == str(context.biz_system_id)
            and body.get("componentName") == ref.component_name
            and body.get("componentSubtype") == ref.component_subtype,
        )
        return resp
    return adapter.database.analysis(
        biz_system_id=context.biz_system_id,
        component_name=ref.component_name,
        component_subtype=ref.component_subtype or "",
        end_time=context.time_window.end_time,
        time_period=context.time_window.period_minutes,
    )


def _load_database_impacted_actions(adapter: Any, context: AnalysisContext, ref: DatabaseComponentRef, *, source_mode: str, op_name: str) -> Any:
    encoded_op_name = encode_op_name(op_name) if op_name else ""
    matcher = (
        lambda body, _resp: str(body.get("bizSystemId")) == str(context.biz_system_id)
        and body.get("componentName") == ref.component_name
        and body.get("componentSubtype") == ref.component_subtype
        and (
            (
                op_name
                and body.get("dataType") == "OP"
                and decode_op_name(str(body.get("opName") or "")).decoded == decode_op_name(op_name).decoded
            )
            or (not op_name and body.get("dataType") == "COMP")
        )
    )
    if _should_use_sample(adapter, source_mode):
        _req, resp, _warning = _find_sample_pair(adapter, "component/database/actionList", matcher=matcher)
        return resp
    return adapter.database.action_list(
        biz_system_id=context.biz_system_id,
        component_name=ref.component_name,
        component_subtype=ref.component_subtype or "",
        end_time=context.time_window.end_time,
        time_period=context.time_window.period_minutes,
        data_type="OP" if op_name else "COMP",
        op_name=encoded_op_name,
    )


def _load_database_related_traces(
    adapter: Any,
    context: AnalysisContext,
    ref: DatabaseComponentRef,
    *,
    source_mode: str,
    top_action: Optional[dict[str, Any]],
    op_name: str,
) -> Any:
    if not top_action:
        return {}
    encoded_op_name = encode_op_name(op_name) if op_name else ""
    matcher = (
        lambda body, _resp: str(body.get("bizSystemId")) == str(context.biz_system_id)
        and body.get("componentName") == ref.component_name
        and body.get("componentSubtype") == ref.component_subtype
        and str(body.get("actionId")) == str(top_action.get("actionId"))
        and (
            (
                op_name
                and body.get("dataType") == "OP"
                and decode_op_name(str(body.get("opName") or "")).decoded == decode_op_name(op_name).decoded
            )
            or (not op_name and body.get("dataType") == "COMP")
        )
    )
    if _should_use_sample(adapter, source_mode):
        _req, resp, _warning = _find_sample_pair(adapter, "component/database/actionTraceList", matcher=matcher)
        return resp
    return adapter.database.action_trace_list(
        biz_system_id=context.biz_system_id,
        component_name=ref.component_name,
        component_subtype=ref.component_subtype or "",
        end_time=context.time_window.end_time,
        time_period=context.time_window.period_minutes,
        action_id=int(top_action.get("actionId")),
        action_type=str(top_action.get("actionType") or "TX"),
        data_type="OP" if op_name else "COMP",
        op_name=encoded_op_name,
    )


def _load_database_graph(adapter: Any, context: AnalysisContext, ref: DatabaseComponentRef, *, source_mode: str) -> Any:
    if _should_use_sample(adapter, source_mode):
        _req, resp, _warning = _find_sample_pair(
            adapter,
            "graph/component/queryDataBaseGraph",
            matcher=lambda body, _resp: str(body.get("bizSystemId")) == str(context.biz_system_id)
            and body.get("componentName") == ref.component_name
            and body.get("componentSubtype") == ref.component_subtype,
        )
        return resp
    return adapter.graph.query_database_graph(
        biz_system_id=context.biz_system_id,
        component_name=ref.component_name,
        component_subtype=ref.component_subtype or "",
        end_time=context.time_window.end_time,
        time_period=context.time_window.period_minutes,
    )


def _load_nosql_list(adapter: Any, context: AnalysisContext, *, source_mode: str) -> tuple[Any, dict[str, Any]]:
    if _should_use_sample(adapter, source_mode):
        req, resp, warning = _find_sample_pair(
            adapter,
            "NoSQL/list",
            matcher=lambda body, _resp: str(body.get("bizSystemId")) == str(context.biz_system_id),
        )
        return resp, {"warning": warning, "request": req}
    return (
        adapter.nosql.list_components(
            biz_system_id=context.biz_system_id,
            end_time=context.time_window.end_time,
            time_period=context.time_window.period_minutes,
        ),
        {},
    )


def _load_nosql_overview(adapter: Any, context: AnalysisContext, ref: NoSQLComponentRef, *, source_mode: str) -> Any:
    if _should_use_sample(adapter, source_mode):
        _req, resp, _warning = _find_sample_pair(
            adapter,
            "NoSQL/overview",
            matcher=lambda body, _resp: str(body.get("bizSystemId")) == str(context.biz_system_id)
            and body.get("componentName") == ref.component_name
            and body.get("componentSubtype") == ref.component_subtype,
        )
        return resp
    return adapter.nosql.overview(
        biz_system_id=context.biz_system_id,
        component_name=ref.component_name,
        component_subtype=ref.component_subtype or "",
        end_time=context.time_window.end_time,
        time_period=context.time_window.period_minutes,
    )


def _load_nosql_analysis(adapter: Any, context: AnalysisContext, ref: NoSQLComponentRef, *, source_mode: str) -> Any:
    if _should_use_sample(adapter, source_mode):
        _req, resp, _warning = _find_sample_pair(
            adapter,
            "NoSQL/analysis",
            matcher=lambda body, _resp: str(body.get("bizSystemId")) == str(context.biz_system_id)
            and body.get("componentName") == ref.component_name
            and body.get("componentSubtype") == ref.component_subtype,
        )
        return resp
    return adapter.nosql.analysis(
        biz_system_id=context.biz_system_id,
        component_name=ref.component_name,
        component_subtype=ref.component_subtype or "",
        end_time=context.time_window.end_time,
        time_period=context.time_window.period_minutes,
    )


def _load_nosql_action_names(adapter: Any, context: AnalysisContext, ref: NoSQLComponentRef, *, source_mode: str) -> Any:
    if _should_use_sample(adapter, source_mode):
        _req, resp, _warning = _find_sample_pair(
            adapter,
            "NoSQL/actionName/list",
            matcher=lambda body, _resp: str(body.get("bizSystemId")) == str(context.biz_system_id)
            and body.get("componentName") == ref.component_name
            and body.get("componentSubtype") == ref.component_subtype,
        )
        return resp
    return adapter.nosql.action_name_list(
        biz_system_id=context.biz_system_id,
        component_name=ref.component_name,
        component_subtype=ref.component_subtype or "",
        end_time=context.time_window.end_time,
        time_period=context.time_window.period_minutes,
    )


def _load_nosql_traces(adapter: Any, context: AnalysisContext, ref: NoSQLComponentRef, *, source_mode: str, op_name: str) -> Any:
    if not op_name:
        return {}
    if _should_use_sample(adapter, source_mode):
        _req, resp, _warning = _find_sample_pair(
            adapter,
            "NoSQL/trace",
            matcher=lambda body, _resp: str(body.get("bizSystemId")) == str(context.biz_system_id)
            and body.get("componentName") == ref.component_name
            and body.get("componentSubtype") == ref.component_subtype
            and body.get("opName") == op_name,
        )
        return resp
    return adapter.nosql.trace(
        biz_system_id=context.biz_system_id,
        component_name=ref.component_name,
        component_subtype=ref.component_subtype or "",
        end_time=context.time_window.end_time,
        time_period=context.time_window.period_minutes,
        op_name=op_name,
    )


def _load_nosql_error_types(adapter: Any, context: AnalysisContext, ref: NoSQLComponentRef, *, source_mode: str) -> Any:
    if _should_use_sample(adapter, source_mode):
        _req, resp, _warning = _find_sample_pair(
            adapter,
            "NoSQL/errorTypeAmount",
            matcher=lambda body, _resp: str(body.get("bizSystemId")) == str(context.biz_system_id)
            and body.get("componentName") == ref.component_name,
        )
        return resp
    return adapter.nosql.error_type_amount(
        biz_system_id=context.biz_system_id,
        component_name=ref.component_name,
        end_time=context.time_window.end_time,
        time_period=context.time_window.period_minutes,
    )


def _load_nosql_graph(adapter: Any, context: AnalysisContext, ref: NoSQLComponentRef, *, source_mode: str) -> Any:
    if _should_use_sample(adapter, source_mode):
        _req, resp, _warning = _find_sample_pair(
            adapter,
            "graph/component/queryNosqlGraph",
            matcher=lambda body, _resp: str(body.get("bizSystemId")) == str(context.biz_system_id)
            and body.get("componentName") == ref.component_name
            and body.get("componentSubtype") == ref.component_subtype,
        )
        return resp
    return adapter.graph.query_nosql_graph(
        biz_system_id=context.biz_system_id,
        component_name=ref.component_name,
        component_subtype=ref.component_subtype or "",
        end_time=context.time_window.end_time,
        time_period=context.time_window.period_minutes,
    )


def _load_connection_list(adapter: Any, context: AnalysisContext, *, source_mode: str) -> tuple[Any, dict[str, Any]]:
    if _should_use_sample(adapter, source_mode):
        req, resp, warning = _find_sample_pair(
            adapter,
            "connection/list",
            matcher=lambda body, _resp: str(body.get("bizSystemId")) == str(context.biz_system_id),
        )
        return resp, {"warning": warning, "request": req}
    biz_system_name = _resolve_biz_system_name(adapter, context)
    return (
        adapter.connection.list_pools(
            biz_system_id=context.biz_system_id,
            biz_system_name=biz_system_name,
            begin_time=_begin_time_from_context(context),
            end_time=context.time_window.end_time,
            time_period=context.time_window.period_minutes,
        ),
        {},
    )


def _load_connection_chart(adapter: Any, context: AnalysisContext, ref: ConnectionPoolRef, pool_row: dict[str, Any], *, source_mode: str) -> Any:
    if _should_use_sample(adapter, source_mode):
        _req, resp, _warning = _find_sample_pair(
            adapter,
            "connection/chart",
            matcher=lambda body, _resp: str(body.get("bizSystemId")) == str(context.biz_system_id)
            and body.get("metricCategory") == pool_row.get("metricCategory"),
        )
        return resp
    biz_system_name = _resolve_biz_system_name(adapter, context)
    return adapter.connection.pool_chart(
        biz_system_id=context.biz_system_id,
        biz_system_name=biz_system_name,
        begin_time=_begin_time_from_context(context),
        end_time=context.time_window.end_time,
        time_period=context.time_window.period_minutes,
        metric_category=str(pool_row.get("metricCategory") or ref.metric_category or ""),
        application_id=int(pool_row.get("applicationId") or ref.application_id or 0),
        instance_id=_int_or_none(pool_row.get("instanceId") or ref.instance_id),
    )


def _load_connection_database_chart(adapter: Any, context: AnalysisContext, ref: DatabaseComponentRef, *, source_mode: str) -> Any:
    if _should_use_sample(adapter, source_mode):
        _req, resp, _warning = _find_sample_pair(
            adapter,
            "connection/database/chart",
            matcher=lambda body, _resp: str(body.get("bizSystemId")) == str(context.biz_system_id)
            and body.get("componentName") == ref.component_name
            and body.get("componentSubtype") == ref.component_subtype,
        )
        return resp
    return adapter.connection.database_chart(
        biz_system_id=context.biz_system_id,
        component_name=ref.component_name,
        component_subtype=ref.component_subtype or "",
        end_time=context.time_window.end_time,
        time_period=context.time_window.period_minutes,
    )


def _load_connection_database_chart_from_pool(adapter: Any, context: AnalysisContext, pool_row: dict[str, Any], *, source_mode: str) -> Any:
    component_name = pool_row.get("addressSplit")
    component_subtype = pool_row.get("databaseType")
    if not component_name or not component_subtype:
        return {}
    return _load_connection_database_chart(
        adapter,
        context,
        DatabaseComponentRef(
            biz_system_id=context.biz_system_id,
            component_name=str(component_name),
            component_subtype=str(component_subtype),
        ),
        source_mode=source_mode,
    )


def _find_sample_pair(
    adapter: Any,
    relative_path: str,
    *,
    matcher: Optional[Callable[[dict[str, Any], Any], bool]] = None,
) -> tuple[dict[str, Any], Any, Optional[WarningMessage]]:
    repo = _require_repo(adapter)
    try:
        entry = repo.load_method_entry(relative_path)
    except FileNotFoundError:
        return {}, {}, WarningMessage(code="sample_missing", message=f"未找到样本接口 {relative_path}。", source_api=relative_path)

    sample_requests = entry.get("sample_requests") or []
    sample_responses = entry.get("sample_responses") or []
    for index, request in enumerate(sample_requests):
        request_body = request.get("body") or {}
        response_body = sample_responses[index].get("body") if index < len(sample_responses) else {}
        if matcher is None or matcher(request_body, unwrap_data(response_body) or response_body):
            return request_body, response_body, None

    if sample_requests:
        response_body = sample_responses[0].get("body") if sample_responses else {}
        return (
            sample_requests[0].get("body") or {},
            response_body,
            WarningMessage(code="sample_fallback", message=f"{relative_path} 未找到完全匹配的样本，已回退到首个样本。", source_api=relative_path),
        )
    return {}, {}, WarningMessage(code="sample_empty", message=f"{relative_path} 没有可用的样本请求。", source_api=relative_path)


def _match_or_choose_component_row(rows: list[dict[str, Any]], ref: Optional[Any]) -> Optional[dict[str, Any]]:
    if ref:
        for row in rows:
            if row.get("componentName") == ref.component_name and row.get("componentSubtype") == ref.component_subtype:
                return normalize_metric_fields(dict(row))
    if not rows:
        return None
    normalized = [normalize_metric_fields(dict(row)) for row in rows]
    return max(
        normalized,
        key=lambda row: (
            _numeric(row.get("total_response_time_ms")) or 0.0,
            _numeric(row.get("response_time_ms")) or 0.0,
            _numeric(row.get("traceCount")) or 0.0,
            _numeric(row.get("count")) or 0.0,
        ),
    )


def _preferred_component_from_sample(adapter: Any, relative_path: str, *, biz_system_id: int) -> Optional[dict[str, str]]:
    req, _resp, _warning = _find_sample_pair(
        adapter,
        relative_path,
        matcher=lambda body, _r: str(body.get("bizSystemId")) == str(biz_system_id)
        and body.get("componentName")
        and body.get("componentSubtype"),
    )
    if not req:
        return None
    return {
        "component_name": str(req.get("componentName")),
        "component_subtype": str(req.get("componentSubtype")),
    }


def _match_or_choose_connection_row(rows: list[dict[str, Any]], ref: Optional[ConnectionPoolRef]) -> Optional[dict[str, Any]]:
    if ref and ref.metric_category:
        for row in rows:
            if row.get("metricCategory") == ref.metric_category:
                return row
    if not rows:
        return None
    return max(rows, key=_connection_row_score)


def _connection_row_score(row: dict[str, Any]) -> tuple[float, float, float]:
    used = _numeric(row.get("currentUsed")) or 0.0
    max_active = _numeric(row.get("maxActive")) or 0.0
    ratio = used / max_active if max_active else 0.0
    avg_time = _numeric(row.get("avgTime")) or 0.0
    wait_count = 0.0
    pools = row.get("pools")
    if isinstance(pools, list):
        wait_count = max((_numeric(pool.get("waitCount")) or 0.0 for pool in pools), default=0.0)
    return ratio, avg_time, wait_count


def _extract_content_rows(payload: Any) -> list[dict[str, Any]]:
    data = unwrap_data(payload) or {}
    if isinstance(data, dict) and isinstance(data.get("content"), list):
        return [item for item in data["content"] if isinstance(item, dict)]
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    return []


def _decoded_operation_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    decoded_rows: list[dict[str, Any]] = []
    for row in rows:
        normalized = normalize_metric_fields(dict(row))
        raw_op_name = row.get("opName")
        decoded = decode_op_name(str(raw_op_name)) if raw_op_name else None
        if decoded:
            normalized["op_name_raw"] = raw_op_name
            normalized["op_name_decoded"] = decoded.decoded
            normalized["op_name_is_encoded"] = decoded.is_encoded
        decoded_rows.append(normalized)
    decoded_rows.sort(
        key=lambda row: (
            _numeric(row.get("response_time_ms")) or 0.0,
            _numeric(row.get("total_response_time_ms")) or _numeric(row.get("totalResptime")) or 0.0,
            _numeric(row.get("count")) or 0.0,
        ),
        reverse=True,
    )
    return decoded_rows


def _normalize_component_trace_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized_rows: list[dict[str, Any]] = []
    for row in rows:
        normalized = dict(row)
        if "respTimeMicro" in row:
            normalized["resp_time_ms"] = _numeric(row.get("respTimeMicro"))
        if "actionTimestamp" in row:
            normalized["timestamp"] = row.get("actionTimestamp")
        normalized_rows.append(normalized)
    return normalized_rows


def _summarize_component_graph(payload: Any) -> dict[str, Any]:
    data = unwrap_data(payload) or {}
    return {
        "node_count": len(data.get("nodeDataArray", [])) if isinstance(data.get("nodeDataArray"), list) else 0,
        "line_count": len(data.get("linkeDataArray", [])) if isinstance(data.get("linkeDataArray"), list) else 0,
        "scale": data.get("scale"),
    }


def _summarize_nosql_error_payload(payload: Any) -> dict[str, Any]:
    data = unwrap_data(payload) or {}
    series = data.get("series") if isinstance(data, dict) else None
    if not isinstance(series, list):
        return {"series_count": 0, "series": []}
    return {
        "series_count": len(series),
        "series": series[:10],
    }


def _summarize_connection_chart(payload: Any) -> dict[str, Any]:
    data = unwrap_data(payload) or {}
    series = data.get("series") if isinstance(data, dict) else []
    points: list[dict[str, Any]] = []
    if isinstance(series, list):
        for item in series:
            if isinstance(item, dict) and isinstance(item.get("data"), list):
                points.extend([row for row in item["data"] if isinstance(row, dict)])
    latest = points[-1] if points else None
    latest_metrics = _parse_tooltip_metrics(latest.get("tooltip")) if latest else {}
    max_waiter = 0.0
    latest_usage = None
    latest_used = None
    for point in points:
        metrics = _parse_tooltip_metrics(point.get("tooltip"))
        max_waiter = max(max_waiter, _numeric(metrics.get("Waiter connections")) or 0.0)
        if point is latest:
            latest_usage = _numeric(metrics.get("使用率(%)") or metrics.get("Usage(%)"))
            latest_used = _numeric(
                metrics.get("Used connections")
                or metrics.get("使用连接数")
                or metrics.get("Used")
            )
    return {
        "point_count": len(points),
        "latest_point": latest,
        "latest_used_connections": latest_used if latest_used is not None else (latest.get("y") if latest else None),
        "latest_waiter_connections": _numeric(latest_metrics.get("Waiter connections")) if latest_metrics else None,
        "latest_usage_ratio_pct": latest_usage,
        "latest_connection_time_ms": _numeric(latest_metrics.get("Connection time")) if latest_metrics else None,
        "max_waiter_connections": max_waiter,
    }


def _parse_tooltip_metrics(tooltip: Any) -> dict[str, Any]:
    if not isinstance(tooltip, str) or not tooltip:
        return {}
    try:
        parsed = json.loads(tooltip)
    except json.JSONDecodeError:
        return {}
    rows = parsed.get("data")
    if not isinstance(rows, list):
        return {}
    result: dict[str, Any] = {}
    for item in rows:
        if isinstance(item, dict) and item.get("title") is not None:
            result[str(item.get("title"))] = item.get("value")
    return result


def _classify_connection_risk(summary: dict[str, Any]) -> str:
    max_waiter = _numeric(summary.get("max_waiter_connections")) or 0.0
    latest_usage = _numeric(summary.get("latest_usage_ratio_pct")) or 0.0
    if max_waiter > 0 or latest_usage >= 80:
        return "high"
    if latest_usage >= 60:
        return "medium"
    return "low"


def _database_component_signals(component: DatabaseComponent, related_traces: list[dict[str, Any]], impacted_actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    signals: list[dict[str, Any]] = []
    response_time = _numeric(component.metrics.get("response_time_ms"))
    if response_time and response_time >= 100:
        signals.append(_signal("database_response_time_high_ms", response_time, level="medium", source="Database/info"))
    if impacted_actions:
        signals.append(_signal("database_impacted_action_count", len(impacted_actions), level="info", source="component/database/actionList"))
    if related_traces:
        signals.append(_signal("database_related_trace_count", len(related_traces), level="info", source="component/database/actionTraceList"))
    return signals


def _nosql_component_signals(component: NoSQLComponent, impacted_actions: list[dict[str, Any]], trace_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    signals: list[dict[str, Any]] = []
    if component.top_operations:
        top_operation = component.top_operations[0]
        signals.append(_signal("nosql_top_operation", top_operation.get("op_name_decoded") or top_operation.get("opName"), level="info", source="NoSQL/analysis"))
    if impacted_actions:
        signals.append(_signal("nosql_impacted_action_count", len(impacted_actions), level="medium", source="NoSQL/actionName/list"))
    if not trace_rows:
        signals.append(_signal("nosql_trace_empty", True, level="medium", source="NoSQL/trace"))
    return signals


def _connection_pool_signals(pool_row: dict[str, Any], chart_summary: dict[str, Any], db_chart_summary: dict[str, Any]) -> list[dict[str, Any]]:
    signals: list[dict[str, Any]] = []
    risk = _classify_connection_risk(chart_summary)
    signals.append(_signal("connection_pool_risk_level", risk, level="info", source="connection/chart"))
    latest_waiter = _numeric(chart_summary.get("latest_waiter_connections")) or 0.0
    if latest_waiter > 0:
        signals.append(_signal("connection_pool_waiters_present", latest_waiter, level="high", source="connection/chart"))
    latest_usage = _numeric(chart_summary.get("latest_usage_ratio_pct")) or 0.0
    if latest_usage >= 80:
        signals.append(_signal("connection_pool_usage_high_pct", latest_usage, level="high", source="connection/chart"))
    avg_conn = _numeric((db_chart_summary.get("overview") or {}).get("avg"))
    if avg_conn and avg_conn > 50:
        signals.append(_signal("database_connection_time_high_ms", avg_conn, level="medium", source="connection/database/chart"))
    return signals


def _resolve_biz_system_name(adapter: Any, context: AnalysisContext) -> str:
    overview = unwrap_data(adapter.application.business_overview(
        biz_system_id=context.biz_system_id,
        end_time=context.time_window.end_time,
        time_period=context.time_window.period_minutes,
    )) or {}
    return str(overview.get("bizSystemName") or f"bizSystem-{context.biz_system_id}")


def _begin_time_from_context(context: AnalysisContext) -> str:
    end_value = context.time_window.end_time
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            end_dt = datetime.strptime(end_value, fmt)
            return (end_dt - timedelta(minutes=context.time_window.period_minutes)).strftime(fmt)
        except ValueError:
            continue
    return end_value


def _first_non_none(*values: Any) -> Any:
    for value in values:
        if value is not None:
            return value
    return None


def _int_or_none(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return None
