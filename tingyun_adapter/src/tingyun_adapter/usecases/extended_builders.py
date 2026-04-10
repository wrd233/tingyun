from __future__ import annotations

import re
from typing import Any, Optional

from tingyun_adapter.domain.enums import PackType
from tingyun_adapter.domain.models.common import (
    ActionRef,
    AnalysisContext,
    DatabaseComponentRef,
    Evidence,
    PackEnvelope,
    WarningMessage,
    dataclass_to_dict,
)
from tingyun_adapter.domain.models.entities import Action, Instance
from tingyun_adapter.domain.models.packs import (
    ActionDependencyBreakdownPackPayload,
    DeploymentInventoryPackPayload,
    ExternalDependencyPackPayload,
    InstanceAnalysisPackPayload,
    SlowSQLPackPayload,
    SQLFactSheetPayload,
    TopologyDependencyPackPayload,
)
from tingyun_adapter.normalizers.field_normalizer import unwrap_data
from tingyun_adapter.normalizers.metric_normalizer import normalize_metric_fields
from tingyun_adapter.normalizers.op_name_decoder import decode_op_name, encode_op_name
from tingyun_adapter.usecases.builders import (
    _coerce_evidence_list,
    _evidence,
    _extract_action_rows,
    _load_matching_action_overview,
    _numeric,
    _pack,
    _require_repo,
    _resolve_action_ref,
    _should_use_sample,
    _signal,
    _summarize_chart,
)
from tingyun_adapter.usecases.component_builders import (
    _begin_time_from_context,
    _decoded_operation_rows,
    _extract_content_rows,
    _find_sample_pair,
    _load_connection_list,
    _load_database_analysis,
    _load_database_impacted_actions,
    _load_database_list,
    _load_database_related_traces,
    _match_or_choose_component_row,
    _normalize_component_trace_rows,
    _preferred_component_from_sample,
)
from tingyun_adapter.usecases.report_support import (
    apply_report_support,
    default_coverage_boundary,
    make_console_link,
    make_metric_semantic,
    make_screenshot_hint,
    time_window_text,
)
from tingyun_adapter.usecases.build_session import BuildSession, context_signature, shard_contexts


def _session_lookup(session: Optional[BuildSession], namespace: str, key: Any) -> Any | None:
    if session is None:
        return None
    found, value = session.lookup(namespace, key)
    return value if found else None


def _session_store(session: Optional[BuildSession], namespace: str, key: Any, value: Any) -> Any:
    if session is None:
        return value
    return session.store(namespace, key, value)


def build_instance_analysis_pack(
    adapter: Any,
    context: AnalysisContext,
    *,
    source_mode: str = "auto",
    application_id: Optional[int] = None,
    instance_id: Optional[int] = None,
) -> PackEnvelope:
    warnings: list[WarningMessage] = []
    evidence: list[Evidence] = []

    overview = _load_business_overview(adapter, context, source_mode=source_mode)
    selected_application_id = _resolve_application_id(
        adapter,
        context,
        source_mode=source_mode,
        application_id=application_id,
        overview=overview,
    )
    if selected_application_id is None:
        warnings.append(WarningMessage(code="missing_application_id", message="没有解析出可用的 applicationId。", source_api="application/business/overview"))
        payload = InstanceAnalysisPackPayload(application={}, evidence=[])
        return _pack(PackType.INSTANCE_ANALYSIS.value, context, payload, evidence=evidence, warnings=warnings)

    instances_payload = _load_instance_select(adapter, context, source_mode=source_mode, application_id=selected_application_id)
    instance_rows = _extract_content_rows(instances_payload)
    if not instance_rows:
        warnings.append(WarningMessage(code="missing_instances", message="实例列表为空。", source_api="application/instance/select"))
        payload = InstanceAnalysisPackPayload(application={"application_id": selected_application_id}, evidence=[])
        return _pack(PackType.INSTANCE_ANALYSIS.value, context, payload, evidence=evidence, warnings=warnings)

    selected_row = _match_instance_row(instance_rows, instance_id)
    selected_instance_id = int(selected_row.get("id"))
    cpu_payload = _load_instance_cpu_chart(
        adapter,
        context,
        source_mode=source_mode,
        application_id=selected_application_id,
        instance_id=selected_instance_id,
    )
    jvm_payload = _load_instance_jvm_chart(
        adapter,
        context,
        source_mode=source_mode,
        application_id=selected_application_id,
        instance_id=selected_instance_id,
    )
    cpu_chart = _summarize_chart(cpu_payload)
    jvm_chart = _summarize_chart(jvm_payload)
    if not jvm_chart.get("point_count"):
        warnings.append(WarningMessage(code="instance_jvm_chart_empty", message="JVM 图表为空，当前仅提供 CPU 视角。", source_api="instance/jvm/chart"))

    instances = [_instance_dict_from_row(row, selected_application_id) for row in instance_rows]
    selected_instance = next((item for item in instances if item["id"] == selected_instance_id), instances[0])
    application = {
        "biz_system_id": context.biz_system_id,
        "application_id": selected_application_id,
        "application_name": _resolve_application_name(overview, selected_application_id),
        "instance_count": len(instances),
    }
    summary = {
        "application_id": selected_application_id,
        "instance_count": len(instances),
        "selected_instance_id": selected_instance_id,
        "selected_instance_name": selected_instance.get("name"),
        "distinct_hosts": len({item.get("host_ip") or item.get("host_name") or item.get("name") for item in instances}),
        "cpu_latest_pct": _numeric((cpu_chart.get("latest_point") or {}).get("y")),
        "cpu_peak_pct": cpu_chart.get("max_y"),
        "jvm_point_count": jvm_chart.get("point_count"),
    }

    evidence.extend(
        [
            _evidence(
                evidence_id="instance_list",
                source_api="application/instance/select",
                source_path="/server-api/application/instance/select",
                source_method="POST",
                request_params={"bizSystemId": context.biz_system_id, "applicationId": selected_application_id},
                response_excerpt={"instances": instance_rows[:10]},
            ),
            _evidence(
                evidence_id="instance_cpu_chart",
                source_api="instance/cpu/chart",
                source_path="/server-api/instance/cpu/chart",
                source_method="POST",
                request_params={
                    "bizSystemId": context.biz_system_id,
                    "applicationId": selected_application_id,
                    "instanceId": selected_instance_id,
                },
                response_excerpt=cpu_chart,
            ),
            _evidence(
                evidence_id="instance_jvm_chart",
                source_api="instance/jvm/chart",
                source_path="/server-api/instance/jvm/chart",
                source_method="POST",
                request_params={
                    "bizSystemId": context.biz_system_id,
                    "applicationId": selected_application_id,
                    "instanceId": selected_instance_id,
                },
                response_excerpt=jvm_chart,
            ),
        ]
    )

    payload = InstanceAnalysisPackPayload(
        application=application,
        instances=instances,
        selected_instance=selected_instance,
        summary=summary,
        cpu_chart=cpu_chart,
        jvm_chart=jvm_chart,
        suspect_signals=_instance_analysis_signals(summary, cpu_chart, jvm_chart),
        evidence=[dataclass_to_dict(item) for item in evidence],
    )
    instance_ref = {"kind": "instance", "application_id": selected_application_id, "instance_id": selected_instance_id}
    page_links = [
        make_console_link(
            adapter,
            context,
            page_type="instance_overview",
            label="实例分析页",
            why_relevant="用于查看实例 CPU、JVM 与实例差异。",
            suggested_report_section="3.2 应用检查",
            navigation_path=["业务系统", "应用", str(selected_application_id), "实例", str(selected_instance_id)],
            suggested_filters={"applicationId": selected_application_id, "instanceId": selected_instance_id},
            target_ref=instance_ref,
        )
    ]
    screenshot_hints = [
        make_screenshot_hint(
            title="实例资源趋势截图建议",
            page_type="instance_overview",
            url=page_links[0]["url"],
            recommended_capture=["CPU 趋势图", "JVM 趋势图", "实例列表"],
            recommended_annotations=["标出异常实例", "标出 CPU 峰值时段", "标出 JVM 数据是否缺失"],
            usage_in_report="可用于实例差异和单实例异常举证。",
            suggested_report_section="3.2 应用检查",
            target_ref=instance_ref,
            priority="medium",
        )
    ]
    metric_semantics = [
        make_metric_semantic(
            metric_name="cpu_latest_pct",
            subject_type="instance",
            subject_key=f"instance:{selected_instance_id}",
            aggregation="latest",
            unit="percent",
            time_window=time_window_text(context),
            sample_scope="selected instance",
        ),
        make_metric_semantic(
            metric_name="cpu_peak_pct",
            subject_type="instance",
            subject_key=f"instance:{selected_instance_id}",
            aggregation="max",
            unit="percent",
            time_window=time_window_text(context),
            sample_scope="selected instance",
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
        PackType.INSTANCE_ANALYSIS.value,
        context,
        payload,
        evidence=evidence,
        warnings=warnings,
        source_mode=source_mode,
    )


def build_deployment_inventory_pack(
    adapter: Any,
    context: AnalysisContext,
    *,
    source_mode: str = "auto",
    session: Optional[BuildSession] = None,
) -> PackEnvelope:
    session = session or BuildSession(context=context, source_mode=source_mode)
    cache_key = (context_signature(context), source_mode)
    cached = _session_lookup(session, "pack:deployment_inventory_pack", cache_key)
    if cached is not None:
        return cached

    stats_snapshot = session.snapshot_counters()
    warnings: list[WarningMessage] = []
    evidence: list[Evidence] = []

    overview = _load_business_overview(adapter, context, source_mode=source_mode)
    application_rows = _cached_application_overview_rows(
        adapter,
        context,
        source_mode=source_mode,
        session=session,
        overview=overview,
    )
    application_ids = _deployment_application_ids(overview, application_rows)
    if not application_ids:
        warnings.append(
            WarningMessage(
                code="deployment_inventory_applications_empty",
                message="没有解析出业务系统下的应用清单。",
                source_api="application/business/overview",
            )
        )

    instance_rows_by_app: dict[int, list[dict[str, Any]]] = {}
    all_instance_rows: list[dict[str, Any]] = []
    for application_id in application_ids:
        rows = _cached_instance_rows(
            adapter,
            context,
            application_id=application_id,
            source_mode=source_mode,
            session=session,
        )
        instance_rows_by_app[application_id] = rows
        all_instance_rows.extend(rows)

    service_inventory, service_host_rows, application_name_map = _build_service_inventory(application_rows, instance_rows_by_app)
    host_inventory = _build_host_inventory(service_host_rows)

    connection_rows = _cached_connection_rows(adapter, context, source_mode=source_mode, session=session)
    component_inventory, component_usage_rows = _build_component_inventory(
        connection_rows,
        application_name_map=application_name_map,
        instance_rows_by_app=instance_rows_by_app,
    )

    if not service_inventory:
        warnings.append(
            WarningMessage(
                code="deployment_inventory_service_empty",
                message="没有整理出服务部署清单，可能缺少应用概览或实例列表。",
                source_api="graph/query/overview",
            )
        )
    if not component_inventory:
        warnings.append(
            WarningMessage(
                code="deployment_inventory_components_empty",
                message="没有整理出数据库/Redis 组件清单，可能缺少连接池注册数据。",
                source_api="connection/list",
            )
        )

    biz_system_name = overview.get("bizSystemName") or _biz_system_name_from_application_rows(application_rows) or f"biz_system_{context.biz_system_id}"
    summary = {
        "application_count": len(service_inventory),
        "instance_count": len(all_instance_rows),
        "host_count": len(host_inventory),
        "service_host_row_count": len(service_host_rows),
        "database_component_count": len([item for item in component_inventory if item.get("component_type") == "database"]),
        "nosql_component_count": len([item for item in component_inventory if item.get("component_type") == "nosql"]),
        "detected_technologies": _unique_strings([item.get("technology") for item in service_inventory]),
        "detected_languages": _unique_strings([item.get("language") for item in service_inventory]),
        "detected_component_subtypes": _unique_strings([item.get("component_subtype") for item in component_inventory]),
        "service_inventory_coverage": {
            "has_service_name": len([item for item in service_inventory if item.get("service_name")]),
            "has_technology": len([item for item in service_inventory if item.get("technology")]),
            "has_host_ip": len([item for item in service_host_rows if item.get("host_ip")]),
        },
        "component_inventory_coverage": {
            "has_address": len([item for item in component_inventory if item.get("address")]),
            "has_application_usage": len([item for item in component_inventory if item.get("used_by_applications")]),
        },
    }
    diagnostics = {
        "service_inventory_basis": ["graph/query/overview(application_overview)", "application/instance/select"],
        "component_inventory_basis": ["connection/list"],
        "supported_inventory_depth": [
            "service_name",
            "language",
            "technology",
            "application_to_instance_mapping",
            "host_ip",
            "host_name",
            "database_or_redis_type",
            "component_address",
            "component_to_application_mapping",
            "connection_framework",
        ],
        "known_gaps": [
            "static_host_sizing_not_stable",
            "precise_os_distribution_not_stable",
            "infra_roles_without_agent_not_visible",
        ],
        "field_coverage": {
            "service_name_and_technology_and_host_ip": any(
                item.get("service_name") and (item.get("technology") or item.get("language")) and item.get("host_ip")
                for item in service_host_rows
            ),
            "database_or_redis_and_address_and_used_by_applications": any(
                item.get("component_subtype") and item.get("address") and item.get("used_by_applications")
                for item in component_inventory
            ),
        },
    }

    evidence.extend(
        [
            _evidence(
                evidence_id="deployment_business_overview",
                source_api="application/business/overview",
                source_path=f"/server-api/application/business/overview/{context.biz_system_id}",
                source_method="POST",
                request_params={"bizSystemId": context.biz_system_id, "timeWindow": dataclass_to_dict(context.time_window)},
                response_excerpt={
                    "bizSystemName": overview.get("bizSystemName"),
                    "applicationIds": overview.get("applicationIds"),
                    "instanceIds": overview.get("instanceIds"),
                    "hostCount": overview.get("hostCount"),
                },
            ),
            _evidence(
                evidence_id="deployment_application_overview",
                source_api="graph/query/overview",
                source_path="/server-api/graph/query/overview?application_overview",
                source_method="POST",
                request_params={"bizSystemId": context.biz_system_id, "metric": "application_overview", "timeWindow": dataclass_to_dict(context.time_window)},
                response_excerpt={"applications": application_rows[:10]},
            ),
            _evidence(
                evidence_id="deployment_instance_select",
                source_api="application/instance/select",
                source_path="/server-api/application/instance/select",
                source_method="POST",
                request_params={"bizSystemId": context.biz_system_id, "applicationIds": application_ids},
                response_excerpt={"service_host_rows": service_host_rows[:10]},
            ),
            _evidence(
                evidence_id="deployment_connection_list",
                source_api="connection/list",
                source_path="/server-api/connection/list",
                source_method="POST",
                request_params={"bizSystemId": context.biz_system_id},
                response_excerpt={"component_inventory": component_inventory[:10]},
            ),
        ]
    )

    payload = DeploymentInventoryPackPayload(
        biz_system={"id": context.biz_system_id, "name": biz_system_name},
        summary=summary,
        service_inventory=service_inventory,
        service_host_rows=service_host_rows,
        host_inventory=host_inventory,
        component_inventory=component_inventory,
        component_usage_rows=component_usage_rows,
        diagnostics=diagnostics,
        suspect_signals=_deployment_inventory_signals(
            overview=overview,
            service_inventory=service_inventory,
            service_host_rows=service_host_rows,
            component_inventory=component_inventory,
        ),
        evidence=[dataclass_to_dict(item) for item in evidence],
    )
    biz_ref = {"kind": "biz_system", "biz_system_id": context.biz_system_id}
    page_links = [
        make_console_link(
            adapter,
            context,
            page_type="business_topology",
            label="业务系统拓扑页",
            why_relevant="用于复核应用、主机和数据库/Redis 依赖关系。",
            suggested_report_section="1.1 部署盘点",
            navigation_path=["业务系统", "拓扑"],
            suggested_filters={"bizSystemId": context.biz_system_id},
            target_ref=biz_ref,
        ),
        make_console_link(
            adapter,
            context,
            page_type="connection_pool_overview",
            label="连接池概览页",
            why_relevant="用于复核数据库/Redis 地址、连接框架和应用使用关系。",
            suggested_report_section="1.1 部署盘点",
            navigation_path=["业务系统", "连接池"],
            suggested_filters={"bizSystemId": context.biz_system_id},
            target_ref=biz_ref,
        ),
    ]
    screenshot_hints = [
        make_screenshot_hint(
            title="部署盘点截图建议",
            page_type="business_topology",
            url=page_links[0]["url"],
            recommended_capture=["应用与组件拓扑", "关键应用节点", "数据库/Redis 依赖节点"],
            recommended_annotations=["标出服务节点", "标出数据库或 Redis 地址", "标出主机数量和关键依赖"],
            usage_in_report="可用于部署结构和监控覆盖范围说明。",
            suggested_report_section="1.1 部署盘点",
            target_ref=biz_ref,
            priority="medium",
        )
    ]
    metric_semantics = [
        make_metric_semantic(
            metric_name="application_count",
            subject_type="biz_system",
            subject_key=f"biz_system:{context.biz_system_id}",
            aggregation="count",
            unit="count",
            time_window=time_window_text(context),
            sample_scope="deployment inventory services",
        ),
        make_metric_semantic(
            metric_name="host_count",
            subject_type="biz_system",
            subject_key=f"biz_system:{context.biz_system_id}",
            aggregation="count",
            unit="count",
            time_window=time_window_text(context),
            sample_scope="deployment inventory monitored hosts",
        ),
    ]
    payload = apply_report_support(
        payload,
        page_links=page_links,
        screenshot_hints=screenshot_hints,
        metric_semantics=metric_semantics,
        coverage_boundary=default_coverage_boundary(adapter),
        evidence_linkage={
            "related_time_windows": [dataclass_to_dict(context.time_window)],
            "related_actions": [],
            "related_traces": [],
            "related_sqls": [],
            "related_dependencies": component_inventory[:10],
            "recommended_next_pages": page_links,
        },
    )
    envelope = _pack(
        PackType.DEPLOYMENT_INVENTORY.value,
        context,
        payload,
        evidence=evidence,
        warnings=warnings,
        source_mode=source_mode,
        build_stats=session.build_stats(
            stats_snapshot,
            collection_count=len(service_inventory) + len(component_inventory),
            ranking_count=len(service_inventory) + len(component_inventory),
            deep_dive_count=0,
            extra={
                "service_count": len(service_inventory),
                "host_count": len(host_inventory),
                "component_count": len(component_inventory),
            },
        ),
    )
    return _session_store(session, "pack:deployment_inventory_pack", cache_key, envelope)


def _cached_database_component_rows(
    adapter: Any,
    context: AnalysisContext,
    *,
    source_mode: str,
    session: Optional[BuildSession],
) -> list[dict[str, Any]]:
    cache_key = (context_signature(context), source_mode)
    cached = _session_lookup(session, "raw:database_component_rows", cache_key)
    if cached is not None:
        return cached
    rows = [normalize_metric_fields(row) for row in _extract_content_rows(_load_database_list(adapter, context, source_mode=source_mode)[0])]
    return _session_store(session, "raw:database_component_rows", cache_key, rows)


def _cached_database_analysis_rows(
    adapter: Any,
    context: AnalysisContext,
    ref: DatabaseComponentRef,
    *,
    source_mode: str,
    session: Optional[BuildSession],
) -> list[dict[str, Any]]:
    cache_key = (context_signature(context), ref.component_name, ref.component_subtype, source_mode)
    cached = _session_lookup(session, "raw:database_analysis_rows", cache_key)
    if cached is not None:
        return cached
    rows = _decoded_operation_rows(_extract_content_rows(_load_database_analysis(adapter, context, ref, source_mode=source_mode)))
    return _session_store(session, "raw:database_analysis_rows", cache_key, rows)


def _cached_database_operate_rows(
    adapter: Any,
    context: AnalysisContext,
    ref: DatabaseComponentRef,
    *,
    source_mode: str,
    session: Optional[BuildSession],
) -> list[dict[str, Any]]:
    cache_key = (context_signature(context), ref.component_name, ref.component_subtype, source_mode)
    cached = _session_lookup(session, "raw:database_operate_rows", cache_key)
    if cached is not None:
        return cached
    rows = _extract_content_rows(_load_database_operate_analysis(adapter, context, ref, source_mode=source_mode))
    return _session_store(session, "raw:database_operate_rows", cache_key, rows)


def _cached_database_impacted_action_rows(
    adapter: Any,
    context: AnalysisContext,
    ref: DatabaseComponentRef,
    *,
    source_mode: str,
    op_name: str,
    session: Optional[BuildSession],
) -> list[dict[str, Any]]:
    cache_key = (context_signature(context), ref.component_name, ref.component_subtype, source_mode, op_name)
    cached = _session_lookup(session, "raw:database_impacted_actions", cache_key)
    if cached is not None:
        return cached
    rows = _extract_content_rows(
        _load_database_impacted_actions(
            adapter,
            context,
            ref,
            source_mode=source_mode,
            op_name=op_name,
        )
    )
    return _session_store(session, "raw:database_impacted_actions", cache_key, rows)


def _cached_database_related_trace_rows(
    adapter: Any,
    context: AnalysisContext,
    ref: DatabaseComponentRef,
    *,
    source_mode: str,
    top_action: Optional[dict[str, Any]],
    op_name: str,
    session: Optional[BuildSession],
) -> list[dict[str, Any]]:
    action_key = (
        top_action.get("actionId") if top_action else None,
        top_action.get("actionType") if top_action else None,
    )
    cache_key = (context_signature(context), ref.component_name, ref.component_subtype, source_mode, op_name, action_key)
    cached = _session_lookup(session, "raw:database_related_traces", cache_key)
    if cached is not None:
        return cached
    rows = _normalize_component_trace_rows(
        _extract_content_rows(
            _load_database_related_traces(
                adapter,
                context,
                ref,
                source_mode=source_mode,
                top_action=top_action,
                op_name=op_name,
            )
        )
    )
    return _session_store(session, "raw:database_related_traces", cache_key, rows)


def _merge_external_dependency_payloads(shard_payloads: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for payload in shard_payloads:
        for item in payload.get("external_dependencies") or []:
            key = str(item.get("node_id") or item.get("protocol") or "")
            if not key:
                continue
            existing = merged.get(key)
            if existing is None:
                clone = dict(item)
                clone["shard_hits"] = 1
                merged[key] = clone
                continue
            existing["shard_hits"] = int(existing.get("shard_hits") or 1) + 1
            for metric_key in ("response_time_ms", "error_rate", "throughput", "link_count"):
                if _numeric(item.get(metric_key)) > _numeric(existing.get(metric_key)):
                    existing[metric_key] = item.get(metric_key)
            upstream_nodes = list(existing.get("upstream_nodes") or [])
            for node in item.get("upstream_nodes") or []:
                if node not in upstream_nodes:
                    upstream_nodes.append(node)
            existing["upstream_nodes"] = upstream_nodes
    ranked = sorted(
        merged.values(),
        key=lambda item: (
            _numeric(item.get("response_time_ms")) or 0.0,
            _numeric(item.get("error_rate")) or 0.0,
            int(item.get("shard_hits") or 1),
        ),
        reverse=True,
    )
    return ranked, _external_protocol_summary(ranked)


def _merge_slow_sql_payloads(shard_payloads: list[dict[str, Any]], *, limit: int) -> tuple[list[dict[str, Any]], dict[str, Any], list[dict[str, Any]]]:
    merged: dict[tuple[str, str, str], dict[str, Any]] = {}
    selected_components: list[dict[str, Any]] = []
    for payload in shard_payloads:
        for component in payload.get("selected_components") or []:
            if component not in selected_components:
                selected_components.append(component)
        for row in payload.get("top_sqls") or []:
            key = (
                str(row.get("component_name") or row.get("componentName") or ""),
                str(row.get("component_subtype") or row.get("componentSubtype") or ""),
                str(row.get("op_name_decoded") or row.get("opName") or ""),
            )
            if not key[2]:
                continue
            existing = merged.get(key)
            if existing is None:
                clone = dict(row)
                clone["shard_hits"] = 1
                merged[key] = clone
                continue
            existing["shard_hits"] = int(existing.get("shard_hits") or 1) + 1
            for metric_key in ("response_time_ms", "total_response_time_ms", "traceCount", "count", "error_count", "errorCount"):
                if _numeric(row.get(metric_key)) > _numeric(existing.get(metric_key)):
                    existing[metric_key] = row.get(metric_key)
            if row.get("sql_features") and not existing.get("sql_features"):
                existing["sql_features"] = row.get("sql_features")
    ranked = sorted(
        merged.values(),
        key=lambda row: (
            _numeric(row.get("response_time_ms")) or 0.0,
            _numeric(row.get("total_response_time_ms")) or 0.0,
            int(row.get("shard_hits") or 1),
        ),
        reverse=True,
    )[:limit]
    overview = {
        "component_count": len(selected_components),
        "sql_count": len(merged),
        "statement_type_counts": _statement_type_counts(list(merged.values())),
        "high_trace_sql_count": len([row for row in merged.values() if (_numeric(row.get("traceCount")) or 0.0) > 0]),
    }
    return ranked, overview, selected_components


def build_topology_dependency_pack(
    adapter: Any,
    context: AnalysisContext,
    *,
    source_mode: str = "auto",
    session: Optional[BuildSession] = None,
) -> PackEnvelope:
    session = session or BuildSession(context=context, source_mode=source_mode)
    cache_key = (context_signature(context), source_mode)
    cached = _session_lookup(session, "pack:topology_dependency_pack", cache_key)
    if cached is not None:
        return cached
    warnings: list[WarningMessage] = []
    evidence: list[Evidence] = []

    business_graph_payload = _load_biz_system_graph(adapter, context, source_mode=source_mode)
    detail_graph_payload = _load_biz_detail_graph(adapter, context, source_mode=source_mode)
    detail_graph = unwrap_data(detail_graph_payload) or {}
    health_payload = _load_graph_health(adapter, context, source_mode=source_mode, graph_payload=detail_graph_payload)
    health_map = _health_map(health_payload)

    business_graph = _annotated_graph_summary(unwrap_data(business_graph_payload) or {}, health_map)
    detail_graph_summary = _annotated_graph_summary(detail_graph, health_map)
    dependencies = _dependency_edges(detail_graph, health_map)
    biz_system = {
        "id": context.biz_system_id,
        "name": _biz_system_name_from_graph(detail_graph) or _biz_system_name_from_graph(unwrap_data(business_graph_payload) or {}),
    }

    evidence.extend(
        [
            _evidence(
                evidence_id="biz_system_graph",
                source_api="graph/queryBizSystenGraph",
                source_path="/server-api/graph/queryBizSystenGraph",
                source_method="POST",
                request_params={"timeWindow": dataclass_to_dict(context.time_window)},
                response_excerpt={"node_count": business_graph.get("node_count"), "line_count": business_graph.get("line_count")},
            ),
            _evidence(
                evidence_id="biz_detail_graph",
                source_api="graph/queryBizDetailGraph",
                source_path="/server-api/graph/queryBizDetailGraph",
                source_method="POST",
                request_params={"bizSystemId": context.biz_system_id, "timeWindow": dataclass_to_dict(context.time_window)},
                response_excerpt={"node_count": detail_graph_summary.get("node_count"), "line_count": detail_graph_summary.get("line_count")},
            ),
            _evidence(
                evidence_id="graph_health",
                source_api="graph/queryGraphHealth",
                source_path="/server-api/graph/queryGraphHealth",
                source_method="POST",
                request_params={"bizSystemId": context.biz_system_id, "nodeCount": len(health_map)},
                response_excerpt={"health_nodes": list(health_map.values())[:10]},
            ),
        ]
    )

    payload = TopologyDependencyPackPayload(
        biz_system=biz_system,
        business_graph=business_graph,
        detail_graph=detail_graph_summary,
        node_health=health_map,
        dependencies=dependencies,
        suspect_signals=_topology_signals(detail_graph_summary, dependencies),
        evidence=[dataclass_to_dict(item) for item in evidence],
    )
    biz_ref = {"kind": "biz_system", "biz_system_id": context.biz_system_id}
    page_links = [
        make_console_link(
            adapter,
            context,
            page_type="business_topology",
            label="业务系统拓扑页",
            why_relevant="用于查看用户、应用、数据库和外部依赖之间的调用关系。",
            suggested_report_section="3.2 应用检查",
            navigation_path=["业务系统", "拓扑"],
            suggested_filters={"bizSystemId": context.biz_system_id},
            target_ref=biz_ref,
        )
    ]
    screenshot_hints = [
        make_screenshot_hint(
            title="业务系统拓扑截图建议",
            page_type="business_topology",
            url=page_links[0]["url"],
            recommended_capture=["全局拓扑图", "健康度异常节点", "关键依赖链路"],
            recommended_annotations=["圈出异常应用或依赖", "标出用户入口到异常组件的链路", "标出异常健康节点"],
            usage_in_report="可用于应用关系和影响链路说明。",
            suggested_report_section="3.2 应用检查",
            target_ref=biz_ref,
            priority="high",
        )
    ]
    payload = apply_report_support(
        payload,
        page_links=page_links,
        screenshot_hints=screenshot_hints,
        metric_semantics=[],
        coverage_boundary=default_coverage_boundary(adapter),
        evidence_linkage={
            "related_time_windows": [dataclass_to_dict(context.time_window)],
            "related_actions": [],
            "related_traces": [],
            "related_sqls": [],
            "related_dependencies": dependencies[:10],
            "recommended_next_pages": page_links,
        },
    )
    envelope = _pack(
        PackType.TOPOLOGY_DEPENDENCY.value,
        context,
        payload,
        evidence=evidence,
        warnings=warnings,
        source_mode=source_mode,
    )
    return _session_store(session, "pack:topology_dependency_pack", cache_key, envelope)


def build_external_dependency_pack(
    adapter: Any,
    context: AnalysisContext,
    *,
    source_mode: str = "auto",
    session: Optional[BuildSession] = None,
) -> PackEnvelope:
    session = session or BuildSession(context=context, source_mode=source_mode)
    cache_key = (context_signature(context), source_mode)
    cached = _session_lookup(session, "pack:external_dependency_pack", cache_key)
    if cached is not None:
        return cached
    stats_snapshot = session.snapshot_counters()
    warnings: list[WarningMessage] = []
    evidence: list[Evidence] = []

    shard_context_list = shard_contexts(context, session.time_strategy)
    if len(shard_context_list) > 1:
        shard_payloads: list[dict[str, Any]] = []
        for shard_context in shard_context_list:
            shard_envelope = build_external_dependency_pack(
                adapter,
                shard_context,
                source_mode=source_mode,
                session=session,
            )
            warnings.extend(shard_envelope.meta.warnings)
            shard_payloads.append(shard_envelope.to_dict()["payload"])
        external_dependencies, protocol_summary = _merge_external_dependency_payloads(shard_payloads)
        topology_summary = {
            "node_count": max([(payload.get("topology_summary") or {}).get("node_count") or 0 for payload in shard_payloads] or [0]),
            "line_count": max([(payload.get("topology_summary") or {}).get("line_count") or 0 for payload in shard_payloads] or [0]),
            "external_dependency_count": len(external_dependencies),
            "protocol_count": len(protocol_summary.get("protocols", [])),
        }
        biz_system = {
            "id": context.biz_system_id,
            "name": next(
                (
                    (payload.get("biz_system") or {}).get("name")
                    for payload in shard_payloads
                    if (payload.get("biz_system") or {}).get("name")
                ),
                None,
            ),
        }
        payload = ExternalDependencyPackPayload(
            biz_system=biz_system,
            topology_summary=topology_summary,
            protocol_summary=protocol_summary,
            external_dependencies=external_dependencies,
            suspect_signals=_external_dependency_signals(external_dependencies),
            evidence=[entry for payload in shard_payloads for entry in (payload.get("evidence") or [])],
        )
        biz_ref = {"kind": "biz_system", "biz_system_id": context.biz_system_id}
        page_links = [
            make_console_link(
                adapter,
                context,
                page_type="external_dependency",
                label="外部依赖页",
                why_relevant="用于查看 HTTP、MQ 等外部依赖的调用量、响应和错误。",
                suggested_report_section="3.2 应用检查",
                navigation_path=["业务系统", "外部依赖"],
                suggested_filters={"bizSystemId": context.biz_system_id},
                target_ref=biz_ref,
            )
        ]
        screenshot_hints = [
            make_screenshot_hint(
                title="外部依赖热点截图建议",
                page_type="external_dependency",
                url=page_links[0]["url"],
                recommended_capture=["外部依赖列表", "协议分布", "高延迟依赖"],
                recommended_annotations=["标出高延迟依赖", "标出高错误依赖", "标出受影响上游应用"],
                usage_in_report="可用于外部依赖影响面说明。",
                suggested_report_section="3.2 应用检查",
                target_ref=biz_ref,
                priority="medium",
            )
        ]
        metric_semantics = [
            make_metric_semantic(
                metric_name="response_time_ms",
                subject_type="external_dependency",
                subject_key=f"biz_system:{context.biz_system_id}:external_dependencies",
                aggregation="average",
                unit="ms",
                time_window=time_window_text(context),
                sample_scope="all external dependencies in selected business scope",
            )
        ]
        payload = apply_report_support(
            payload,
            page_links=page_links,
            screenshot_hints=screenshot_hints,
            metric_semantics=metric_semantics,
            coverage_boundary=default_coverage_boundary(adapter),
            evidence_linkage={
                "related_time_windows": [dataclass_to_dict(context.time_window)],
                "related_actions": [],
                "related_traces": [],
                "related_sqls": [],
                "related_dependencies": external_dependencies[:10],
                "recommended_next_pages": page_links,
            },
        )
        envelope = _pack(
            PackType.EXTERNAL_DEPENDENCY.value,
            context,
            payload,
            evidence=_coerce_evidence_list(payload.evidence),
            warnings=warnings,
            source_mode=source_mode,
            build_stats=session.build_stats(
                stats_snapshot,
                collection_count=len(external_dependencies),
                ranking_count=len(external_dependencies),
                deep_dive_count=0,
                extra={"protocol_count": len(protocol_summary.get("protocols", []))},
            ),
        )
        return _session_store(session, "pack:external_dependency_pack", cache_key, envelope)

    detail_graph_payload = _load_biz_detail_graph(adapter, context, source_mode=source_mode)
    detail_graph = unwrap_data(detail_graph_payload) or {}
    health_payload = _load_graph_health(adapter, context, source_mode=source_mode, graph_payload=detail_graph_payload)
    health_map = _health_map(health_payload)

    external_dependencies = _external_dependencies(detail_graph, health_map)
    if not external_dependencies:
        warnings.append(WarningMessage(code="external_dependency_empty", message="当前拓扑中没有识别到外部依赖节点。", source_api="graph/queryBizDetailGraph"))
    protocol_summary = _external_protocol_summary(external_dependencies)
    topology_summary = {
        "node_count": len(detail_graph.get("nodeDataArray", [])) if isinstance(detail_graph.get("nodeDataArray"), list) else 0,
        "line_count": len(detail_graph.get("linkeDataArray", [])) if isinstance(detail_graph.get("linkeDataArray"), list) else 0,
        "external_dependency_count": len(external_dependencies),
        "protocol_count": len(protocol_summary.get("protocols", [])),
    }
    biz_system = {
        "id": context.biz_system_id,
        "name": _biz_system_name_from_graph(detail_graph),
    }

    evidence.extend(
        [
            _evidence(
                evidence_id="external_detail_graph",
                source_api="graph/queryBizDetailGraph",
                source_path="/server-api/graph/queryBizDetailGraph",
                source_method="POST",
                request_params={"bizSystemId": context.biz_system_id, "timeWindow": dataclass_to_dict(context.time_window)},
                response_excerpt={"external_dependencies": external_dependencies[:10]},
            ),
            _evidence(
                evidence_id="external_graph_health",
                source_api="graph/queryGraphHealth",
                source_path="/server-api/graph/queryGraphHealth",
                source_method="POST",
                request_params={"bizSystemId": context.biz_system_id},
                response_excerpt={"health_nodes": [health_map.get(item["node_id"]) for item in external_dependencies[:10]]},
            ),
        ]
    )

    payload = ExternalDependencyPackPayload(
        biz_system=biz_system,
        topology_summary=topology_summary,
        protocol_summary=protocol_summary,
        external_dependencies=external_dependencies,
        suspect_signals=_external_dependency_signals(external_dependencies),
        evidence=[dataclass_to_dict(item) for item in evidence],
    )
    biz_ref = {"kind": "biz_system", "biz_system_id": context.biz_system_id}
    page_links = [
        make_console_link(
            adapter,
            context,
            page_type="external_dependency",
            label="外部依赖页",
            why_relevant="用于查看 HTTP、MQ 等外部依赖的调用量、响应和错误。",
            suggested_report_section="3.2 应用检查",
            navigation_path=["业务系统", "外部依赖"],
            suggested_filters={"bizSystemId": context.biz_system_id},
            target_ref=biz_ref,
        )
    ]
    screenshot_hints = [
        make_screenshot_hint(
            title="外部依赖热点截图建议",
            page_type="external_dependency",
            url=page_links[0]["url"],
            recommended_capture=["外部依赖列表", "协议分布", "高延迟依赖"],
            recommended_annotations=["标出高延迟依赖", "标出高错误依赖", "标出受影响上游应用"],
            usage_in_report="可用于外部依赖影响面说明。",
            suggested_report_section="3.2 应用检查",
            target_ref=biz_ref,
            priority="medium",
        )
    ]
    metric_semantics = [
        make_metric_semantic(
            metric_name="response_time_ms",
            subject_type="external_dependency",
            subject_key=f"biz_system:{context.biz_system_id}:external_dependencies",
            aggregation="average",
            unit="ms",
            time_window=time_window_text(context),
            sample_scope="all external dependencies in selected business scope",
        )
    ]
    payload = apply_report_support(
        payload,
        page_links=page_links,
        screenshot_hints=screenshot_hints,
        metric_semantics=metric_semantics,
        coverage_boundary=default_coverage_boundary(adapter),
        evidence_linkage={
            "related_time_windows": [dataclass_to_dict(context.time_window)],
            "related_actions": [],
            "related_traces": [],
            "related_sqls": [],
            "related_dependencies": external_dependencies[:10],
            "recommended_next_pages": page_links,
        },
    )
    envelope = _pack(
        PackType.EXTERNAL_DEPENDENCY.value,
        context,
        payload,
        evidence=evidence,
        warnings=warnings,
        source_mode=source_mode,
        build_stats=session.build_stats(
            stats_snapshot,
            collection_count=len(external_dependencies),
            ranking_count=len(external_dependencies),
            deep_dive_count=0,
            extra={"protocol_count": len(protocol_summary.get("protocols", []))},
        ),
    )
    return _session_store(session, "pack:external_dependency_pack", cache_key, envelope)


def build_slow_sql_pack(
    adapter: Any,
    context: AnalysisContext,
    *,
    source_mode: str = "auto",
    component_ref: Optional[DatabaseComponentRef] = None,
    limit: int = 10,
    session: Optional[BuildSession] = None,
    preloaded_component_rows: Optional[list[dict[str, Any]]] = None,
) -> PackEnvelope:
    session = session or BuildSession(context=context, source_mode=source_mode)
    cache_key = (
        context_signature(context),
        source_mode,
        dataclass_to_dict(component_ref) if component_ref else None,
        limit,
    )
    cached = _session_lookup(session, "pack:slow_sql_pack", cache_key)
    if cached is not None:
        return cached
    stats_snapshot = session.snapshot_counters()
    warnings: list[WarningMessage] = []
    evidence: list[Evidence] = []
    pool_limits = session.get_pool_limits("slow_sql", fallback_limit=limit)

    shard_context_list = shard_contexts(context, session.time_strategy)
    if component_ref is None and len(shard_context_list) > 1:
        shard_payloads: list[dict[str, Any]] = []
        for shard_context in shard_context_list:
            shard_envelope = build_slow_sql_pack(
                adapter,
                shard_context,
                source_mode=source_mode,
                component_ref=component_ref,
                limit=pool_limits.collection_limit,
                session=session,
            )
            warnings.extend(shard_envelope.meta.warnings)
            shard_payloads.append(shard_envelope.to_dict()["payload"])
        top_sqls, operation_overview, selected_components = _merge_slow_sql_payloads(
            shard_payloads,
            limit=pool_limits.collection_limit,
        )
        scope = {
            "bizSystemId": context.biz_system_id,
            "componentNames": [row.get("componentName") for row in selected_components],
            "limit": limit,
        }
        payload = SlowSQLPackPayload(
            scope=scope,
            selected_components=selected_components,
            top_sqls=top_sqls,
            operation_overview=operation_overview,
            diagnostics={
                "pool_limits": dataclass_to_dict(pool_limits),
                "time_strategy": dataclass_to_dict(session.time_strategy),
                "selected_component_count": len(selected_components),
            },
            suspect_signals=_slow_sql_signals(top_sqls, operation_overview),
            evidence=[entry for shard_payload in shard_payloads for entry in (shard_payload.get("evidence") or [])],
        )
        page_links = [
            make_console_link(
                adapter,
                context,
                page_type="slow_sql_list",
                label="慢 SQL 列表页",
                why_relevant="用于查看业务系统范围内的慢 SQL Top。",
                suggested_report_section="3.4 SQL 检查",
                navigation_path=["业务系统", "数据库组件", "慢 SQL"],
                suggested_filters={"bizSystemId": context.biz_system_id, "componentNames": scope.get("componentNames")},
                target_ref={"kind": "slow_sql_scope", "biz_system_id": context.biz_system_id},
            )
        ]
        screenshot_hints = [
            make_screenshot_hint(
                title="慢 SQL 总表截图建议",
                page_type="slow_sql_list",
                url=page_links[0]["url"],
                recommended_capture=["慢 SQL Top 列表", "语句类型分布", "高 trace SQL 列表"],
                recommended_annotations=["标出最慢 SQL", "标出受影响组件", "标出高调用或高 trace SQL"],
                usage_in_report="可用于慢 SQL 总览和排序说明。",
                suggested_report_section="3.4 SQL 检查",
                target_ref=page_links[0]["target_ref"],
                priority="high",
            )
        ]
        metric_semantics = [
            make_metric_semantic(
                metric_name="response_time_ms",
                subject_type="sql_operation",
                subject_key=f"biz_system:{context.biz_system_id}:slow_sql_top",
                aggregation="average",
                unit="ms",
                time_window=time_window_text(context),
                sample_scope="top SQL operations across selected database components",
            )
        ]
        payload = apply_report_support(
            payload,
            page_links=page_links,
            screenshot_hints=screenshot_hints,
            metric_semantics=metric_semantics,
            coverage_boundary=default_coverage_boundary(adapter),
            evidence_linkage={
                "related_time_windows": [dataclass_to_dict(context.time_window)],
                "related_actions": [],
                "related_traces": [],
                "related_sqls": top_sqls[:10],
                "related_dependencies": [],
                "recommended_next_pages": page_links,
            },
        )
        envelope = _pack(
            PackType.SLOW_SQL.value,
            context,
            payload,
            evidence=_coerce_evidence_list(payload.evidence),
            warnings=warnings,
            source_mode=source_mode,
            build_stats=session.build_stats(
                stats_snapshot,
                collection_count=operation_overview.get("sql_count") or len(top_sqls),
                ranking_count=min(len(top_sqls), pool_limits.ranking_limit),
                deep_dive_count=0,
                extra={"component_count": len(selected_components)},
            ),
        )
        return _session_store(session, "pack:slow_sql_pack", cache_key, envelope)

    component_rows = preloaded_component_rows or _cached_database_component_rows(
        adapter,
        context,
        source_mode=source_mode,
        session=session,
    )
    selected_components = _select_database_components(adapter, context, source_mode=source_mode, component_rows=component_rows, component_ref=component_ref)
    if not selected_components:
        warnings.append(WarningMessage(code="slow_sql_empty_component", message="没有可用的 Database 组件来分析 SQL。", source_api="Database/list"))
        payload = SlowSQLPackPayload(scope={"bizSystemId": context.biz_system_id}, diagnostics={"time_strategy": dataclass_to_dict(session.time_strategy)}, evidence=[])
        envelope = _pack(PackType.SLOW_SQL.value, context, payload, evidence=evidence, warnings=warnings)
        return _session_store(session, "pack:slow_sql_pack", cache_key, envelope)

    aggregated_sqls: list[dict[str, Any]] = []
    for selected in selected_components:
        ref = DatabaseComponentRef(
            biz_system_id=context.biz_system_id,
            component_name=str(selected.get("componentName") or ""),
            component_subtype=selected.get("componentSubtype"),
        )
        analysis_rows = _cached_database_analysis_rows(adapter, context, ref, source_mode=source_mode, session=session)
        operate_rows = _cached_database_operate_rows(adapter, context, ref, source_mode=source_mode, session=session)
        evidence.append(
            _evidence(
                evidence_id=f"slow_sql_analysis_{ref.component_name}",
                source_api="Database/analysis",
                source_path="/server-api/Database/analysis",
                source_method="POST",
                request_params={"bizSystemId": context.biz_system_id, "componentName": ref.component_name},
                response_excerpt={"top_sqls": analysis_rows[:3]},
            )
        )
        evidence.append(
            _evidence(
                evidence_id=f"slow_sql_operate_{ref.component_name}",
                source_api="Database/operate/analysisList",
                source_path="/server-api/Database/operate/analysisList",
                source_method="POST",
                request_params={"bizSystemId": context.biz_system_id, "componentName": ref.component_name},
                response_excerpt={"top_operation_types": operate_rows[:3]},
            )
        )
        for row in analysis_rows:
            aggregated = dict(row)
            aggregated["component_name"] = ref.component_name
            aggregated["component_subtype"] = ref.component_subtype
            aggregated["sql_features"] = _sql_features(aggregated.get("op_name_decoded") or aggregated.get("opName") or "")
            aggregated_sqls.append(aggregated)

    aggregated_sqls.sort(
        key=lambda row: (
            _numeric(row.get("response_time_ms")) or 0.0,
            _numeric(row.get("total_response_time_ms")) or 0.0,
            _numeric(row.get("count")) or 0.0,
        ),
        reverse=True,
    )
    top_sqls = aggregated_sqls[: pool_limits.collection_limit]
    operation_overview = {
        "component_count": len(selected_components),
        "sql_count": len(aggregated_sqls),
        "statement_type_counts": _statement_type_counts(aggregated_sqls),
        "high_trace_sql_count": len([row for row in aggregated_sqls if (_numeric(row.get("traceCount")) or 0.0) > 0]),
    }
    scope = {
        "bizSystemId": context.biz_system_id,
        "componentNames": [row.get("componentName") for row in selected_components],
        "limit": limit,
    }

    payload = SlowSQLPackPayload(
        scope=scope,
        selected_components=selected_components,
        top_sqls=top_sqls,
        operation_overview=operation_overview,
        diagnostics={
            "pool_limits": dataclass_to_dict(pool_limits),
            "time_strategy": dataclass_to_dict(session.time_strategy),
            "selected_component_count": len(selected_components),
        },
        suspect_signals=_slow_sql_signals(top_sqls, operation_overview),
        evidence=[dataclass_to_dict(item) for item in evidence],
    )
    page_links = [
        make_console_link(
            adapter,
            context,
            page_type="slow_sql_list",
            label="慢 SQL 列表页",
            why_relevant="用于查看业务系统范围内的慢 SQL Top。",
            suggested_report_section="3.4 SQL 检查",
            navigation_path=["业务系统", "数据库组件", "慢 SQL"],
            suggested_filters={"bizSystemId": context.biz_system_id, "componentNames": scope.get("componentNames")},
            target_ref={"kind": "slow_sql_scope", "biz_system_id": context.biz_system_id},
        )
    ]
    screenshot_hints = [
        make_screenshot_hint(
            title="慢 SQL 总表截图建议",
            page_type="slow_sql_list",
            url=page_links[0]["url"],
            recommended_capture=["慢 SQL Top 列表", "语句类型分布", "高 trace SQL 列表"],
            recommended_annotations=["标出最慢 SQL", "标出受影响组件", "标出高调用或高 trace SQL"],
            usage_in_report="可用于慢 SQL 总览和排序说明。",
            suggested_report_section="3.4 SQL 检查",
            target_ref=page_links[0]["target_ref"],
            priority="high",
        )
    ]
    metric_semantics = [
        make_metric_semantic(
            metric_name="response_time_ms",
            subject_type="sql_operation",
            subject_key=f"biz_system:{context.biz_system_id}:slow_sql_top",
            aggregation="average",
            unit="ms",
            time_window=time_window_text(context),
            sample_scope="top SQL operations across selected database components",
        )
    ]
    payload = apply_report_support(
        payload,
        page_links=page_links,
        screenshot_hints=screenshot_hints,
        metric_semantics=metric_semantics,
        coverage_boundary=default_coverage_boundary(adapter),
        evidence_linkage={
            "related_time_windows": [dataclass_to_dict(context.time_window)],
            "related_actions": [],
            "related_traces": [],
            "related_sqls": top_sqls[:10],
            "related_dependencies": [],
            "recommended_next_pages": page_links,
        },
    )
    envelope = _pack(
        PackType.SLOW_SQL.value,
        context,
        payload,
        evidence=evidence,
        warnings=warnings,
        source_mode=source_mode,
        build_stats=session.build_stats(
            stats_snapshot,
            collection_count=len(aggregated_sqls),
            ranking_count=min(len(top_sqls), pool_limits.ranking_limit),
            deep_dive_count=0,
            extra={"component_count": len(selected_components)},
        ),
    )
    return _session_store(session, "pack:slow_sql_pack", cache_key, envelope)


def build_sql_fact_sheet(
    adapter: Any,
    context: AnalysisContext,
    *,
    source_mode: str = "auto",
    component_ref: Optional[DatabaseComponentRef] = None,
    op_name: Optional[str] = None,
    limit: int = 10,
    mode: str = "full",
    session: Optional[BuildSession] = None,
    preloaded_component_rows: Optional[list[dict[str, Any]]] = None,
    preloaded_analysis_rows: Optional[list[dict[str, Any]]] = None,
    preloaded_operate_rows: Optional[list[dict[str, Any]]] = None,
    selected_sql_row: Optional[dict[str, Any]] = None,
) -> PackEnvelope:
    session = session or BuildSession(context=context, source_mode=source_mode)
    cache_key = (
        context_signature(context),
        source_mode,
        dataclass_to_dict(component_ref) if component_ref else None,
        op_name,
        limit,
        mode,
    )
    cached = _session_lookup(session, "pack:sql_fact_sheet", cache_key)
    if cached is not None:
        return cached
    stats_snapshot = session.snapshot_counters()
    warnings: list[WarningMessage] = []
    evidence: list[Evidence] = []

    component_rows = preloaded_component_rows or _cached_database_component_rows(
        adapter,
        context,
        source_mode=source_mode,
        session=session,
    )
    selected_component = _resolve_sql_component(adapter, context, source_mode=source_mode, component_rows=component_rows, component_ref=component_ref)
    if not selected_component:
        warnings.append(WarningMessage(code="sql_fact_missing_component", message="没有可用的 Database 组件来构建 SQL fact sheet。", source_api="Database/list"))
        payload = SQLFactSheetPayload(selector={}, diagnostics={"mode": mode}, evidence=[])
        envelope = _pack(PackType.SQL_FACT_SHEET.value, context, payload, evidence=evidence, warnings=warnings)
        return _session_store(session, "pack:sql_fact_sheet", cache_key, envelope)

    ref = DatabaseComponentRef(
        biz_system_id=context.biz_system_id,
        component_name=str(selected_component.get("componentName") or ""),
        component_subtype=selected_component.get("componentSubtype"),
    )
    analysis_rows = preloaded_analysis_rows or _cached_database_analysis_rows(
        adapter,
        context,
        ref,
        source_mode=source_mode,
        session=session,
    )
    if not analysis_rows:
        warnings.append(WarningMessage(code="sql_fact_missing_analysis", message="当前组件没有 SQL 操作样本。", source_api="Database/analysis"))
        payload = SQLFactSheetPayload(
            selector={"componentName": ref.component_name},
            component=selected_component,
            diagnostics={"mode": mode},
            evidence=[],
        )
        envelope = _pack(PackType.SQL_FACT_SHEET.value, context, payload, evidence=evidence, warnings=warnings)
        return _session_store(session, "pack:sql_fact_sheet", cache_key, envelope)

    selected_sql = selected_sql_row or _resolve_sql_row(analysis_rows, op_name)
    if op_name and selected_sql != analysis_rows[0] and not _op_name_matches(selected_sql, op_name):
        warnings.append(WarningMessage(code="sql_fact_fallback", message="未找到指定 SQL，已回退到当前最慢 SQL。", source_api="Database/analysis"))

    related_actions: list[dict[str, Any]] = []
    related_traces: list[dict[str, Any]] = []
    if mode == "full":
        related_actions = _cached_database_impacted_action_rows(
            adapter,
            context,
            ref,
            source_mode=source_mode,
            op_name=str(selected_sql.get("op_name_raw") or selected_sql.get("opName") or ""),
            session=session,
        )[:limit]
        top_action = related_actions[0] if related_actions else None
        related_traces = _cached_database_related_trace_rows(
            adapter,
            context,
            ref,
            source_mode=source_mode,
            top_action=top_action,
            op_name=str(selected_sql.get("op_name_raw") or selected_sql.get("opName") or ""),
            session=session,
        )[:limit]
    operate_rows = preloaded_operate_rows or _cached_database_operate_rows(
        adapter,
        context,
        ref,
        source_mode=source_mode,
        session=session,
    )

    selector = {
        "componentName": ref.component_name,
        "componentSubtype": ref.component_subtype,
        "opName": selected_sql.get("op_name_decoded") or selected_sql.get("opName"),
    }
    sql_features = _sql_features(selected_sql.get("op_name_decoded") or selected_sql.get("opName") or "")
    drilldown_keys = {
        "componentName": ref.component_name,
        "componentSubtype": ref.component_subtype,
        "opName": encode_op_name(str(selected_sql.get("op_name_decoded") or selected_sql.get("opName") or "")),
        "topActionId": top_action.get("actionId") if top_action else None,
        "topActionType": top_action.get("actionType") if top_action else None,
    }

    evidence.extend(
        [
            _evidence(
                evidence_id="sql_fact_analysis",
                source_api="Database/analysis",
                source_path="/server-api/Database/analysis",
                source_method="POST",
                request_params={"bizSystemId": context.biz_system_id, "componentName": ref.component_name},
                response_excerpt={"selected_sql": selected_sql},
            ),
            _evidence(
                evidence_id="sql_fact_operate",
                source_api="Database/operate/analysisList",
                source_path="/server-api/Database/operate/analysisList",
                source_method="POST",
                request_params={"bizSystemId": context.biz_system_id, "componentName": ref.component_name},
                response_excerpt={"top_operation_types": operate_rows[:5]},
            ),
            _evidence(
                evidence_id="sql_fact_actions",
                source_api="component/database/actionList",
                source_path="/server-api/component/database/actionList",
                source_method="POST",
                request_params={"bizSystemId": context.biz_system_id, "componentName": ref.component_name},
                response_excerpt={"related_actions": related_actions[:5]},
            ),
            _evidence(
                evidence_id="sql_fact_traces",
                source_api="component/database/actionTraceList",
                source_path="/server-api/component/database/actionTraceList",
                source_method="POST",
                request_params={"bizSystemId": context.biz_system_id, "componentName": ref.component_name},
                response_excerpt={"related_traces": related_traces[:5]},
            ),
        ]
    )

    payload = SQLFactSheetPayload(
        selector=selector,
        component=selected_component,
        sql=selected_sql,
        sql_features=sql_features,
        related_actions=related_actions,
        related_traces=related_traces,
        drilldown_keys=drilldown_keys,
        diagnostics={
            "mode": mode,
            "time_strategy": dataclass_to_dict(session.time_strategy),
            "reused_analysis_rows": preloaded_analysis_rows is not None,
            "reused_operate_rows": preloaded_operate_rows is not None,
        },
        suspect_signals=_sql_fact_signals(selected_sql, related_actions, related_traces, sql_features),
        evidence=[dataclass_to_dict(item) for item in evidence],
    )
    sql_ref = {
        "kind": "sql",
        "component_name": ref.component_name,
        "component_subtype": ref.component_subtype,
        "op_name": selector.get("opName"),
    }
    page_links = [
        make_console_link(
            adapter,
            context,
            page_type="sql_detail",
            label="SQL 详情页",
            why_relevant="用于查看单条 SQL 的耗时、错误和调用者。",
            suggested_report_section="3.4 SQL 检查",
            navigation_path=["业务系统", "数据库组件", ref.component_name, "SQL 详情"],
            suggested_filters={"componentName": ref.component_name, "componentSubtype": ref.component_subtype, "opName": selector.get("opName")},
            target_ref=sql_ref,
        ),
        make_console_link(
            adapter,
            context,
            page_type="sql_related_actions",
            label="SQL 调用者页",
            why_relevant="用于查看受该 SQL 影响的事务或接口。",
            suggested_report_section="3.4 SQL 检查",
            navigation_path=["业务系统", "数据库组件", ref.component_name, "SQL 调用者"],
            suggested_filters={"componentName": ref.component_name, "opName": selector.get("opName")},
            target_ref=sql_ref,
        ),
    ]
    screenshot_hints = [
        make_screenshot_hint(
            title="SQL 详情截图建议",
            page_type="sql_detail",
            url=page_links[0]["url"],
            recommended_capture=["SQL 指标摘要", "SQL 文本或特征", "耗时/错误相关图表"],
            recommended_annotations=["标出 SQL 指纹", "标出平均耗时", "标出错误次数或 trace 数"],
            usage_in_report="可用于重点 SQL 的核心证据截图。",
            suggested_report_section="3.4 SQL 检查",
            target_ref=sql_ref,
            priority="high",
        ),
        make_screenshot_hint(
            title="SQL 调用者截图建议",
            page_type="sql_related_actions",
            url=page_links[1]["url"],
            recommended_capture=["关联事务列表", "代表性 trace 列表"],
            recommended_annotations=["标出受影响接口", "标出代表性 trace", "标出影响面"],
            usage_in_report="可用于 SQL 与接口/事务关系说明。",
            suggested_report_section="3.4 SQL 检查",
            target_ref=sql_ref,
            priority="high",
        ),
    ]
    metric_semantics = [
        make_metric_semantic(
            metric_name="response_time_ms",
            subject_type="sql_operation",
            subject_key=f"sql:{ref.component_name}:{selector.get('opName')}",
            aggregation="average",
            unit="ms",
            time_window=time_window_text(context),
            sample_scope="selected SQL operation within selected component",
        ),
        make_metric_semantic(
            metric_name="count",
            subject_type="sql_operation",
            subject_key=f"sql:{ref.component_name}:{selector.get('opName')}",
            aggregation="count",
            unit="count",
            time_window=time_window_text(context),
            sample_scope="selected SQL operation within selected component",
        ),
    ]
    payload = apply_report_support(
        payload,
        page_links=page_links,
        screenshot_hints=screenshot_hints,
        metric_semantics=metric_semantics,
        coverage_boundary=default_coverage_boundary(adapter),
        evidence_linkage={
            "related_time_windows": [dataclass_to_dict(context.time_window)],
            "related_actions": related_actions[:5],
            "related_traces": related_traces[:5],
            "related_sqls": [selected_sql],
            "related_dependencies": [],
            "recommended_next_pages": page_links,
        },
    )
    envelope = _pack(
        PackType.SQL_FACT_SHEET.value,
        context,
        payload,
        evidence=evidence,
        warnings=warnings,
        source_mode=source_mode,
        build_stats=session.build_stats(
            stats_snapshot,
            collection_count=len(analysis_rows),
            ranking_count=min(len(analysis_rows), session.get_pool_limits("slow_sql", fallback_limit=limit).ranking_limit),
            deep_dive_count=1 if mode == "full" else 0,
            extra={"mode": mode, "related_action_count": len(related_actions), "related_trace_count": len(related_traces)},
        ),
    )
    return _session_store(session, "pack:sql_fact_sheet", cache_key, envelope)


def build_action_dependency_breakdown_pack(
    adapter: Any,
    context: AnalysisContext,
    *,
    source_mode: str = "auto",
    action_ref: Optional[ActionRef] = None,
) -> PackEnvelope:
    warnings: list[WarningMessage] = []
    evidence: list[Evidence] = []

    action_row, resolved_action_ref, action_warnings = _resolve_breakdown_action_ref(adapter, context, source_mode=source_mode, action_ref=action_ref)
    warnings.extend(action_warnings)
    if resolved_action_ref is None:
        payload = ActionDependencyBreakdownPackPayload(action_ref={}, evidence=[])
        return _pack(PackType.ACTION_DEPENDENCY_BREAKDOWN.value, context, payload, evidence=evidence, warnings=warnings)

    overview_payload = _load_matching_action_overview(
        adapter,
        context,
        source_mode=source_mode,
        action_id=resolved_action_ref.action_id,
        application_id=resolved_action_ref.application_id,
        action_type=resolved_action_ref.action_type,
    )
    breakdown_payload = _load_action_breakdown(adapter, context, source_mode=source_mode, action_ref=resolved_action_ref)
    action_graph_payload = _load_action_graph(adapter, context, source_mode=source_mode, action_ref=resolved_action_ref)

    component_breakdown = [normalize_metric_fields(row) for row in _extract_breakdown_rows(breakdown_payload)]
    component_breakdown.sort(
        key=lambda row: (
            _numeric(row.get("totalResptime") or row.get("totalExclusiveRespTime") or row.get("totalTime")) or 0.0,
            _numeric(row.get("respTime") or row.get("avgExclusiveRespTime")) or 0.0,
            _numeric(row.get("count")) or 0.0,
        ),
        reverse=True,
    )
    graph_data = unwrap_data(action_graph_payload) or {}
    topology_summary = _annotated_graph_summary(graph_data, {})
    breakdown_summary = {
        "component_count": len(component_breakdown),
        "component_type_counts": _component_type_counts(component_breakdown),
        "top_component": component_breakdown[0] if component_breakdown else {},
        "time_slot_count": len((unwrap_data(breakdown_payload) or {}).get("timeActionCounts", []) or []),
        "topology_node_count": topology_summary.get("node_count"),
        "topology_line_count": topology_summary.get("line_count"),
    }

    action = {
        "id": resolved_action_ref.action_id,
        "application_id": resolved_action_ref.application_id,
        "biz_system_id": context.biz_system_id,
        "type": resolved_action_ref.action_type,
        "name": action_row.get("actionName") or (unwrap_data(overview_payload) or {}).get("actionName"),
        "alias": action_row.get("actionAlias") or (unwrap_data(overview_payload) or {}).get("actionAlias"),
        "metrics": {
            "response_time_ms": action_row.get("response_time_ms"),
            "total_response_time_ms": action_row.get("total_response_time_ms"),
            "throughput": action_row.get("throughput"),
            "error_count": action_row.get("error_count"),
            "slow_count": action_row.get("slow_count") or action_row.get("slowCount"),
        },
    }

    evidence.extend(
        [
            _evidence(
                evidence_id="action_breakdown",
                source_api="webaction/performance/breakdown",
                source_path="/server-api/webaction/performance/breakdown",
                source_method="POST",
                request_params={"bizSystemId": context.biz_system_id, "actionId": resolved_action_ref.action_id},
                response_excerpt={"component_breakdown": component_breakdown[:5]},
            ),
            _evidence(
                evidence_id="action_graph",
                source_api="graph/queryActionGraph",
                source_path="/server-api/graph/queryActionGraph",
                source_method="POST",
                request_params={"bizSystemId": context.biz_system_id, "actionId": resolved_action_ref.action_id},
                response_excerpt=topology_summary,
            ),
            _evidence(
                evidence_id="action_overview_for_breakdown",
                source_api="webaction/overview",
                source_path="/server-api/webaction/overview",
                source_method="POST",
                request_params={"bizSystemId": context.biz_system_id, "actionId": resolved_action_ref.action_id},
                response_excerpt=unwrap_data(overview_payload) or {},
            ),
        ]
    )

    payload = ActionDependencyBreakdownPackPayload(
        action_ref=dataclass_to_dict(resolved_action_ref),
        action=action,
        breakdown_summary=breakdown_summary,
        component_breakdown=component_breakdown,
        action_graph=graph_data,
        topology_summary=topology_summary,
        suspect_signals=_action_breakdown_signals(component_breakdown, topology_summary),
        evidence=[dataclass_to_dict(item) for item in evidence],
    )
    action_target = {
        "kind": "action",
        "biz_system_id": context.biz_system_id,
        "application_id": resolved_action_ref.application_id,
        "action_id": resolved_action_ref.action_id,
        "action_type": resolved_action_ref.action_type,
    }
    page_links = [
        make_console_link(
            adapter,
            context,
            page_type="action_dependency_breakdown",
            label="接口依赖拆解页",
            why_relevant="用于查看接口耗时拆分、下游组件构成和依赖拓扑。",
            suggested_report_section="3.3 接口检查",
            navigation_path=["业务系统", "接口", str(resolved_action_ref.action_id), "依赖拆解"],
            suggested_filters={"applicationId": resolved_action_ref.application_id, "actionId": resolved_action_ref.action_id},
            target_ref=action_target,
        )
    ]
    screenshot_hints = [
        make_screenshot_hint(
            title="接口依赖拆解截图建议",
            page_type="action_dependency_breakdown",
            url=page_links[0]["url"],
            recommended_capture=["组件耗时拆分表", "依赖拓扑图", "Top 组件列表"],
            recommended_annotations=["标出耗时占比最高的组件", "标出 SQL 或外部依赖", "标出关键链路"],
            usage_in_report="可用于接口根因方向的证据说明。",
            suggested_report_section="3.3 接口检查",
            target_ref=action_target,
            priority="high",
        )
    ]
    metric_semantics = [
        make_metric_semantic(
            metric_name="component_total_time",
            subject_type="action",
            subject_key=f"action:{resolved_action_ref.action_id}",
            aggregation="sum",
            unit="ms",
            time_window=time_window_text(context),
            sample_scope="dependency components within selected action",
        )
    ]
    payload = apply_report_support(
        payload,
        page_links=page_links,
        screenshot_hints=screenshot_hints,
        metric_semantics=metric_semantics,
        coverage_boundary=default_coverage_boundary(adapter),
        evidence_linkage={
            "related_time_windows": [dataclass_to_dict(context.time_window)],
            "related_actions": [action],
            "related_traces": [],
            "related_sqls": [item for item in component_breakdown[:5] if str(item.get("componentType") or "").lower() in {"database", "sql"}],
            "related_dependencies": component_breakdown[:5],
            "recommended_next_pages": page_links,
        },
    )
    return _pack(
        PackType.ACTION_DEPENDENCY_BREAKDOWN.value,
        context,
        payload,
        evidence=evidence,
        warnings=warnings,
        source_mode=source_mode,
    )


def _load_business_overview(adapter: Any, context: AnalysisContext, *, source_mode: str) -> dict[str, Any]:
    if _should_use_sample(adapter, source_mode):
        repo = _require_repo(adapter)
        return unwrap_data(repo.load_first_sample_response(f"application/business/overview/{context.biz_system_id}")) or {}
    return unwrap_data(
        adapter.application.business_overview(
            biz_system_id=context.biz_system_id,
            end_time=context.time_window.end_time,
            time_period=context.time_window.period_minutes,
        )
    ) or {}


def _load_application_overview(adapter: Any, context: AnalysisContext, *, source_mode: str) -> Any:
    if _should_use_sample(adapter, source_mode):
        _req, resp, _warning = _find_sample_pair(
            adapter,
            "graph/query/overview",
            matcher=lambda body, _resp: body.get("metric") == "application_overview",
        )
        return resp
    return adapter.graph.query_overview(
        metric="application_overview",
        payload={
            "endTime": context.time_window.end_time,
            "labels": {"health": [], "problems": [], "technology": []},
            "lang": context.lang,
            "metric": "application_overview",
            "timePeriod": context.time_window.period_minutes,
            "zoomTime": True,
        },
    )


def _cached_application_overview_rows(
    adapter: Any,
    context: AnalysisContext,
    *,
    source_mode: str,
    session: Optional[BuildSession],
    overview: Optional[dict[str, Any]] = None,
) -> list[dict[str, Any]]:
    cache_key = (context_signature(context), source_mode)
    cached = _session_lookup(session, "raw:application_overview_rows", cache_key)
    if cached is not None:
        return cached
    overview = overview or {}
    application_ids = {str(item) for item in (overview.get("applicationIds") or []) if item is not None}
    rows: list[dict[str, Any]] = []
    for row in _extract_content_rows(_load_application_overview(adapter, context, source_mode=source_mode)):
        normalized = normalize_metric_fields(dict(row))
        system_id = normalized.get("systemId")
        application_id = normalized.get("applicationId")
        if str(system_id) == str(context.biz_system_id) or (application_ids and str(application_id) in application_ids):
            rows.append(normalized)
    rows.sort(
        key=lambda row: (
            _numeric(row.get("totalCount")) or 0.0,
            _numeric(row.get("throughput")) or 0.0,
            _numeric(row.get("responseP50")) or 0.0,
        ),
        reverse=True,
    )
    return _session_store(session, "raw:application_overview_rows", cache_key, rows)


def _resolve_application_id(
    adapter: Any,
    context: AnalysisContext,
    *,
    source_mode: str,
    application_id: Optional[int],
    overview: dict[str, Any],
) -> Optional[int]:
    if application_id:
        return application_id
    application_ids = overview.get("applicationIds")
    if isinstance(application_ids, list) and application_ids:
        try:
            return int(application_ids[0])
        except (TypeError, ValueError):
            pass
    if _should_use_sample(adapter, source_mode):
        req, _resp, _warning = _find_sample_pair(
            adapter,
            "application/instance/select",
            matcher=lambda body, _resp: str(body.get("bizSystemId")) == str(context.biz_system_id),
        )
        value = req.get("applicationId")
        try:
            return int(value) if value is not None else None
        except (TypeError, ValueError):
            return None
    return None


def _resolve_application_name(overview: dict[str, Any], application_id: int) -> Optional[str]:
    if application_id in (overview.get("applicationId"),):
        return overview.get("applicationName")
    return None


def _load_instance_select(adapter: Any, context: AnalysisContext, *, source_mode: str, application_id: int) -> Any:
    if _should_use_sample(adapter, source_mode):
        _req, resp, _warning = _find_sample_pair(
            adapter,
            "application/instance/select",
            matcher=lambda body, _resp: str(body.get("bizSystemId")) == str(context.biz_system_id)
            and str(body.get("applicationId")) == str(application_id),
        )
        return resp
    return adapter.instance.list_instances(
        biz_system_id=context.biz_system_id,
        application_id=application_id,
        end_time=context.time_window.end_time,
        time_period=context.time_window.period_minutes,
    )


def _cached_instance_rows(
    adapter: Any,
    context: AnalysisContext,
    *,
    application_id: int,
    source_mode: str,
    session: Optional[BuildSession],
) -> list[dict[str, Any]]:
    cache_key = (context_signature(context), application_id, source_mode)
    cached = _session_lookup(session, "raw:instance_rows", cache_key)
    if cached is not None:
        return cached
    rows = [normalize_metric_fields(dict(row)) for row in _extract_content_rows(_load_instance_select(adapter, context, source_mode=source_mode, application_id=application_id))]
    return _session_store(session, "raw:instance_rows", cache_key, rows)


def _cached_connection_rows(
    adapter: Any,
    context: AnalysisContext,
    *,
    source_mode: str,
    session: Optional[BuildSession],
) -> list[dict[str, Any]]:
    cache_key = (context_signature(context), source_mode)
    cached = _session_lookup(session, "raw:connection_rows", cache_key)
    if cached is not None:
        return cached
    rows = [normalize_metric_fields(dict(row)) for row in _extract_content_rows(_load_connection_list(adapter, context, source_mode=source_mode)[0])]
    return _session_store(session, "raw:connection_rows", cache_key, rows)


def _load_instance_cpu_chart(
    adapter: Any,
    context: AnalysisContext,
    *,
    source_mode: str,
    application_id: int,
    instance_id: int,
) -> Any:
    if _should_use_sample(adapter, source_mode):
        _req, resp, _warning = _find_sample_pair(
            adapter,
            "instance/cpu/chart",
            matcher=lambda body, _resp: str(body.get("bizSystemId")) == str(context.biz_system_id)
            and str(body.get("applicationId")) == str(application_id)
            and str(body.get("instanceId")) == str(instance_id),
        )
        return resp
    return adapter.instance.cpu_chart(
        biz_system_id=context.biz_system_id,
        application_id=application_id,
        instance_id=instance_id,
        end_time=context.time_window.end_time,
        time_period=context.time_window.period_minutes,
    )


def _load_instance_jvm_chart(
    adapter: Any,
    context: AnalysisContext,
    *,
    source_mode: str,
    application_id: int,
    instance_id: int,
) -> Any:
    if _should_use_sample(adapter, source_mode):
        _req, resp, _warning = _find_sample_pair(
            adapter,
            "instance/jvm/chart",
            matcher=lambda body, _resp: str(body.get("bizSystemId")) == str(context.biz_system_id)
            and str(body.get("applicationId")) == str(application_id)
            and str(body.get("instanceId")) == str(instance_id),
        )
        return resp
    return adapter.instance.jvm_chart(
        biz_system_id=context.biz_system_id,
        application_id=application_id,
        instance_id=instance_id,
        end_time=context.time_window.end_time,
        time_period=context.time_window.period_minutes,
    )


def _match_instance_row(rows: list[dict[str, Any]], instance_id: Optional[int]) -> dict[str, Any]:
    if instance_id:
        for row in rows:
            if str(row.get("id")) == str(instance_id):
                return row
    return rows[0]


def _instance_dict_from_row(row: dict[str, Any], application_id: int) -> dict[str, Any]:
    name = row.get("name")
    parsed = _parse_instance_name(name)
    instance = Instance(
        id=int(row.get("id")),
        application_id=application_id,
        name=name,
        host_ip=str(row.get("hostIp") or row.get("instanceIp") or parsed.get("host_ip") or "") or None,
        host_name=str(row.get("hostName") or parsed.get("host_name") or "") or None,
        os=str(row.get("os") or "") or None,
    )
    return dataclass_to_dict(instance)


def _parse_instance_name(value: Any) -> dict[str, Optional[str]]:
    if not isinstance(value, str):
        return {"host_name": None, "host_ip": None}
    match = re.match(r"(?P<host>[^()]+)\((?P<ip>[^()]+)\)$", value)
    if not match:
        return {"host_name": value, "host_ip": None}
    return {"host_name": match.group("host"), "host_ip": match.group("ip")}


def _instance_analysis_signals(summary: dict[str, Any], cpu_chart: dict[str, Any], jvm_chart: dict[str, Any]) -> list[dict[str, Any]]:
    signals: list[dict[str, Any]] = []
    cpu_peak = _numeric(cpu_chart.get("max_y"))
    if cpu_peak and cpu_peak >= 80:
        signals.append(_signal("instance_cpu_peak_high_pct", cpu_peak, level="high", source="instance/cpu/chart"))
    cpu_latest = _numeric(summary.get("cpu_latest_pct"))
    if cpu_latest and cpu_latest >= 60:
        signals.append(_signal("instance_cpu_latest_high_pct", cpu_latest, level="medium", source="instance/cpu/chart"))
    if (summary.get("instance_count") or 0) > 1:
        signals.append(_signal("instance_count", summary.get("instance_count"), level="info", source="application/instance/select"))
    if not jvm_chart.get("point_count"):
        signals.append(_signal("instance_jvm_chart_empty", True, level="medium", source="instance/jvm/chart"))
    return signals


def _deployment_application_ids(overview: dict[str, Any], application_rows: list[dict[str, Any]]) -> list[int]:
    values: list[int] = []
    for item in overview.get("applicationIds") or []:
        try:
            values.append(int(item))
        except (TypeError, ValueError):
            continue
    if values:
        return sorted(dict.fromkeys(values))
    for row in application_rows:
        try:
            values.append(int(row.get("applicationId")))
        except (TypeError, ValueError):
            continue
    return sorted(dict.fromkeys(values))


def _build_service_inventory(
    application_rows: list[dict[str, Any]],
    instance_rows_by_app: dict[int, list[dict[str, Any]]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[int, str]]:
    app_rows_by_id: dict[int, dict[str, Any]] = {}
    for row in application_rows:
        try:
            app_rows_by_id[int(row.get("applicationId"))] = row
        except (TypeError, ValueError):
            continue

    application_name_map: dict[int, str] = {}
    service_inventory: list[dict[str, Any]] = []
    service_host_rows: list[dict[str, Any]] = []

    for application_id in sorted(set(app_rows_by_id) | set(instance_rows_by_app)):
        app_row = app_rows_by_id.get(application_id, {})
        instances = list(instance_rows_by_app.get(application_id) or [])
        service_name = str(app_row.get("applicationName") or f"application:{application_id}")
        application_name_map[application_id] = service_name
        language = app_row.get("language")
        technology = app_row.get("tech")
        process_names = _unique_strings([row.get("processName") for row in instances])
        host_ips = _unique_strings([row.get("hostIp") or row.get("instanceIp") for row in instances])
        host_names = _unique_strings([row.get("hostName") for row in instances])
        os_types = _unique_strings([row.get("os") for row in instances])

        for row in instances:
            parsed = _parse_instance_name(row.get("name"))
            service_host_rows.append(
                {
                    "application_id": application_id,
                    "service_name": service_name,
                    "language": language,
                    "technology": technology,
                    "instance_id": row.get("id"),
                    "instance_name": row.get("name"),
                    "host_ip": row.get("hostIp") or row.get("instanceIp") or parsed.get("host_ip"),
                    "host_name": row.get("hostName") or parsed.get("host_name"),
                    "process_name": row.get("processName"),
                    "os": row.get("os"),
                }
            )

        service_inventory.append(
            {
                "application_id": application_id,
                "service_name": service_name,
                "language": language,
                "technology": technology,
                "tech_stack": " / ".join([item for item in (language, technology) if item]),
                "instance_count": len(instances),
                "host_count": len(host_ips or host_names),
                "host_ips": host_ips,
                "host_names": host_names,
                "instance_ids": [row.get("id") for row in instances if row.get("id") is not None],
                "process_names": process_names,
                "os_types": os_types,
                "request_count": app_row.get("totalCount"),
                "throughput": app_row.get("throughput"),
                "response_p50_ms": app_row.get("responseP50"),
            }
        )

    service_inventory.sort(
        key=lambda item: (
            _numeric(item.get("request_count")) or 0.0,
            _numeric(item.get("throughput")) or 0.0,
            item.get("service_name") or "",
        ),
        reverse=True,
    )
    service_host_rows.sort(key=lambda item: (item.get("service_name") or "", item.get("host_ip") or "", str(item.get("instance_id") or "")))
    return service_inventory, service_host_rows, application_name_map


def _build_host_inventory(service_host_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    host_map: dict[str, dict[str, Any]] = {}
    for row in service_host_rows:
        host_key = str(row.get("host_ip") or row.get("host_name") or row.get("instance_name") or "")
        if not host_key:
            continue
        host = host_map.setdefault(
            host_key,
            {
                "host_ip": row.get("host_ip"),
                "host_name": row.get("host_name"),
                "os_types": [],
                "services": [],
                "application_ids": [],
                "instance_ids": [],
                "process_names": [],
            },
        )
        host["os_types"] = _merge_unique_values(host.get("os_types"), [row.get("os")])
        host["services"] = _merge_unique_values(host.get("services"), [row.get("service_name")])
        host["application_ids"] = _merge_unique_values(host.get("application_ids"), [row.get("application_id")])
        host["instance_ids"] = _merge_unique_values(host.get("instance_ids"), [row.get("instance_id")])
        host["process_names"] = _merge_unique_values(host.get("process_names"), [row.get("process_name")])
    return sorted(host_map.values(), key=lambda item: (item.get("host_ip") or "", item.get("host_name") or ""))


def _build_component_inventory(
    connection_rows: list[dict[str, Any]],
    *,
    application_name_map: dict[int, str],
    instance_rows_by_app: dict[int, list[dict[str, Any]]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    instance_lookup: dict[tuple[int, int], dict[str, Any]] = {}
    for application_id, rows in instance_rows_by_app.items():
        for row in rows:
            try:
                instance_lookup[(application_id, int(row.get("id")))] = row
            except (TypeError, ValueError):
                continue

    component_map: dict[tuple[str, str, str], dict[str, Any]] = {}
    usage_rows: list[dict[str, Any]] = []
    for row in connection_rows:
        component_subtype = str(row.get("databaseType") or "")
        address = str(row.get("addressSplit") or row.get("address") or "")
        if not component_subtype or not address:
            continue
        component_type = _inventory_component_type(component_subtype)
        database_name = str(row.get("databaseName") or "") or None
        endpoint = _component_endpoint(address, database_name)
        framework = row.get("framework")
        application_id = int(row.get("applicationId")) if row.get("applicationId") not in (None, "") else None
        instance_id = int(row.get("instanceId")) if row.get("instanceId") not in (None, "") else None
        application_name = application_name_map.get(application_id or -1) or (f"application:{application_id}" if application_id is not None else None)
        instance_row = instance_lookup.get((application_id or -1, instance_id or -1), {})

        usage_row = {
            "component_type": component_type,
            "component_subtype": component_subtype,
            "component_endpoint": endpoint,
            "address": address,
            "database_name": database_name,
            "application_id": application_id,
            "application_name": application_name,
            "instance_id": instance_id,
            "instance_name": instance_row.get("name"),
            "host_ip": instance_row.get("hostIp") or instance_row.get("instanceIp"),
            "host_name": instance_row.get("hostName"),
            "framework": framework,
            "metric_category": row.get("metricCategory"),
        }
        usage_rows.append(usage_row)

        key = (component_type, component_subtype, endpoint)
        component = component_map.setdefault(
            key,
            {
                "component_type": component_type,
                "component_subtype": component_subtype,
                "address": address,
                "database_name": database_name,
                "component_endpoint": endpoint,
                "frameworks": [],
                "used_by_applications": [],
                "used_by_application_ids": [],
                "used_by_instances": [],
                "used_by_instance_ids": [],
                "used_by_hosts": [],
                "metric_categories": [],
            },
        )
        component["frameworks"] = _merge_unique_values(component.get("frameworks"), [framework])
        component["used_by_applications"] = _merge_unique_values(component.get("used_by_applications"), [application_name])
        component["used_by_application_ids"] = _merge_unique_values(component.get("used_by_application_ids"), [application_id])
        component["used_by_instances"] = _merge_unique_values(component.get("used_by_instances"), [instance_row.get("name")])
        component["used_by_instance_ids"] = _merge_unique_values(component.get("used_by_instance_ids"), [instance_id])
        component["used_by_hosts"] = _merge_unique_values(component.get("used_by_hosts"), [instance_row.get("hostIp") or instance_row.get("instanceIp")])
        component["metric_categories"] = _merge_unique_values(component.get("metric_categories"), [row.get("metricCategory")])
        component["usage_application_count"] = len(component["used_by_application_ids"])
        component["usage_instance_count"] = len(component["used_by_instance_ids"])

    component_inventory = sorted(component_map.values(), key=lambda item: (item.get("component_type") or "", item.get("component_endpoint") or ""))
    usage_rows.sort(key=lambda item: (item.get("component_type") or "", item.get("component_endpoint") or "", item.get("application_name") or ""))
    return component_inventory, usage_rows


def _inventory_component_type(component_subtype: str) -> str:
    lowered = component_subtype.strip().lower()
    if lowered in {"redis", "mongodb", "memcached", "cassandra", "hbase", "elasticsearch"}:
        return "nosql"
    return "database"


def _component_endpoint(address: str, database_name: Optional[str]) -> str:
    if database_name and f"/{database_name}" not in address:
        return f"{address}/{database_name}"
    return address


def _biz_system_name_from_application_rows(application_rows: list[dict[str, Any]]) -> Optional[str]:
    if not application_rows:
        return None
    system_id = application_rows[0].get("systemId")
    return f"biz_system_{system_id}" if system_id is not None else None


def _merge_unique_values(existing: list[Any], additions: list[Any]) -> list[Any]:
    merged = list(existing or [])
    seen = {repr(item) for item in merged}
    for item in additions:
        if item in (None, "", []):
            continue
        marker = repr(item)
        if marker in seen:
            continue
        seen.add(marker)
        merged.append(item)
    return merged


def _unique_strings(items: list[Any]) -> list[str]:
    values: list[str] = []
    seen: set[str] = set()
    for item in items:
        if item in (None, ""):
            continue
        value = str(item)
        if value in seen:
            continue
        seen.add(value)
        values.append(value)
    return values


def _deployment_inventory_signals(
    *,
    overview: dict[str, Any],
    service_inventory: list[dict[str, Any]],
    service_host_rows: list[dict[str, Any]],
    component_inventory: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    signals: list[dict[str, Any]] = []
    host_count = overview.get("hostCount")
    if host_count is not None:
        signals.append(_signal("monitored_host_count", host_count, level="info", source="application/business/overview"))
    if any(not item.get("host_ip") for item in service_host_rows):
        signals.append(_signal("service_host_ip_partial_missing", True, level="medium", source="application/instance/select"))
    if not component_inventory:
        signals.append(_signal("database_or_redis_inventory_missing", True, level="high", source="connection/list"))
    signals.append(_signal("static_host_sizing_unavailable", True, level="info", source="deployment_inventory_pack"))
    signals.append(_signal("precise_os_distribution_unavailable", True, level="info", source="deployment_inventory_pack"))
    if service_inventory:
        signals.append(_signal("service_inventory_count", len(service_inventory), level="info", source="graph/query/overview"))
    return signals


def _load_biz_system_graph(adapter: Any, context: AnalysisContext, *, source_mode: str) -> Any:
    if _should_use_sample(adapter, source_mode):
        _req, resp, _warning = _find_sample_pair(adapter, "graph/queryBizSystenGraph")
        return resp
    return adapter.graph.query_biz_system_graph(
        end_time=context.time_window.end_time,
        time_period=context.time_window.period_minutes,
    )


def _load_biz_detail_graph(adapter: Any, context: AnalysisContext, *, source_mode: str) -> Any:
    if _should_use_sample(adapter, source_mode):
        _req, resp, _warning = _find_sample_pair(
            adapter,
            "graph/queryBizDetailGraph",
            matcher=lambda body, _resp: str(body.get("bizSystemId")) == str(context.biz_system_id),
        )
        return resp
    return adapter.graph.query_biz_detail_graph(
        biz_system_id=context.biz_system_id,
        end_time=context.time_window.end_time,
        time_period=context.time_window.period_minutes,
    )


def _load_graph_health(adapter: Any, context: AnalysisContext, *, source_mode: str, graph_payload: Any) -> Any:
    node_ids = _graph_node_ids(unwrap_data(graph_payload) or {})
    if not node_ids:
        return {}
    if _should_use_sample(adapter, source_mode):
        _req, resp, _warning = _find_sample_pair(adapter, "graph/queryGraphHealth")
        return resp
    return adapter.graph.query_graph_health(
        end_time=context.time_window.end_time,
        time_period=context.time_window.period_minutes,
        node_ids=node_ids,
    )


def _graph_node_ids(graph: dict[str, Any]) -> dict[str, int]:
    node_ids: dict[str, int] = {}
    for node in graph.get("nodeDataArray", []) if isinstance(graph.get("nodeDataArray"), list) else []:
        if isinstance(node, dict) and node.get("id") and node.get("type") is not None:
            try:
                node_ids[str(node["id"])] = int(node["type"])
            except (TypeError, ValueError):
                continue
    return node_ids


def _health_map(payload: Any) -> dict[str, dict[str, Any]]:
    rows = _extract_content_rows(payload)
    return {str(row.get("id")): row for row in rows if row.get("id")}


def _annotated_graph_summary(graph: dict[str, Any], health_map: dict[str, dict[str, Any]]) -> dict[str, Any]:
    nodes = []
    raw_nodes = graph.get("nodeDataArray", []) if isinstance(graph.get("nodeDataArray"), list) else []
    raw_links = graph.get("linkeDataArray", []) if isinstance(graph.get("linkeDataArray"), list) else []
    for node in raw_nodes:
        if not isinstance(node, dict):
            continue
        node_id = str(node.get("id") or "")
        nodes.append(
            {
                "id": node_id,
                "name": ((node.get("info") or {}).get("name")) or ((node.get("tips") or {}).get("name")),
                "category": _graph_node_category(node),
                "type": node.get("type"),
                "response_time_ms": ((node.get("info") or {}).get("response")),
                "throughput": ((node.get("info") or {}).get("throught")),
                "error_rate": ((node.get("info") or {}).get("error")),
                "health": (health_map.get(node_id) or {}).get("health", (node.get("info") or {}).get("health")),
            }
        )
    links = []
    for link in raw_links:
        if not isinstance(link, dict):
            continue
        links.append(
            {
                "from": link.get("from"),
                "to": link.get("to"),
                "response_time_ms": link.get("response"),
                "throughput": link.get("throught"),
                "error_rate": link.get("error"),
                "slow_error": link.get("slowError"),
            }
        )
    return {
        "node_count": len(nodes),
        "line_count": len(links),
        "node_type_counts": _graph_node_type_counts(nodes),
        "nodes": nodes,
        "links": links,
    }


def _graph_node_category(node: dict[str, Any]) -> str:
    node_id = str(node.get("id") or "")
    if "External_" in node_id or node.get("type") == 17:
        return "external"
    if "Database_" in node_id or node.get("type") == 14:
        return "database"
    if node.get("type") == 12:
        return "application"
    if node.get("type") == 11:
        return "user"
    if node.get("type") == 13:
        return "biz_system"
    return "unknown"


def _graph_node_type_counts(nodes: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for node in nodes:
        category = str(node.get("category") or "unknown")
        counts[category] = counts.get(category, 0) + 1
    return counts


def _dependency_edges(graph: dict[str, Any], health_map: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    annotated = _annotated_graph_summary(graph, health_map)
    node_index = {node["id"]: node for node in annotated["nodes"]}
    dependencies: list[dict[str, Any]] = []
    for link in annotated["links"]:
        source = node_index.get(str(link.get("from")) or "")
        target = node_index.get(str(link.get("to")) or "")
        dependencies.append(
            {
                "from": source.get("name") if source else link.get("from"),
                "from_category": source.get("category") if source else None,
                "to": target.get("name") if target else link.get("to"),
                "to_category": target.get("category") if target else None,
                "response_time_ms": link.get("response_time_ms"),
                "throughput": link.get("throughput"),
                "error_rate": link.get("error_rate"),
                "target_health": target.get("health") if target else None,
            }
        )
    dependencies.sort(key=lambda item: (_numeric(item.get("response_time_ms")) or 0.0, _numeric(item.get("throughput")) or 0.0), reverse=True)
    return dependencies


def _biz_system_name_from_graph(graph: dict[str, Any]) -> Optional[str]:
    nodes = graph.get("nodeDataArray") if isinstance(graph, dict) else None
    if not isinstance(nodes, list):
        return None
    for node in nodes:
        if isinstance(node, dict) and node.get("type") == 13:
            return ((node.get("info") or {}).get("name")) or ((node.get("tips") or {}).get("name"))
    return None


def _topology_signals(detail_graph_summary: dict[str, Any], dependencies: list[dict[str, Any]]) -> list[dict[str, Any]]:
    signals: list[dict[str, Any]] = []
    counts = detail_graph_summary.get("node_type_counts") or {}
    if counts.get("external"):
        signals.append(_signal("topology_external_dependency_count", counts.get("external"), level="info", source="graph/queryBizDetailGraph"))
    if counts.get("database"):
        signals.append(_signal("topology_database_dependency_count", counts.get("database"), level="info", source="graph/queryBizDetailGraph"))
    if dependencies:
        top = dependencies[0]
        if (_numeric(top.get("response_time_ms")) or 0.0) >= 1000:
            signals.append(_signal("topology_slowest_dependency_ms", top.get("response_time_ms"), level="medium", source="graph/queryBizDetailGraph"))
    return signals


def _external_dependencies(graph: dict[str, Any], health_map: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    annotated = _annotated_graph_summary(graph, health_map)
    node_index = {node["id"]: node for node in annotated["nodes"]}
    dependencies: list[dict[str, Any]] = []
    for node in annotated["nodes"]:
        if node.get("category") != "external":
            continue
        related_links = [link for link in annotated["links"] if link.get("to") == node["id"] or link.get("from") == node["id"]]
        upstream = []
        for link in related_links:
            other_id = link.get("from") if link.get("to") == node["id"] else link.get("to")
            other_node = node_index.get(str(other_id))
            if other_node:
                upstream.append({"id": other_node["id"], "name": other_node["name"], "category": other_node["category"]})
        dependencies.append(
            {
                "node_id": node["id"],
                "protocol": node.get("name"),
                "response_time_ms": node.get("response_time_ms"),
                "throughput": node.get("throughput"),
                "error_rate": node.get("error_rate"),
                "health": node.get("health"),
                "upstream_nodes": upstream,
                "link_count": len(related_links),
            }
        )
    dependencies.sort(key=lambda item: (_numeric(item.get("response_time_ms")) or 0.0, _numeric(item.get("throughput")) or 0.0), reverse=True)
    return dependencies


def _external_protocol_summary(items: list[dict[str, Any]]) -> dict[str, Any]:
    protocols = []
    by_protocol: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        key = str(item.get("protocol") or "unknown")
        by_protocol.setdefault(key, []).append(item)
    for protocol, rows in sorted(by_protocol.items()):
        responses = [_numeric(row.get("response_time_ms")) for row in rows if _numeric(row.get("response_time_ms")) is not None]
        protocols.append(
            {
                "protocol": protocol,
                "dependency_count": len(rows),
                "max_response_time_ms": max(responses) if responses else None,
                "avg_response_time_ms": (sum(responses) / len(responses)) if responses else None,
            }
        )
    return {"protocols": protocols}


def _external_dependency_signals(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    signals: list[dict[str, Any]] = []
    if items:
        signals.append(_signal("external_dependency_count", len(items), level="info", source="graph/queryBizDetailGraph"))
    for item in items:
        response_time = _numeric(item.get("response_time_ms")) or 0.0
        if response_time >= 1000:
            signals.append(_signal("external_dependency_response_time_high_ms", response_time, level="medium", source="graph/queryBizDetailGraph"))
            break
    for item in items:
        if (_numeric(item.get("error_rate")) or 0.0) > 0:
            signals.append(_signal("external_dependency_error_rate_present", item.get("error_rate"), level="high", source="graph/queryBizDetailGraph"))
            break
    return signals


def _select_database_components(
    adapter: Any,
    context: AnalysisContext,
    *,
    source_mode: str,
    component_rows: list[dict[str, Any]],
    component_ref: Optional[DatabaseComponentRef],
) -> list[dict[str, Any]]:
    if component_ref:
        chosen = _match_or_choose_component_row(component_rows, component_ref)
        return [chosen] if chosen else []
    if _should_use_sample(adapter, source_mode):
        preferred = _preferred_component_from_sample(adapter, "Database/analysis", biz_system_id=context.biz_system_id)
        if preferred:
            chosen = _match_or_choose_component_row(
                component_rows,
                DatabaseComponentRef(
                    biz_system_id=context.biz_system_id,
                    component_name=preferred["component_name"],
                    component_subtype=preferred["component_subtype"],
                ),
            )
            return [chosen] if chosen else []
    ranked = sorted(
        component_rows,
        key=lambda row: (
            _numeric(row.get("total_response_time_ms")) or 0.0,
            _numeric(row.get("response_time_ms")) or 0.0,
            _numeric(row.get("traceCount")) or 0.0,
        ),
        reverse=True,
    )
    return ranked[:3]


def _resolve_sql_component(
    adapter: Any,
    context: AnalysisContext,
    *,
    source_mode: str,
    component_rows: list[dict[str, Any]],
    component_ref: Optional[DatabaseComponentRef],
) -> Optional[dict[str, Any]]:
    selected = _select_database_components(
        adapter,
        context,
        source_mode=source_mode,
        component_rows=component_rows,
        component_ref=component_ref,
    )
    return selected[0] if selected else None


def _load_database_operate_analysis(adapter: Any, context: AnalysisContext, ref: DatabaseComponentRef, *, source_mode: str) -> Any:
    if _should_use_sample(adapter, source_mode):
        _req, resp, _warning = _find_sample_pair(
            adapter,
            "Database/operate/analysisList",
            matcher=lambda body, _resp: str(body.get("bizSystemId")) == str(context.biz_system_id)
            and body.get("componentName") == ref.component_name
            and body.get("componentSubtype") == ref.component_subtype,
        )
        return resp
    return adapter.database.operate_analysis_list(
        biz_system_id=context.biz_system_id,
        component_name=ref.component_name,
        component_subtype=ref.component_subtype or "",
        end_time=context.time_window.end_time,
        time_period=context.time_window.period_minutes,
    )


def _statement_type_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        statement = ((_sql_features(row.get("op_name_decoded") or row.get("opName") or "")).get("statement_type")) or "UNKNOWN"
        counts[statement] = counts.get(statement, 0) + 1
    return counts


def _slow_sql_signals(top_sqls: list[dict[str, Any]], overview: dict[str, Any]) -> list[dict[str, Any]]:
    signals: list[dict[str, Any]] = []
    if top_sqls:
        top = top_sqls[0]
        signals.append(_signal("slow_sql_count", len(top_sqls), level="info", source="Database/analysis"))
        response_time = _numeric(top.get("response_time_ms"))
        if response_time and response_time >= 1000:
            signals.append(_signal("slowest_sql_response_time_ms", response_time, level="high", source="Database/analysis"))
    if (overview.get("statement_type_counts") or {}).get("SELECT"):
        signals.append(_signal("select_statement_count", overview["statement_type_counts"]["SELECT"], level="info", source="Database/analysis"))
    return signals


def _resolve_sql_row(rows: list[dict[str, Any]], op_name: Optional[str]) -> dict[str, Any]:
    if op_name:
        for row in rows:
            if _op_name_matches(row, op_name):
                return row
    return rows[0]


def _op_name_matches(row: dict[str, Any], target: str) -> bool:
    decoded = decode_op_name(target).decoded
    row_candidates = {
        str(row.get("opName") or ""),
        str(row.get("op_name_raw") or ""),
        str(row.get("op_name_decoded") or ""),
        decode_op_name(str(row.get("opName") or "")).decoded,
    }
    return decoded in row_candidates or target in row_candidates


def _sql_features(sql_text: str) -> dict[str, Any]:
    text = (sql_text or "").strip()
    upper = text.upper()
    statement_type = upper.split(None, 1)[0] if upper else None
    tables: list[str] = []
    for pattern in (
        r"\bFROM\s+([`\"A-Z0-9_\.]+)",
        r"\bJOIN\s+([`\"A-Z0-9_\.]+)",
        r"\bUPDATE\s+([`\"A-Z0-9_\.]+)",
        r"\bINTO\s+([`\"A-Z0-9_\.]+)",
        r"\bDELETE\s+FROM\s+([`\"A-Z0-9_\.]+)",
    ):
        for match in re.finditer(pattern, upper):
            table = match.group(1).strip("`\"")
            if table not in tables:
                tables.append(table)
    tags: list[str] = []
    if " JOIN " in upper:
        tags.append("JOIN")
    if " LEFT JOIN " in upper:
        tags.append("LEFT_JOIN")
    if " UNION ALL " in upper:
        tags.append("UNION_ALL")
    elif " UNION " in upper:
        tags.append("UNION")
    if " GROUP BY " in upper:
        tags.append("GROUP_BY")
    if " ORDER BY " in upper:
        tags.append("ORDER_BY")
    if " DISTINCT " in upper:
        tags.append("DISTINCT")
    if upper.count("SELECT") > 1:
        tags.append("SUBQUERY")
    if re.search(r"\bLIKE\s+['\"]?%", upper):
        tags.append("LIKE_PREFIXLESS")
    if re.search(r"\bIN\s*\((?:[^)]*\?,){4,}", upper) or re.search(r"\bIN\s*\((?:[^)]*,){9,}[^)]*\)", upper):
        tags.append("IN_LARGE_SET")
    if re.search(r"\b(UPPER|LOWER|DATE_FORMAT|SUBSTR|SUBSTRING|TRIM|CAST|CONVERT)\s*\(\s*[A-Z0-9_`\"\.]+\s*\)", upper):
        tags.append("FUNCTION_ON_COLUMN")
    return {
        "statement_type": statement_type,
        "table_candidates": tables[:10],
        "has_join": " JOIN " in upper,
        "has_subquery": upper.count("SELECT") > 1,
        "has_order_by": " ORDER BY " in upper,
        "has_group_by": " GROUP BY " in upper,
        "has_limit": " LIMIT " in upper,
        "has_distinct": " DISTINCT " in upper,
        "tags": tags,
        "length": len(text),
    }


def _sql_fact_signals(
    sql_row: dict[str, Any],
    related_actions: list[dict[str, Any]],
    related_traces: list[dict[str, Any]],
    sql_features: dict[str, Any],
) -> list[dict[str, Any]]:
    signals: list[dict[str, Any]] = []
    response_time = _numeric(sql_row.get("response_time_ms"))
    if response_time and response_time >= 1000:
        signals.append(_signal("sql_response_time_high_ms", response_time, level="high", source="Database/analysis"))
    if sql_features.get("has_join"):
        signals.append(_signal("sql_has_join", True, level="medium", source="Database/analysis"))
    if sql_features.get("has_subquery"):
        signals.append(_signal("sql_has_subquery", True, level="medium", source="Database/analysis"))
    if related_actions:
        signals.append(_signal("sql_related_action_count", len(related_actions), level="info", source="component/database/actionList"))
    if related_traces:
        signals.append(_signal("sql_related_trace_count", len(related_traces), level="info", source="component/database/actionTraceList"))
    return signals


def _resolve_breakdown_action_ref(
    adapter: Any,
    context: AnalysisContext,
    *,
    source_mode: str,
    action_ref: Optional[ActionRef],
) -> tuple[dict[str, Any], Optional[ActionRef], list[WarningMessage]]:
    if action_ref is not None:
        return _resolve_action_ref(adapter, context, source_mode=source_mode, action_ref=action_ref)
    if _should_use_sample(adapter, source_mode):
        req, _resp, warning = _find_sample_pair(
            adapter,
            "webaction/performance/breakdown",
            matcher=lambda body, _resp: str(body.get("bizSystemId")) == str(context.biz_system_id),
        )
        if req:
            resolved = ActionRef(
                biz_system_id=context.biz_system_id,
                application_id=int(req.get("applicationId")),
                action_id=int(req.get("actionId")),
                action_type=str(req.get("actionType") or "TX"),
            )
            return {}, resolved, [warning] if warning else []
    return _resolve_action_ref(adapter, context, source_mode=source_mode, action_ref=None)


def _load_action_breakdown(adapter: Any, context: AnalysisContext, *, source_mode: str, action_ref: ActionRef) -> Any:
    if _should_use_sample(adapter, source_mode):
        _req, resp, _warning = _find_sample_pair(
            adapter,
            "webaction/performance/breakdown",
            matcher=lambda body, _resp: str(body.get("bizSystemId")) == str(context.biz_system_id)
            and str(body.get("applicationId")) == str(action_ref.application_id)
            and str(body.get("actionId")) == str(action_ref.action_id),
        )
        return resp
    return adapter.webaction.performance_breakdown(
        biz_system_id=context.biz_system_id,
        application_id=action_ref.application_id,
        action_id=action_ref.action_id,
        action_type=action_ref.action_type,
        begin_time=_begin_time_from_context(context),
        end_time=context.time_window.end_time,
        time_period=context.time_window.period_minutes,
    )


def _load_action_graph(adapter: Any, context: AnalysisContext, *, source_mode: str, action_ref: ActionRef) -> Any:
    if _should_use_sample(adapter, source_mode):
        _req, resp, _warning = _find_sample_pair(
            adapter,
            "graph/queryActionGraph",
            matcher=lambda body, _resp: str(body.get("bizSystemId")) == str(context.biz_system_id)
            and str(body.get("applicationId")) == str(action_ref.application_id)
            and str(body.get("actionId")) == str(action_ref.action_id),
        )
        return resp
    return adapter.graph.query_action_graph(
        biz_system_id=context.biz_system_id,
        application_id=action_ref.application_id,
        action_id=action_ref.action_id,
        action_type=action_ref.action_type,
        end_time=context.time_window.end_time,
        time_period=context.time_window.period_minutes,
    )


def _component_type_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        key = str(row.get("componentTypeName") or row.get("componentType") or "unknown")
        counts[key] = counts.get(key, 0) + 1
    return counts


def _extract_breakdown_rows(payload: Any) -> list[dict[str, Any]]:
    data = unwrap_data(payload) or {}
    if isinstance(data, dict) and isinstance(data.get("componentItems"), list):
        return [item for item in data["componentItems"] if isinstance(item, dict)]
    return []


def _action_breakdown_signals(component_breakdown: list[dict[str, Any]], topology_summary: dict[str, Any]) -> list[dict[str, Any]]:
    signals: list[dict[str, Any]] = []
    if component_breakdown:
        top = component_breakdown[0]
        signals.append(
            _signal(
                "action_top_component",
                top.get("componentTypeName") or top.get("componentType"),
                level="info",
                source="webaction/performance/breakdown",
            )
        )
        top_resp = _numeric(top.get("respTime") or top.get("avgExclusiveRespTime"))
        if top_resp and top_resp >= 1000:
            signals.append(_signal("action_top_component_response_high_ms", top_resp, level="medium", source="webaction/performance/breakdown"))
    if (topology_summary.get("node_type_counts") or {}).get("database"):
        signals.append(_signal("action_graph_database_node_present", True, level="info", source="graph/queryActionGraph"))
    return signals
