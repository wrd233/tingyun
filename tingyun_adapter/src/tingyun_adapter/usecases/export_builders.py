from __future__ import annotations

import base64
import hashlib
import json
import re
from typing import Any, Optional
from urllib.parse import unquote

from tingyun_adapter.domain.enums import PackType
from tingyun_adapter.domain.models.common import AnalysisContext, Evidence, WarningMessage, dataclass_to_dict
from tingyun_adapter.domain.models.packs import DataExportPackPayload
from tingyun_adapter.usecases.builders import _pack
from tingyun_adapter.usecases.report_support import (
    apply_report_support,
    default_coverage_boundary,
    make_console_link,
    make_metric_semantic,
    make_screenshot_hint,
    time_window_text,
)


DEFAULT_EXPORT_MAX_BYTES = 5_000_000


def build_data_export_pack(
    adapter: Any,
    context: AnalysisContext,
    *,
    source_mode: str = "auto",
    export_kind: Optional[str] = None,
    export_params: Optional[dict[str, Any]] = None,
    execute_export: bool = False,
    include_file_content: bool = True,
    max_export_bytes: int = DEFAULT_EXPORT_MAX_BYTES,
) -> Any:
    warnings: list[WarningMessage] = []
    evidence: list[Evidence] = []
    export_params = dict(export_params or {})

    export_specs = _export_specs()
    available_exports: list[dict[str, Any]] = []
    for spec in export_specs:
        available_exports.append(_catalog_entry(adapter, context, spec, export_params))

    selected_export: dict[str, Any] = {}
    execution: dict[str, Any] = {
        "requested": bool(execute_export),
        "executed": False,
        "status": "catalog_only" if not export_kind else "ready",
    }

    selected_spec = _find_export_spec(export_specs, export_kind)
    if export_kind and selected_spec is None:
        warnings.append(
            WarningMessage(
                code="unsupported_export_kind",
                message=f"Unsupported export kind: {export_kind}",
                source_api="data_export_pack",
            )
        )
        execution["status"] = "unsupported_export_kind"
    elif selected_spec is not None:
        selected_export = _resolve_selected_export(adapter, context, selected_spec, export_params)
        evidence.append(_selected_export_evidence(selected_spec, selected_export))
        execution = {
            "requested": bool(execute_export),
            "executed": False,
            "status": "ready",
            "mode": selected_spec["execution_mode"],
        }
        if execute_export:
            if source_mode == "sample":
                execution.update(
                    {
                        "status": "sample_mode_catalog_only",
                        "reason": "Sample mode only exposes captured request templates and cannot execute live exports.",
                    }
                )
                warnings.append(
                    WarningMessage(
                        code="export_execution_unavailable_in_sample",
                        message="Export execution is unavailable in sample mode; only captured request templates are returned.",
                        source_api=str(selected_spec["path"]),
                    )
                )
            else:
                execution = _execute_selected_export(
                    adapter,
                    selected_spec,
                    selected_export,
                    include_file_content=include_file_content,
                    max_export_bytes=max_export_bytes,
                    warnings=warnings,
                )

    payload = DataExportPackPayload(
        scope={
            "bizSystemId": context.biz_system_id,
            "sourceMode": source_mode,
            "exportKind": export_kind,
            "executeExport": execute_export,
            "includeFileContent": include_file_content,
            "maxExportBytes": max_export_bytes,
        },
        available_exports=available_exports,
        selected_export=selected_export,
        execution=execution,
        diagnostics={
            "available_export_count": len(available_exports),
            "direct_download_count": len([item for item in available_exports if item.get("execution_mode") == "direct_download"]),
            "task_export_count": len([item for item in available_exports if item.get("execution_mode") == "task_api"]),
            "captured_export_count": len([item for item in available_exports if (item.get("captured_support") or {}).get("captured")]),
            "selected_export_kind": export_kind,
        },
        input_dependencies=["captured_api_repository", "live_export_http"],
        derivation_notes=[
            "This pack unifies captured export request templates with optional live execution so upper applications can materialize export files locally.",
            "When executeExport=false, the payload behaves as an export contract/catalog and does not contact the live Tingyun service.",
        ],
        evidence=[dataclass_to_dict(item) for item in evidence],
    )

    biz_ref = {"kind": "biz_system", "biz_system_id": context.biz_system_id}
    page_links = [
        make_console_link(
            adapter,
            context,
            page_type="data_export",
            label="导出能力相关页面",
            why_relevant="用于复核列表页、组件页和错误页中的导出入口。",
            suggested_report_section="0.5 导出取数能力",
            navigation_path=["业务系统", "相关列表页", "导出"],
            suggested_filters={"bizSystemId": context.biz_system_id},
            target_ref=biz_ref,
        )
    ]
    screenshot_hints = [
        make_screenshot_hint(
            title="导出入口截图建议",
            page_type="data_export",
            url=page_links[0]["url"],
            recommended_capture=["导出按钮位置", "导出前筛选条件", "导出后任务提示或下载动作"],
            recommended_annotations=["标出导出入口", "标出导出参数范围", "标出导出对象列表类型"],
            usage_in_report="可用于说明后续脚本筛选所基于的原始导出列表来源。",
            suggested_report_section="0.5 导出取数能力",
            target_ref=biz_ref,
            priority="low",
        )
    ]
    metric_semantics = [
        make_metric_semantic(
            metric_name="available_export_count",
            subject_type="export_capability",
            subject_key=f"biz_system:{context.biz_system_id}:exports",
            aggregation="count",
            unit="count",
            time_window=time_window_text(context),
            sample_scope="captured and modeled export endpoints for the selected business scope",
            confidence="medium",
        )
    ]
    payload = apply_report_support(
        payload,
        page_links=page_links,
        screenshot_hints=screenshot_hints,
        metric_semantics=metric_semantics,
        coverage_boundary=default_coverage_boundary(
            adapter,
            page_reason="This pack models backend export APIs and may not yet cover every SPA export workflow or final async download handoff.",
            available_page_evidence=["captured_export_requests", "replay_templates", "live_download_execution"],
            missing_page_evidence=["every_async_export_final_download_step", "frontend_only_export_dialog_variants"],
        ),
        evidence_linkage={
            "related_time_windows": [dataclass_to_dict(context.time_window)],
            "related_actions": [],
            "related_traces": [],
            "related_sqls": [],
            "related_dependencies": [],
            "recommended_next_pages": page_links,
        },
    )
    return _pack(
        PackType.DATA_EXPORT.value,
        context,
        payload,
        evidence=evidence,
        warnings=warnings,
        source_mode=source_mode,
        build_stats={
            "available_export_count": len(available_exports),
            "executed": bool(execution.get("executed")),
        },
    )


def _export_specs() -> list[dict[str, Any]]:
    return [
        {
            "export_key": "action_list_export",
            "label": "事务列表导出",
            "category": "webaction",
            "execution_mode": "direct_download",
            "method": "GET",
            "path": "/server-api/webaction/list/actionList",
            "captured_relative_path": "webaction/list/actionList",
            "page_type": "action_list",
            "parameter_schema": [
                _param("timePeriod", "query", "integer", True, "统计周期，单位分钟", default_from_context="period_minutes"),
                _param("endTime", "query", "string", True, "结束时间", default_from_context="end_time"),
                _param("bizSystemId", "query", "integer", True, "业务系统 ID", default_from_context="biz_system_id"),
                _param("sortField", "query", "string", False, "排序字段", default="response"),
                _param("sortDirection", "query", "string", False, "排序方向", default="DESC"),
                _param("actionName", "query", "string", False, "按事务名筛选", default=""),
                _param("applicationId", "query", "integer", False, "按应用筛选，0 表示全部", default=0),
                _param("favorites", "query", "boolean", False, "仅导出收藏对象", default=False),
                _param("downloadFile", "query", "boolean", False, "是否启用导出", default=True),
            ],
            "build_request": _build_action_list_export_request,
            "suggested_filename": "action_list_export_{biz_system_id}_{end_time_safe}.bin",
        },
        {
            "export_key": "interface_list_export",
            "label": "服务接口列表导出",
            "category": "webaction",
            "execution_mode": "direct_download",
            "method": "GET",
            "path": "/server-api/webaction/list/interfaceList",
            "captured_relative_path": "webaction/list/interfaceList",
            "page_type": "interface_list",
            "parameter_schema": [
                _param("timePeriod", "query", "integer", True, "统计周期，单位分钟", default_from_context="period_minutes"),
                _param("endTime", "query", "string", True, "结束时间", default_from_context="end_time"),
                _param("bizSystemId", "query", "integer", True, "业务系统 ID", default_from_context="biz_system_id"),
                _param("sortField", "query", "string", False, "排序字段", default="response"),
                _param("sortDirection", "query", "string", False, "排序方向", default="DESC"),
                _param("actionName", "query", "string", False, "按接口名筛选", default=""),
                _param("applicationId", "query", "integer", False, "按应用筛选，0 表示全部", default=0),
                _param("downloadFile", "query", "boolean", False, "是否启用导出", default=True),
            ],
            "build_request": _build_interface_list_export_request,
            "suggested_filename": "interface_list_export_{biz_system_id}_{end_time_safe}.bin",
        },
        {
            "export_key": "component_analysis_export",
            "label": "组件操作分析导出",
            "category": "component",
            "execution_mode": "direct_download",
            "method": "GET",
            "path": "/server-api/Database/analysis/download",
            "captured_relative_path": "Database/analysis/download",
            "page_type": "component_analysis_export",
            "parameter_schema": [
                _param("componentType", "query", "string", True, "组件类型，可为 Database 或 NoSQL", default="Database"),
                _param("bizSystemId", "query", "integer", True, "业务系统 ID", default_from_context="biz_system_id"),
                _param("endTime", "query", "string", True, "结束时间", default_from_context="end_time"),
                _param("timePeriod", "query", "integer", True, "统计周期，单位分钟", default_from_context="period_minutes"),
                _param("dataType", "query", "string", False, "数据层级，通常为 OP", default="OP"),
                _param("componentName", "query", "string", True, "组件名，如数据库地址或 Redis 地址"),
                _param("componentSubtype", "query", "string", True, "组件子类型，如 MySQL/Redis"),
                _param("pageSize", "query", "integer", False, "导出分页大小", default=10000),
                _param("pageNumber", "query", "integer", False, "导出页码", default=1),
                _param("limit", "query", "boolean", False, "是否启用分页限制", default=True),
                _param("sortField", "query", "string", False, "排序字段", default="respTime"),
                _param("sortDirection", "query", "string", False, "排序方向", default="DESC"),
            ],
            "build_request": _build_component_analysis_export_request,
            "suggested_filename": "component_analysis_export_{component_type}_{component_subtype}_{end_time_safe}.xls",
        },
        {
            "export_key": "graph_overview_export",
            "label": "概览图表导出",
            "category": "graph",
            "execution_mode": "direct_download",
            "method": "POST",
            "path": "/server-api/graph/download/overview",
            "captured_relative_path": "graph/download/overview",
            "page_type": "graph_overview_export",
            "parameter_schema": [
                _param("metric", "query+body", "string", True, "导出指标，可为 application_overview 或 request_overview", default="request_overview"),
                _param("endTime", "body", "string", True, "结束时间", default_from_context="end_time"),
                _param("timePeriod", "body", "integer", True, "统计周期，单位分钟", default_from_context="period_minutes"),
                _param("labels", "body", "object", False, "图表标签条件，支持 systemIds / actionTypes / technology / health / problems", default={}),
                _param("zoomTime", "body", "boolean", False, "是否放大时间窗", default=True),
            ],
            "build_request": _build_graph_overview_export_request,
            "suggested_filename": "graph_overview_export_{metric}_{end_time_safe}.bin",
        },
        {
            "export_key": "error_export_task_list",
            "label": "错误导出任务列表",
            "category": "error",
            "execution_mode": "task_api",
            "method": "POST",
            "path": "/server-api/error/smart/errorExport/List",
            "captured_relative_path": "error/smart/errorExport/List",
            "page_type": "error_export",
            "parameter_schema": [
                _param("lang", "body", "string", False, "语言代码", default_from_context="lang"),
            ],
            "build_request": _build_error_export_list_request,
            "suggested_filename": "error_export_task_list_{end_time_safe}.json",
        },
        {
            "export_key": "error_export_create_task",
            "label": "创建错误导出任务",
            "category": "error",
            "execution_mode": "task_api",
            "method": "POST",
            "path": "/server-api/error/smart/errorExport/creatTask",
            "captured_relative_path": "error/smart/errorExport/creatTask",
            "page_type": "error_export",
            "parameter_schema": [
                _param("beginTime", "body", "string", True, "开始时间"),
                _param("bizSystemId", "body", "integer", True, "业务系统 ID", default_from_context="biz_system_id"),
                _param("bizSystemName", "body", "string", False, "业务系统名称"),
                _param("endTime", "body", "string", True, "结束时间", default_from_context="end_time"),
                _param("errorLevel", "body", "string", False, "错误级别", default="ER"),
                _param("exportColumns", "body", "string", False, "导出列配置", default="1,2,3,4,5,13,6,7,8,10"),
                _param("filterParams", "body", "array", False, "筛选条件数组", default=[]),
                _param("localeOptionContent", "body", "string", False, "时间范围文案", default="Custom"),
                _param("serviceGroupId", "body", "integer", False, "服务组 ID", default=0),
                _param("timePeriod", "body", "integer", False, "统计周期，单位分钟", default_from_context="period_minutes"),
            ],
            "build_request": _build_error_export_create_task_request,
            "suggested_filename": "error_export_task_create_{end_time_safe}.json",
        },
    ]


def _param(
    name: str,
    location: str,
    param_type: str,
    required: bool,
    description: str,
    *,
    default: Any = None,
    default_from_context: Optional[str] = None,
) -> dict[str, Any]:
    return {
        "name": name,
        "location": location,
        "type": param_type,
        "required": required,
        "description": description,
        "default": default,
        "default_from_context": default_from_context,
    }


def _catalog_entry(adapter: Any, context: AnalysisContext, spec: dict[str, Any], export_params: dict[str, Any]) -> dict[str, Any]:
    captured = _captured_method_summary(adapter, spec["captured_relative_path"], spec["method"])
    resolved = spec["build_request"](context, export_params)
    return {
        "export_key": spec["export_key"],
        "label": spec["label"],
        "category": spec["category"],
        "execution_mode": spec["execution_mode"],
        "source_api": spec["captured_relative_path"],
        "request_contract": {
            "method": spec["method"],
            "path": spec["path"],
            "query": resolved.get("query") or {},
            "body": resolved.get("body"),
            "content_type": resolved.get("content_type"),
        },
        "parameter_schema": _resolved_parameter_schema(context, spec),
        "captured_support": captured,
        "suggested_filename_template": spec["suggested_filename"],
    }


def _resolve_selected_export(adapter: Any, context: AnalysisContext, spec: dict[str, Any], export_params: dict[str, Any]) -> dict[str, Any]:
    resolved = spec["build_request"](context, export_params)
    captured = _captured_method_summary(adapter, spec["captured_relative_path"], spec["method"])
    filename = _suggested_filename(spec["suggested_filename"], context, resolved)
    return {
        "export_key": spec["export_key"],
        "label": spec["label"],
        "category": spec["category"],
        "execution_mode": spec["execution_mode"],
        "parameter_schema": _resolved_parameter_schema(context, spec),
        "parameter_overrides": export_params,
        "resolved_request": {
            "method": spec["method"],
            "path": spec["path"],
            "query": resolved.get("query") or {},
            "body": resolved.get("body"),
            "content_type": resolved.get("content_type"),
            "required_headers": _captured_required_headers(captured),
        },
        "suggested_filename": filename,
        "captured_support": captured,
    }


def _selected_export_evidence(spec: dict[str, Any], selected_export: dict[str, Any]) -> Evidence:
    resolved_request = selected_export.get("resolved_request") or {}
    return Evidence(
        id=f"export_contract:{spec['export_key']}",
        source_api=spec["captured_relative_path"],
        source_path=spec["path"],
        source_method=spec["method"],
        request_signature={"export_key": spec["export_key"]},
        request_params={
            "query": resolved_request.get("query") or {},
            "body": resolved_request.get("body"),
        },
        response_excerpt={"execution_mode": spec["execution_mode"], "suggested_filename": selected_export.get("suggested_filename")},
    )


def _execute_selected_export(
    adapter: Any,
    spec: dict[str, Any],
    selected_export: dict[str, Any],
    *,
    include_file_content: bool,
    max_export_bytes: int,
    warnings: list[WarningMessage],
) -> dict[str, Any]:
    resolved_request = selected_export.get("resolved_request") or {}
    query = dict(resolved_request.get("query") or {})
    body = resolved_request.get("body")
    content_type = str(resolved_request.get("content_type") or "application/json")
    response = _raw_http_client(adapter)
    result = _execute_raw_request(
        response,
        method=str(resolved_request.get("method") or spec["method"]),
        path=str(resolved_request.get("path") or spec["path"]),
        query=query,
        body=body,
        content_type=content_type,
    )
    body_bytes = bytes(result.get("body_bytes") or b"")
    byte_size = len(body_bytes)
    mime_type = str(result.get("mime_type") or "")
    filename = _filename_from_headers(result.get("headers") or {}) or str(selected_export.get("suggested_filename") or "")

    execution = {
        "requested": True,
        "executed": True,
        "status": "executed",
        "status_code": result.get("status"),
        "mime_type": mime_type,
        "byte_size": byte_size,
        "suggested_filename": filename,
        "sha1": hashlib.sha1(body_bytes).hexdigest() if body_bytes else None,
        "headers": result.get("headers") or {},
        "content_included": False,
    }

    if "json" in mime_type:
        execution["response_json"] = _decode_json_bytes(body_bytes)
        return execution

    if include_file_content:
        if byte_size > max_export_bytes:
            warnings.append(
                WarningMessage(
                    code="export_content_omitted_by_size",
                    message=f"Export content size {byte_size} exceeds maxExportBytes={max_export_bytes}; content omitted but metadata retained.",
                    source_api=spec["captured_relative_path"],
                )
            )
            execution["status"] = "executed_content_omitted"
            execution["content_omitted_reason"] = "size_limit"
        else:
            execution["content_base64"] = base64.b64encode(body_bytes).decode("ascii")
            execution["content_included"] = True
    return execution


def _raw_http_client(adapter: Any) -> Any:
    for attr in ("application", "webaction", "database", "graph"):
        client = getattr(adapter, attr, None)
        if client is not None:
            return client
    raise RuntimeError("No HTTP client available for export execution.")


def _execute_raw_request(
    client: Any,
    *,
    method: str,
    path: str,
    query: dict[str, Any],
    body: Any,
    content_type: str,
) -> dict[str, Any]:
    upper_method = method.upper()
    if upper_method == "GET":
        return client.get_raw(path, query=query, content_type=content_type)
    if "application/x-www-form-urlencoded" in content_type:
        return client.post_form_raw(path, body or {}, query=query)
    return client.post_json_raw(path, body or {}, query=query)


def _find_export_spec(specs: list[dict[str, Any]], export_kind: Optional[str]) -> Optional[dict[str, Any]]:
    if not export_kind:
        return None
    for spec in specs:
        if spec["export_key"] == export_kind:
            return spec
    return None


def _captured_method_summary(adapter: Any, relative_path: str, method: str) -> dict[str, Any]:
    repo = getattr(adapter, "captured_api", None)
    if repo is None or not repo.exists():
        return {"captured": False}
    try:
        entry = repo.load_method_entry(relative_path, method)
    except Exception:
        return {"captured": False}
    return {
        "captured": True,
        "count_seen": entry.get("count_seen"),
        "mime_types": entry.get("mime_types") or {},
        "inferred_purpose": entry.get("inferred_purpose"),
        "inference_basis": entry.get("inference_basis") or [],
        "request_headers_template": entry.get("request_headers_template") or {},
        "query_variants": entry.get("query_variants") or [],
        "body_variants": entry.get("body_variants") or [],
        "replay": entry.get("replay") or {},
        "page_context_summary": entry.get("page_context_summary") or {},
        "sample_requests": (entry.get("sample_requests") or [])[:2],
        "sample_responses": (entry.get("sample_responses") or [])[:1],
    }


def _captured_required_headers(captured: dict[str, Any]) -> dict[str, Any]:
    if not captured.get("captured"):
        return {}
    return dict(captured.get("request_headers_template") or {})


def _resolved_parameter_schema(context: AnalysisContext, spec: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in spec.get("parameter_schema") or []:
        row = dict(item)
        if row.get("default_from_context") == "biz_system_id":
            row["resolved_default"] = context.biz_system_id
        elif row.get("default_from_context") == "end_time":
            row["resolved_default"] = context.time_window.end_time
        elif row.get("default_from_context") == "period_minutes":
            row["resolved_default"] = context.time_window.period_minutes
        elif row.get("default_from_context") == "lang":
            row["resolved_default"] = context.lang
        else:
            row["resolved_default"] = row.get("default")
        rows.append(row)
    return rows


def _build_action_list_export_request(context: AnalysisContext, export_params: dict[str, Any]) -> dict[str, Any]:
    query = {
        "timePeriod": _param_value(context, export_params, "timePeriod", context.time_window.period_minutes),
        "endTime": _param_value(context, export_params, "endTime", context.time_window.end_time),
        "bizSystemId": _param_value(context, export_params, "bizSystemId", context.biz_system_id),
        "sortField": _param_value(context, export_params, "sortField", "response"),
        "sortDirection": _param_value(context, export_params, "sortDirection", "DESC"),
        "actionName": _param_value(context, export_params, "actionName", ""),
        "applicationId": _param_value(context, export_params, "applicationId", 0),
        "favorites": _bool_to_string(_param_value(context, export_params, "favorites", False)),
        "downloadFile": _bool_to_string(_param_value(context, export_params, "downloadFile", True)),
    }
    return {"query": query, "body": None, "content_type": "application/json"}


def _build_interface_list_export_request(context: AnalysisContext, export_params: dict[str, Any]) -> dict[str, Any]:
    query = {
        "timePeriod": _param_value(context, export_params, "timePeriod", context.time_window.period_minutes),
        "endTime": _param_value(context, export_params, "endTime", context.time_window.end_time),
        "bizSystemId": _param_value(context, export_params, "bizSystemId", context.biz_system_id),
        "sortField": _param_value(context, export_params, "sortField", "response"),
        "sortDirection": _param_value(context, export_params, "sortDirection", "DESC"),
        "actionName": _param_value(context, export_params, "actionName", ""),
        "applicationId": _param_value(context, export_params, "applicationId", 0),
        "downloadFile": _bool_to_string(_param_value(context, export_params, "downloadFile", True)),
    }
    return {"query": query, "body": None, "content_type": "application/json"}


def _build_component_analysis_export_request(context: AnalysisContext, export_params: dict[str, Any]) -> dict[str, Any]:
    query = {
        "componentType": _param_value(context, export_params, "componentType", "Database"),
        "bizSystemId": _param_value(context, export_params, "bizSystemId", context.biz_system_id),
        "endTime": _param_value(context, export_params, "endTime", context.time_window.end_time),
        "timePeriod": _param_value(context, export_params, "timePeriod", context.time_window.period_minutes),
        "dataType": _param_value(context, export_params, "dataType", "OP"),
        "componentName": _param_value(context, export_params, "componentName", ""),
        "componentSubtype": _param_value(context, export_params, "componentSubtype", ""),
        "pageSize": _param_value(context, export_params, "pageSize", 10000),
        "pageNumber": _param_value(context, export_params, "pageNumber", 1),
        "limit": _bool_to_string(_param_value(context, export_params, "limit", True)),
        "sortField": _param_value(context, export_params, "sortField", "respTime"),
        "sortDirection": _param_value(context, export_params, "sortDirection", "DESC"),
    }
    return {"query": query, "body": None, "content_type": "application/json"}


def _build_graph_overview_export_request(context: AnalysisContext, export_params: dict[str, Any]) -> dict[str, Any]:
    metric = str(_param_value(context, export_params, "metric", "request_overview"))
    labels = export_params.get("labels")
    if not isinstance(labels, dict):
        if metric == "application_overview":
            labels = {"systemIds": [str(context.biz_system_id)]}
        else:
            labels = {"actionTypes": ["TX,IF"], "systemIds": [str(context.biz_system_id)]}
    body = {
        "endTime": _param_value(context, export_params, "endTime", context.time_window.end_time),
        "labels": labels,
        "metric": metric,
        "timePeriod": _param_value(context, export_params, "timePeriod", context.time_window.period_minutes),
    }
    if "zoomTime" in export_params or metric == "application_overview":
        body["zoomTime"] = bool(_param_value(context, export_params, "zoomTime", True))
    return {"query": {metric: ""}, "body": body, "content_type": "application/json"}


def _build_error_export_list_request(context: AnalysisContext, export_params: dict[str, Any]) -> dict[str, Any]:
    body = {"lang": _param_value(context, export_params, "lang", context.lang)}
    return {"query": {}, "body": body, "content_type": "application/x-www-form-urlencoded"}


def _build_error_export_create_task_request(context: AnalysisContext, export_params: dict[str, Any]) -> dict[str, Any]:
    begin_time = _param_value(context, export_params, "beginTime", _begin_time_from_context(context))
    body = {
        "beginTime": begin_time,
        "bizSystemId": _param_value(context, export_params, "bizSystemId", context.biz_system_id),
        "bizSystemName": _param_value(context, export_params, "bizSystemName", ""),
        "endTime": _param_value(context, export_params, "endTime", context.time_window.end_time),
        "errorLevel": _param_value(context, export_params, "errorLevel", "ER"),
        "exportColumns": _param_value(context, export_params, "exportColumns", "1,2,3,4,5,13,6,7,8,10"),
        "filterParams": _param_value(context, export_params, "filterParams", []),
        "localeOptionContent": _param_value(context, export_params, "localeOptionContent", "Custom"),
        "serviceGroupId": _param_value(context, export_params, "serviceGroupId", 0),
        "timePeriod": _param_value(context, export_params, "timePeriod", context.time_window.period_minutes),
    }
    return {"query": {}, "body": body, "content_type": "application/json"}


def _param_value(context: AnalysisContext, export_params: dict[str, Any], name: str, default: Any) -> Any:
    if name in export_params:
        return export_params[name]
    return default


def _bool_to_string(value: Any) -> str:
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes", "on"}:
            return "true"
        if lowered in {"false", "0", "no", "off"}:
            return "false"
    return "true" if bool(value) else "false"


def _begin_time_from_context(context: AnalysisContext) -> str:
    # Keep format aligned with Tingyun request patterns using minute precision.
    try:
        end_time = context.time_window.end_time
        if len(end_time) >= 16:
            return end_time
    except Exception:
        pass
    return context.time_window.end_time


def _suggested_filename(template: str, context: AnalysisContext, resolved: dict[str, Any]) -> str:
    query = resolved.get("query") or {}
    body = resolved.get("body") or {}
    metric = str(body.get("metric") or "")
    component_type = str(query.get("componentType") or "")
    component_subtype = str(query.get("componentSubtype") or "")
    end_time_safe = re.sub(r"[^0-9A-Za-z]+", "_", str(context.time_window.end_time)).strip("_")
    return (
        template.replace("{biz_system_id}", str(context.biz_system_id))
        .replace("{end_time_safe}", end_time_safe)
        .replace("{metric}", metric or "export")
        .replace("{component_type}", component_type or "component")
        .replace("{component_subtype}", component_subtype or "subtype")
    )


def _filename_from_headers(headers: dict[str, Any]) -> Optional[str]:
    for key, value in headers.items():
        if str(key).lower() != "content-disposition":
            continue
        text = str(value)
        match = re.search(r"filename\\*=UTF-8''([^;]+)", text, re.IGNORECASE)
        if match:
            return unquote(match.group(1))
        match = re.search(r'filename="?([^\";]+)"?', text, re.IGNORECASE)
        if match:
            return match.group(1)
    return None


def _decode_json_bytes(body_bytes: bytes) -> Any:
    if not body_bytes:
        return None
    text = body_bytes.decode("utf-8", errors="replace")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"raw_text": text}
