from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from typing import Any

from tingyun_adapter.usecases.analysis_rules import BACKGROUND_KEYWORDS, CORE_BUSINESS_KEYWORDS, SUPPORT_KEYWORDS


ISSUE_PRIORITY_ORDER = {
    "P0": 0,
    "P1": 1,
    "P2": 2,
    "P3": 3,
    "observation": 4,
}


def sql_fingerprint(sql_text: str) -> str:
    normalized = _normalize_sql_text(sql_text)
    if not normalized:
        return "sql:empty"
    digest = hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:16]
    return f"sql:{digest}"


def extract_sql_feature_tags(sql_text: str) -> list[str]:
    text = (sql_text or "").strip()
    upper = text.upper()
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
    return tags


def rank_issue_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    ranked = dict(candidate)
    occurrence_count = _safe_int(ranked.get("occurrence_count"))
    active_days = _safe_int(ranked.get("active_days")) or (1 if occurrence_count else 0)
    active_windows = _safe_int(ranked.get("active_windows")) or (1 if occurrence_count else 0)
    affected_requests = _safe_int(ranked.get("affected_requests"))
    affected_traces = _safe_int(ranked.get("affected_traces"))
    affected_objects = _safe_int(ranked.get("affected_objects")) or 1
    severity_level = str(ranked.get("severity_level") or _infer_severity_level(ranked))
    evidence_strength = str(ranked.get("evidence_strength") or _infer_evidence_strength(ranked))
    business_criticality = str(ranked.get("business_criticality") or _infer_business_criticality(ranked))
    critical_path = bool(ranked.get("critical_path"))
    fatal = bool(ranked.get("fatal"))
    failure_rate = _safe_float(ranked.get("failure_rate"))

    matched_dimensions: list[str] = []
    if occurrence_count >= 3 or active_windows >= 2:
        matched_dimensions.append("高频或跨时间窗出现")
    if affected_requests >= 100 or affected_traces >= 3 or affected_objects >= 3:
        matched_dimensions.append("影响范围较大")
    if business_criticality == "high":
        matched_dimensions.append("命中核心业务链路")
    if evidence_strength == "strong":
        matched_dimensions.append("trace / SQL /错误证据较强")
    if active_days >= 2 or active_windows >= 2:
        matched_dimensions.append("具备一定复现性")
    if critical_path:
        matched_dimensions.append("属于主链路对象")

    auto_downgraded = (
        occurrence_count <= 1
        and active_windows <= 1
        and affected_objects <= 1
        and affected_traces <= 1
        and business_criticality != "high"
        and evidence_strength != "strong"
        and not critical_path
        and not fatal
    )
    exceptional_upgrade = fatal or (critical_path and failure_rate >= 0.99 and evidence_strength in {"medium", "strong"})

    if exceptional_upgrade:
        report_priority = "P0" if severity_level == "critical" else "P1"
    elif auto_downgraded:
        report_priority = "observation"
    elif len(matched_dimensions) >= 4 and severity_level in {"critical", "high"}:
        report_priority = "P0" if severity_level == "critical" else "P1"
    elif len(matched_dimensions) >= 3:
        report_priority = "P1" if severity_level in {"critical", "high"} else "P2"
    elif len(matched_dimensions) >= 2:
        report_priority = "P2"
    elif severity_level in {"critical", "high"}:
        report_priority = "P3"
    else:
        report_priority = "observation"

    selection_reason = ranked.get("selection_reason")
    downgrade_reason = ranked.get("downgrade_reason")
    if report_priority == "observation":
        downgrade_reason = downgrade_reason or "低频、影响范围小或证据闭环不足，先进入观察项。"
        selection_reason = selection_reason or ""
    else:
        selection_reason = selection_reason or "；".join(matched_dimensions[:3]) or "具备进入正文主问题的综合条件。"
        downgrade_reason = downgrade_reason or ""

    ranked.update(
        {
            "canonical_issue_key": str(ranked.get("canonical_issue_key") or _default_issue_key(ranked)),
            "issue_type": str(ranked.get("issue_type") or "generic_issue"),
            "severity_level": severity_level,
            "report_priority": report_priority,
            "occurrence_count": occurrence_count,
            "active_days": active_days,
            "active_windows": active_windows,
            "affected_requests": affected_requests,
            "affected_traces": affected_traces,
            "affected_objects": affected_objects,
            "evidence_strength": evidence_strength,
            "business_criticality": business_criticality,
            "selection_reason": selection_reason,
            "downgrade_reason": downgrade_reason,
            "primary_section": str(ranked.get("primary_section") or _default_primary_section(ranked)),
            "duplicate_of": ranked.get("duplicate_of"),
            "evidence_role": str(ranked.get("evidence_role") or "primary"),
            "priority": ranked.get("priority") or report_priority.lower(),
            "title": ranked.get("title") or _default_issue_title(ranked),
            "summary": ranked.get("summary") or ranked.get("title") or _default_issue_title(ranked),
            "details": ranked.get("details") or {},
        }
    )
    return ranked


def dedupe_issue_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ranked = [rank_issue_candidate(candidate) for candidate in candidates]
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for candidate in ranked:
        grouped[str(candidate.get("canonical_issue_key") or _default_issue_key(candidate))].append(candidate)

    deduped: list[dict[str, Any]] = []
    for canonical_key, items in grouped.items():
        ordered = sorted(items, key=_issue_sort_key)
        primary = dict(ordered[0])
        primary["canonical_issue_key"] = canonical_key
        primary["duplicate_of"] = None
        primary["evidence_role"] = "primary"
        deduped.append(primary)
        for duplicate in ordered[1:]:
            duplicate_item = dict(duplicate)
            duplicate_item["canonical_issue_key"] = canonical_key
            duplicate_item["duplicate_of"] = canonical_key
            duplicate_item["report_priority"] = primary.get("report_priority")
            duplicate_item["evidence_role"] = "supporting"
            deduped.append(duplicate_item)
    return sorted(deduped, key=_issue_sort_key)


def split_ranked_issues(candidates: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    deduped = dedupe_issue_candidates(candidates)
    issues = [item for item in deduped if item.get("duplicate_of") is None and item.get("report_priority") != "observation"]
    observations = [item for item in deduped if item.get("duplicate_of") is None and item.get("report_priority") == "observation"]
    return issues, observations, deduped


def union_sql_candidates(
    rows: list[dict[str, Any]],
    *,
    trace_case: dict[str, Any] | None = None,
    sql_fact_payloads: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    sql_fact_payloads = sql_fact_payloads or {}
    if not rows:
        return {
            "sql_candidates": [],
            "sql_main_candidates": [],
            "sql_opportunities": [],
        }

    by_avg = sorted(rows, key=lambda item: _safe_float(item.get("response_time_ms")), reverse=True)
    by_total = sorted(rows, key=lambda item: _safe_float(item.get("total_response_time_ms") or item.get("totalResptime")), reverse=True)
    by_trace = sorted(rows, key=lambda item: _safe_float(item.get("traceCount")), reverse=True)
    avg_rank = {id(item): index for index, item in enumerate(by_avg, start=1)}
    total_rank = {id(item): index for index, item in enumerate(by_total, start=1)}
    trace_rank = {id(item): index for index, item in enumerate(by_trace, start=1)}

    trace_info = (trace_case or {}).get("trace") or {}
    trace_id = trace_info.get("trace_id_numeric")
    trace_action_id = trace_info.get("action_id")

    candidates: list[dict[str, Any]] = []
    for row in rows:
        sql_text = str(row.get("op_name_decoded") or row.get("opName") or "")
        fingerprint = sql_fingerprint(sql_text)
        feature_tags = list(row.get("sql_features", {}).get("tags") or extract_sql_feature_tags(sql_text))
        fact_payload = sql_fact_payloads.get(fingerprint) or {}
        related_actions = fact_payload.get("related_actions") or []
        related_traces = fact_payload.get("related_traces") or []
        candidate_sources = {"global_top"}
        if trace_rank.get(id(row), 999) <= 5 or _sql_matches_trace_action(related_actions, trace_action_id):
            candidate_sources.add("trace_bound")
        if feature_tags or (_safe_float(row.get("count")) >= 20 and _safe_float(row.get("total_response_time_ms")) >= 3000):
            candidate_sources.add("optimization")

        trace_case_ids: list[str] = []
        if trace_id and ("trace_bound" in candidate_sources or _sql_matches_trace_action(related_actions, trace_action_id)):
            trace_case_ids.append(str(trace_id))
        trace_binding_strength = _trace_binding_strength(row, related_actions, related_traces, trace_case_ids)
        recommendation = _sql_report_recommendation(row, candidate_sources, trace_binding_strength)
        candidate = {
            "sql_fingerprint": fingerprint,
            "sql_text": sql_text,
            "component_name": row.get("component_name") or row.get("componentName"),
            "component_subtype": row.get("component_subtype") or row.get("componentSubtype"),
            "candidate_source": sorted(candidate_sources),
            "rank_by_avg": avg_rank.get(id(row)),
            "rank_by_total": total_rank.get(id(row)),
            "rank_by_trace": trace_rank.get(id(row)),
            "trace_binding_strength": trace_binding_strength,
            "caller_objects": _caller_objects(related_actions, row),
            "impact_objects": _impact_objects(related_actions, row),
            "sql_feature_tags": feature_tags,
            "optimization_hypothesis": _optimization_hypothesis(feature_tags, row),
            "report_recommendation": recommendation,
            "trace_case_ids": trace_case_ids,
            "trace_case_count": len(trace_case_ids),
            "trace_positions": ["critical_path"] if trace_case_ids else [],
            "metrics": {
                "response_time_ms": _safe_float(row.get("response_time_ms")),
                "total_response_time_ms": _safe_float(row.get("total_response_time_ms") or row.get("totalResptime")),
                "count": _safe_int(row.get("count")),
                "trace_count": _safe_int(row.get("traceCount")),
                "error_count": _safe_int(row.get("error_count") or row.get("errorCount")),
            },
            "details": row,
        }
        candidates.append(candidate)

    deduped = _dedupe_sql_candidates(candidates)
    main_candidates = [item for item in deduped if item.get("report_recommendation") == "main_issue"]
    opportunities = [item for item in deduped if "optimization" in (item.get("candidate_source") or []) and item.get("report_recommendation") != "main_issue"]
    return {
        "sql_candidates": deduped,
        "sql_main_candidates": main_candidates,
        "sql_opportunities": opportunities,
    }


def build_issue_inventory(
    *,
    summary: dict[str, Any],
    snapshot_payload: dict[str, Any],
    hotspot_payload: dict[str, Any],
    trace_payload: dict[str, Any],
    sql_main_candidates: list[dict[str, Any]],
    sql_opportunities: list[dict[str, Any]],
) -> dict[str, Any]:
    candidates: list[dict[str, Any]] = []
    action_health = (snapshot_payload.get("health") or {}).get("action") or {}
    if _safe_int(action_health.get("warn")) > 0:
        candidates.append(
            {
                "issue_type": "system_health_warning",
                "canonical_issue_key": f"health:action:{_safe_int(action_health.get('warn'))}",
                "title": "业务系统存在告警级 Action 健康对象",
                "summary": "业务系统健康统计中存在告警对象，需要纳入正文检查。",
                "priority": "high",
                "category": "health",
                "evidence_ref": "health_level_statistics",
                "severity_level": "high",
                "occurrence_count": _safe_int(action_health.get("warn")),
                "active_days": 1,
                "active_windows": 1,
                "affected_objects": _safe_int(action_health.get("warn")),
                "evidence_strength": "strong",
                "business_criticality": "medium",
                "primary_section": "3.1 业务系统总体检查",
                "details": action_health,
            }
        )

    for hotspot in (hotspot_payload.get("hotspots") or [])[:8]:
        action = hotspot.get("action") or {}
        metrics = action.get("metrics") or {}
        response_time = _safe_float(metrics.get("response_time_ms"))
        error_count = _safe_int(metrics.get("error_count"))
        slow_count = _safe_int(metrics.get("slow_count"))
        count = _safe_int(metrics.get("count"))
        if response_time < 500 and error_count <= 0 and slow_count <= 0:
            continue
        issue_type = "action_error" if error_count > 0 else "action_latency"
        candidates.append(
            {
                "issue_type": issue_type,
                "canonical_issue_key": f"action:{issue_type}:{action.get('id')}",
                "title": f"接口 {action.get('name') or action.get('id')} 指标异常",
                "summary": f"接口 {action.get('name') or action.get('id')} 在当前时间窗内响应或慢请求表现异常。",
                "priority": "high" if response_time >= 1000 or error_count > 0 else "medium",
                "category": "hotspot",
                "evidence_ref": "action_list",
                "severity_level": "critical" if error_count > 0 and count > 0 and error_count >= max(1, count // 2) else ("high" if response_time >= 1000 else "medium"),
                "occurrence_count": max(slow_count, error_count, 1),
                "active_days": 1,
                "active_windows": 2 if slow_count >= 5 or error_count > 0 else 1,
                "affected_requests": count,
                "affected_traces": slow_count,
                "affected_objects": len((hotspot.get("overview") or {}).get("components", {}) or {}) or 1,
                "evidence_strength": "strong" if hotspot.get("overview") else "medium",
                "business_criticality": _criticality_from_name(action.get("name") or action.get("alias")),
                "critical_path": _criticality_from_name(action.get("name") or action.get("alias")) == "high",
                "failure_rate": error_count / count if count else 0.0,
                "fatal": bool(error_count and count and error_count >= count),
                "primary_section": "3.3 事务与服务接口检查",
                "details": hotspot,
            }
        )

    trace_case = trace_payload.get("trace_case") or {}
    trace_info = trace_case.get("trace") or {}
    suspected = trace_info.get("suspected_problems") or []
    trace_duration = _safe_float(trace_info.get("duration_ms"))
    if suspected or trace_duration >= 1000:
        candidates.append(
            {
                "issue_type": "trace_bottleneck",
                "canonical_issue_key": f"trace:{trace_info.get('trace_id_numeric') or trace_info.get('trace_guid')}",
                "title": "代表性 Trace 存在明显瓶颈段",
                "summary": "代表性 trace 已出现可疑节点，可作为根因分析正文样本。",
                "priority": "high",
                "category": "trace",
                "evidence_ref": "trace_detail",
                "severity_level": "high" if trace_duration >= 1000 else "medium",
                "occurrence_count": max(len(suspected), 1),
                "active_days": 1,
                "active_windows": 1,
                "affected_requests": 1,
                "affected_traces": 1,
                "affected_objects": len({item.get("metricName") for item in suspected if item.get("metricName")}),
                "evidence_strength": "strong" if suspected else "medium",
                "business_criticality": _criticality_from_name(trace_case.get("detail_summary", {}).get("actionName")),
                "critical_path": _criticality_from_name(trace_case.get("detail_summary", {}).get("actionName")) == "high",
                "primary_section": "3.5 请求追踪与根因分析专题",
                "details": trace_case,
            }
        )

    for sql_candidate in sql_main_candidates + sql_opportunities[:10]:
        metrics = sql_candidate.get("metrics") or {}
        candidates.append(
            {
                "issue_type": "sql_latency",
                "canonical_issue_key": f"sql:{sql_candidate.get('sql_fingerprint')}",
                "title": f"SQL 候选 {sql_candidate.get('sql_fingerprint')} 需要重点关注",
                "summary": "SQL 候选同时具备慢 SQL、trace 绑定或优化价值，需要在 SQL 章节明确归类。",
                "priority": "high" if sql_candidate in sql_main_candidates else "medium",
                "category": "sql",
                "evidence_ref": "slow_sql_analysis",
                "severity_level": "high" if _safe_float(metrics.get("response_time_ms")) >= 1000 else "medium",
                "occurrence_count": _safe_int(metrics.get("count")) or 1,
                "active_days": 1,
                "active_windows": 2 if sql_candidate.get("trace_binding_strength") in {"strong", "medium"} else 1,
                "affected_requests": _safe_int(metrics.get("count")),
                "affected_traces": _safe_int(metrics.get("trace_count")) or _safe_int(sql_candidate.get("trace_case_count")),
                "affected_objects": len(sql_candidate.get("impact_objects") or []) or 1,
                "evidence_strength": "strong" if sql_candidate.get("trace_binding_strength") == "strong" else "medium",
                "business_criticality": "high" if len(sql_candidate.get("impact_objects") or []) >= 2 else "medium",
                "selection_reason": "SQL 已进入全局慢 SQL 候选池，并且具备 trace / 调用者支撑。" if sql_candidate in sql_main_candidates else "",
                "downgrade_reason": "当前更适合作为 SQL 优化储备而不是正文主问题。" if sql_candidate not in sql_main_candidates else "",
                "primary_section": "3.4 SQL 检查",
                "details": sql_candidate,
            }
        )

    issues, observations, issue_candidates = split_ranked_issues(candidates)
    return {
        "issues": issues,
        "observations": observations,
        "issue_candidates": issue_candidates,
        "legacy_issues": [_legacy_issue_row(item) for item in issues],
    }


def build_template_mapping(
    *,
    issues: list[dict[str, Any]],
    observations: list[dict[str, Any]],
    sql_main_candidates: list[dict[str, Any]],
    sql_opportunities: list[dict[str, Any]],
    page_boundary: dict[str, Any],
) -> dict[str, Any]:
    sections = [
        {
            "section_id": "overview",
            "section_title": "本次巡检范围与总体判断",
            "source_paths": ["report_scope", "summary", "coverage_boundary"],
            "writer_guidance": "先交代范围、时间窗和能力边界，再给出总体判断。",
        },
        {
            "section_id": "issues",
            "section_title": "重点问题清单",
            "source_paths": ["issues", "issue_candidates"],
            "writer_guidance": "正文主问题优先使用 P0/P1，再补 P2 的影响说明。",
        },
        {
            "section_id": "sql",
            "section_title": "SQL 检查与优化建议",
            "source_paths": ["sql_main_candidates", "sql_opportunities"],
            "writer_guidance": "先写数据库整体结论，再写重点 SQL，最后列优化储备。",
        },
        {
            "section_id": "trace",
            "section_title": "请求追踪与根因样本",
            "source_paths": ["trace_case"],
            "writer_guidance": "使用代表性 trace 说明瓶颈链路，明确证据边界。",
        },
        {
            "section_id": "page_boundary",
            "section_title": "页面能力边界与截图索引",
            "source_paths": ["coverage_boundary", "screenshot_index_summary"],
            "writer_guidance": "缺少页面侧专用输入时，明确写能力边界，不要虚构页面问题。",
        },
    ]
    return {
        "sections": sections,
        "counts": {
            "issue_count": len(issues),
            "observation_count": len(observations),
            "sql_main_count": len(sql_main_candidates),
            "sql_opportunity_count": len(sql_opportunities),
        },
        "page_boundary_status": ((page_boundary or {}).get("page_experience") or {}).get("status"),
    }


def build_writer_input(
    *,
    report_scope: dict[str, Any],
    summary: dict[str, Any],
    coverage_boundary: dict[str, Any],
    issues: list[dict[str, Any]],
    observations: list[dict[str, Any]],
    sql_main_candidates: list[dict[str, Any]],
    sql_opportunities: list[dict[str, Any]],
    trace_case: dict[str, Any],
    page_payload: dict[str, Any],
    screenshot_index_summary: dict[str, Any],
    template_mapping: dict[str, Any],
) -> dict[str, Any]:
    capability_boundary = coverage_boundary or {}
    manual_review_items = _manual_review_items(capability_boundary, issues, sql_main_candidates, page_payload)
    section_evidence_map = {
        "overview": ["system_snapshot.overview", "system_snapshot.health", "report_fact_pack.summary"],
        "issues": ["report_fact_pack.issues", "report_fact_pack.issue_candidates"],
        "sql": ["report_fact_pack.sql_main_candidates", "report_fact_pack.sql_opportunities"],
        "trace": ["trace_case_pack.trace_case"],
        "page": ["page_experience_pack.pages", "coverage_boundary", "screenshot_index_summary"],
    }
    executive_summary = {
        "overall_assessment": _overall_assessment(issues, sql_main_candidates, capability_boundary),
        "top_issue_count": len(issues),
        "observation_count": len(observations),
        "sql_focus_count": len(sql_main_candidates),
    }
    return {
        "scope": report_scope,
        "capability_boundary": capability_boundary,
        "executive_summary": executive_summary,
        "top_issues": issues,
        "observations": observations,
        "sql_main_candidates": sql_main_candidates,
        "sql_opportunities": sql_opportunities,
        "trace_cases": [trace_case] if trace_case else [],
        "page_boundary": {
            "coverage_boundary": (page_payload or {}).get("coverage_boundary") or capability_boundary,
            "pages": (page_payload or {}).get("pages") or [],
            "related_actions": (page_payload or {}).get("related_actions") or [],
        },
        "screenshot_index_summary": screenshot_index_summary,
        "section_evidence_map": section_evidence_map,
        "template_mapping": template_mapping,
        "manual_review_items": manual_review_items,
        "summary": summary,
    }


def render_writer_input_markdown(writer_input: dict[str, Any]) -> str:
    lines = [
        "# Report Writer Input",
        "",
        "## 本次巡检范围",
        f"- 业务系统: {((writer_input.get('scope') or {}).get('bizSystemId'))}",
        f"- 时间窗: {((writer_input.get('scope') or {}).get('endTime'))}",
        f"- 分析周期: {((writer_input.get('scope') or {}).get('periodMinutes'))} 分钟",
        "",
        "## 能力边界",
        f"- 页面体验状态: {(((writer_input.get('capability_boundary') or {}).get('page_experience') or {}).get('status') or 'unknown')}",
        f"- 页面体验边界说明: {(((writer_input.get('capability_boundary') or {}).get('page_experience') or {}).get('reason') or '未提供')}",
        "",
        "## 总体判断",
        f"- 结论: {((writer_input.get('executive_summary') or {}).get('overall_assessment') or '待补充')}",
        f"- 主问题数: {((writer_input.get('executive_summary') or {}).get('top_issue_count') or 0)}",
        f"- 观察项数: {((writer_input.get('executive_summary') or {}).get('observation_count') or 0)}",
        f"- SQL 重点对象数: {((writer_input.get('executive_summary') or {}).get('sql_focus_count') or 0)}",
        "",
        "## 重点问题清单摘要",
    ]
    lines.extend(_render_issue_markdown(writer_input.get("top_issues") or [], fallback="- 当前没有进入正文主问题的对象。"))
    lines.extend(
        [
            "",
            "## 观察项摘要",
        ]
    )
    lines.extend(_render_issue_markdown(writer_input.get("observations") or [], fallback="- 当前没有观察项。"))
    lines.extend(
        [
            "",
            "## SQL 主问题摘要",
        ]
    )
    lines.extend(_render_sql_markdown(writer_input.get("sql_main_candidates") or [], fallback="- 当前没有进入主问题的 SQL。"))
    lines.extend(
        [
            "",
            "## SQL 优化储备摘要",
        ]
    )
    lines.extend(_render_sql_markdown(writer_input.get("sql_opportunities") or [], fallback="- 当前没有 SQL 优化储备。"))
    lines.extend(
        [
            "",
            "## Trace 典型样本摘要",
        ]
    )
    trace_cases = writer_input.get("trace_cases") or []
    if trace_cases:
        trace = trace_cases[0]
        trace_detail = trace.get("detail_summary") or {}
        trace_trace = trace.get("trace") or {}
        lines.extend(
            [
                f"- Trace 样本: {trace_trace.get('trace_id_numeric') or trace_trace.get('trace_guid')}",
                f"- 关联接口: {trace_detail.get('actionName') or trace_trace.get('action_id')}",
                f"- 持续时间: {trace_trace.get('duration_ms')}",
                f"- 绑定 SQL 数: {len(trace.get('key_sqls') or [])}",
            ]
        )
    else:
        lines.append("- 当前没有可写入的 trace 样本。")
    lines.extend(
        [
            "",
            "## 页面能力边界与截图摘要",
            f"- 页面对象数: {len((writer_input.get('page_boundary') or {}).get('pages') or [])}",
            f"- 截图候选数: {((writer_input.get('screenshot_index_summary') or {}).get('card_count') or 0)}",
            "",
            "## 待人工定稿项",
        ]
    )
    manual_items = writer_input.get("manual_review_items") or []
    if manual_items:
        for item in manual_items:
            lines.append(f"- {item}")
    else:
        lines.append("- 当前没有额外的人工定稿提醒。")
    return "\n".join(lines).strip() + "\n"


def render_template_outline_markdown(template_mapping: dict[str, Any]) -> str:
    lines = [
        "# Template Outline Mapping",
        "",
        "## 章节映射",
    ]
    for section in template_mapping.get("sections") or []:
        lines.extend(
            [
                f"### {section.get('section_title')}",
                f"- section_id: {section.get('section_id')}",
                f"- source_paths: {', '.join(section.get('source_paths') or [])}",
                f"- writer_guidance: {section.get('writer_guidance')}",
                "",
            ]
        )
    return "\n".join(lines).strip() + "\n"


def render_sql_section_markdown(
    *,
    summary: dict[str, Any],
    slow_sql_overview: dict[str, Any],
    sql_main_candidates: list[dict[str, Any]],
    sql_opportunities: list[dict[str, Any]],
) -> str:
    lines = [
        "# SQL 检查",
        "",
        "## 组件层",
        f"- 平均响应时间: {summary.get('avg_response_time_ms')}",
        f"- 调用吞吐: {summary.get('avg_throughput')}",
        f"- SQL 候选数: {slow_sql_overview.get('sql_count')}",
        f"- 组件数: {slow_sql_overview.get('component_count')}",
        f"- 高 trace SQL 数: {slow_sql_overview.get('high_trace_sql_count')}",
        "",
        "## 平均耗时 / 总耗时 / trace 绑定重点 SQL",
    ]
    lines.extend(_render_sql_markdown(sql_main_candidates, fallback="- 当前没有进入重点 SQL 清单的对象。"))
    lines.extend(
        [
            "",
            "## 优化机会 SQL",
        ]
    )
    lines.extend(_render_sql_markdown(sql_opportunities, fallback="- 当前没有 SQL 优化储备。"))
    return "\n".join(lines).strip() + "\n"


def build_report_pack_exports(
    *,
    issues: list[dict[str, Any]],
    observations: list[dict[str, Any]],
    issue_candidates: list[dict[str, Any]],
    sql_candidates: list[dict[str, Any]],
    sql_opportunities: list[dict[str, Any]],
    writer_input: dict[str, Any],
    writer_markdown: str,
    template_outline_markdown: str,
    sql_section_markdown: str,
    screenshot_index_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "03_issues/issues.csv": _csv_export(issues, ISSUE_EXPORT_COLUMNS),
        "03_issues/observations.csv": _csv_export(observations, ISSUE_EXPORT_COLUMNS),
        "03_issues/sql_opportunities.csv": _csv_export(sql_opportunities, SQL_EXPORT_COLUMNS),
        "01_foundation/screenshot_index.csv": _csv_export(screenshot_index_rows, SCREENSHOT_EXPORT_COLUMNS),
        "04_raw/issue_candidates.json": {"format": "json", "data": issue_candidates},
        "04_raw/sql_candidates.json": {"format": "json", "data": sql_candidates},
        "00_internal/report_writer_input.json": {"format": "json", "data": writer_input},
        "00_internal/report_writer_input.md": {"format": "markdown", "content": writer_markdown},
        "00_internal/template_outline.md": {"format": "markdown", "content": template_outline_markdown},
        "02_sections/sql.md": {"format": "markdown", "content": sql_section_markdown},
    }


ISSUE_EXPORT_COLUMNS = [
    "title",
    "summary",
    "category",
    "priority",
    "evidence_ref",
    "canonical_issue_key",
    "issue_type",
    "severity_level",
    "report_priority",
    "occurrence_count",
    "active_days",
    "active_windows",
    "affected_requests",
    "affected_traces",
    "affected_objects",
    "evidence_strength",
    "business_criticality",
    "selection_reason",
    "downgrade_reason",
    "primary_section",
    "duplicate_of",
    "evidence_role",
]

SQL_EXPORT_COLUMNS = [
    "sql_fingerprint",
    "component_name",
    "component_subtype",
    "candidate_source",
    "rank_by_avg",
    "rank_by_total",
    "rank_by_trace",
    "trace_binding_strength",
    "caller_objects",
    "impact_objects",
    "sql_feature_tags",
    "optimization_hypothesis",
    "report_recommendation",
    "trace_case_ids",
    "trace_case_count",
    "trace_positions",
]

SCREENSHOT_EXPORT_COLUMNS = [
    "figure_id",
    "title",
    "page_type",
    "suggested_report_section",
    "priority",
    "url_status",
    "writer_summary",
]


def _csv_export(rows: list[dict[str, Any]], columns: list[str]) -> dict[str, Any]:
    exported_rows: list[dict[str, Any]] = []
    for row in rows:
        exported_rows.append({column: _csv_value(row.get(column)) for column in columns})
    return {
        "format": "csv",
        "columns": columns,
        "rows": exported_rows,
    }


def _csv_value(value: Any) -> Any:
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return value


def _dedupe_sql_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for candidate in candidates:
        fingerprint = str(candidate.get("sql_fingerprint") or "sql:empty")
        current = grouped.get(fingerprint)
        if current is None:
            grouped[fingerprint] = dict(candidate)
            continue
        current["candidate_source"] = sorted(set((current.get("candidate_source") or []) + (candidate.get("candidate_source") or [])))
        current["sql_feature_tags"] = sorted(set((current.get("sql_feature_tags") or []) + (candidate.get("sql_feature_tags") or [])))
        current["trace_case_ids"] = sorted(set((current.get("trace_case_ids") or []) + (candidate.get("trace_case_ids") or [])))
        current["trace_case_count"] = len(current["trace_case_ids"])
        current["caller_objects"] = _merge_named_objects(current.get("caller_objects") or [], candidate.get("caller_objects") or [])
        current["impact_objects"] = _merge_named_objects(current.get("impact_objects") or [], candidate.get("impact_objects") or [])
        current["rank_by_avg"] = min(_safe_int(current.get("rank_by_avg")) or 9999, _safe_int(candidate.get("rank_by_avg")) or 9999)
        current["rank_by_total"] = min(_safe_int(current.get("rank_by_total")) or 9999, _safe_int(candidate.get("rank_by_total")) or 9999)
        current["rank_by_trace"] = min(_safe_int(current.get("rank_by_trace")) or 9999, _safe_int(candidate.get("rank_by_trace")) or 9999)
        current["report_recommendation"] = _better_sql_recommendation(current.get("report_recommendation"), candidate.get("report_recommendation"))
        current["trace_binding_strength"] = _better_trace_strength(current.get("trace_binding_strength"), candidate.get("trace_binding_strength"))
    return sorted(grouped.values(), key=_sql_sort_key)


def _issue_sort_key(item: dict[str, Any]) -> tuple[int, int, int, int, str]:
    return (
        ISSUE_PRIORITY_ORDER.get(str(item.get("report_priority")), 99),
        -_safe_int(item.get("affected_objects")),
        -_safe_int(item.get("affected_requests")),
        -_safe_int(item.get("occurrence_count")),
        str(item.get("title") or ""),
    )


def _sql_sort_key(item: dict[str, Any]) -> tuple[int, int, int, str]:
    recommendation_weight = {"main_issue": 0, "section_highlight": 1, "appendix_candidate": 2}
    return (
        recommendation_weight.get(str(item.get("report_recommendation")), 9),
        _safe_int(item.get("rank_by_avg")) or 9999,
        _safe_int(item.get("rank_by_trace")) or 9999,
        str(item.get("sql_fingerprint") or ""),
    )


def _default_issue_key(candidate: dict[str, Any]) -> str:
    target_id = candidate.get("target_id") or candidate.get("object_id") or candidate.get("evidence_ref") or candidate.get("title") or "generic"
    return f"{candidate.get('issue_type') or 'generic'}:{target_id}"


def _default_primary_section(candidate: dict[str, Any]) -> str:
    mapping = {
        "system_health_warning": "3.1 业务系统总体检查",
        "action_latency": "3.3 事务与服务接口检查",
        "action_error": "3.3 事务与服务接口检查",
        "trace_bottleneck": "3.5 请求追踪与根因分析专题",
        "sql_latency": "3.4 SQL 检查",
    }
    return mapping.get(str(candidate.get("issue_type")), "3.6 其他问题")


def _default_issue_title(candidate: dict[str, Any]) -> str:
    return str(candidate.get("summary") or candidate.get("issue_type") or "未命名问题")


def _infer_severity_level(candidate: dict[str, Any]) -> str:
    response_time = _safe_float(candidate.get("response_time_ms"))
    failure_rate = _safe_float(candidate.get("failure_rate"))
    if candidate.get("fatal") or failure_rate >= 0.99:
        return "critical"
    if response_time >= 3000 or _safe_int(candidate.get("error_count")) > 0:
        return "high"
    if response_time >= 1000 or _safe_int(candidate.get("occurrence_count")) >= 3:
        return "medium"
    return "low"


def _infer_evidence_strength(candidate: dict[str, Any]) -> str:
    if candidate.get("selection_reason"):
        return "strong"
    if _safe_int(candidate.get("affected_traces")) >= 1 or _safe_int(candidate.get("affected_objects")) >= 2:
        return "medium"
    return "weak"


def _infer_business_criticality(candidate: dict[str, Any]) -> str:
    text = " ".join(
        str(candidate.get(key) or "")
        for key in ("title", "summary", "object_name", "action_name")
    ).lower()
    return _criticality_from_name(text)


def _criticality_from_name(name: Any) -> str:
    text = str(name or "").lower()
    if not text:
        return "medium"
    if any(keyword in text for keyword in CORE_BUSINESS_KEYWORDS) or any(token in text for token in ("/api/", "/dwr/", "/rest/", "login", "submit", "save")):
        return "high"
    if any(keyword in text for keyword in SUPPORT_KEYWORDS):
        return "medium"
    if any(keyword in text for keyword in BACKGROUND_KEYWORDS):
        return "low"
    return "medium"


def _legacy_issue_row(item: dict[str, Any]) -> dict[str, Any]:
    legacy = dict(item)
    legacy["priority"] = legacy.get("priority") or str(legacy.get("report_priority") or "").lower()
    legacy["details"] = legacy.get("details") or {}
    return legacy


def _normalize_sql_text(sql_text: str) -> str:
    text = (sql_text or "").strip().upper()
    if not text:
        return ""
    text = re.sub(r"'[^']*'", "?", text)
    text = re.sub(r'"[^"]*"', "?", text)
    text = re.sub(r"\b\d+\b", "?", text)
    text = re.sub(r"\s+", " ", text)
    return text


def _sql_matches_trace_action(related_actions: list[dict[str, Any]], trace_action_id: Any) -> bool:
    if trace_action_id is None:
        return False
    return any(str(item.get("actionId")) == str(trace_action_id) for item in related_actions)


def _trace_binding_strength(
    row: dict[str, Any],
    related_actions: list[dict[str, Any]],
    related_traces: list[dict[str, Any]],
    trace_case_ids: list[str],
) -> str:
    trace_count = _safe_int(row.get("traceCount"))
    if trace_case_ids or len(related_traces) >= 2 or len(related_actions) >= 2 or trace_count >= 5:
        return "strong"
    if len(related_traces) >= 1 or trace_count >= 1:
        return "medium"
    return "weak"


def _sql_report_recommendation(row: dict[str, Any], candidate_sources: set[str], trace_binding_strength: str) -> str:
    response_time = _safe_float(row.get("response_time_ms"))
    total_response_time = _safe_float(row.get("total_response_time_ms") or row.get("totalResptime"))
    if response_time >= 1000 and trace_binding_strength in {"strong", "medium"}:
        return "main_issue"
    if total_response_time >= 3000 and "optimization" in candidate_sources:
        return "section_highlight"
    if "optimization" in candidate_sources:
        return "appendix_candidate"
    return "section_highlight"


def _caller_objects(related_actions: list[dict[str, Any]], row: dict[str, Any]) -> list[dict[str, Any]]:
    if related_actions:
        return [
            {
                "action_id": item.get("actionId"),
                "application_id": item.get("applicationId"),
                "action_name": item.get("actionName") or item.get("actionAlias"),
            }
            for item in related_actions[:10]
        ]
    if row.get("actionId"):
        return [
            {
                "action_id": row.get("actionId"),
                "application_id": row.get("applicationId"),
                "action_name": row.get("actionName") or row.get("actionAlias"),
            }
        ]
    return []


def _impact_objects(related_actions: list[dict[str, Any]], row: dict[str, Any]) -> list[dict[str, Any]]:
    objects = _caller_objects(related_actions, row)
    if not objects and row.get("componentName"):
        objects = [{"component_name": row.get("componentName"), "component_subtype": row.get("componentSubtype")}]
    return objects


def _optimization_hypothesis(feature_tags: list[str], row: dict[str, Any]) -> str:
    if not feature_tags:
        if _safe_float(row.get("count")) >= 20:
            return "调用频次较高，可优先检查索引、批量读取与结果集裁剪。"
        return "建议结合执行计划与调用者分布确认是否需要优化。"
    if "SUBQUERY" in feature_tags or "JOIN" in feature_tags or "LEFT_JOIN" in feature_tags:
        return "SQL 结构较复杂，建议优先检查 JOIN / 子查询执行计划与索引覆盖。"
    if "ORDER_BY" in feature_tags or "GROUP_BY" in feature_tags or "DISTINCT" in feature_tags:
        return "排序或聚合特征明显，建议核对排序列和聚合列上的索引策略。"
    if "LIKE_PREFIXLESS" in feature_tags or "FUNCTION_ON_COLUMN" in feature_tags:
        return "存在索引失效风险，建议优先检查谓词写法。"
    return "SQL 具备潜在优化空间，建议结合执行计划进一步确认。"


def _merge_named_objects(left: list[dict[str, Any]], right: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    merged: list[dict[str, Any]] = []
    for item in left + right:
        key = json.dumps(item, ensure_ascii=False, sort_keys=True)
        if key in seen:
            continue
        seen.add(key)
        merged.append(item)
    return merged[:10]


def _better_sql_recommendation(current: Any, other: Any) -> str:
    ranking = {"main_issue": 0, "section_highlight": 1, "appendix_candidate": 2}
    current_value = str(current or "appendix_candidate")
    other_value = str(other or "appendix_candidate")
    return current_value if ranking.get(current_value, 9) <= ranking.get(other_value, 9) else other_value


def _better_trace_strength(current: Any, other: Any) -> str:
    ranking = {"strong": 0, "medium": 1, "weak": 2}
    current_value = str(current or "weak")
    other_value = str(other or "weak")
    return current_value if ranking.get(current_value, 9) <= ranking.get(other_value, 9) else other_value


def _overall_assessment(issues: list[dict[str, Any]], sql_main_candidates: list[dict[str, Any]], capability_boundary: dict[str, Any]) -> str:
    if any(item.get("report_priority") == "P0" for item in issues):
        return "当前时间窗存在需要优先展开的高危问题，建议正文先写主链路风险与根因证据。"
    if issues or sql_main_candidates:
        return "当前时间窗存在可稳定成稿的问题与 SQL 重点对象，适合直接进入正式报告编排。"
    if ((capability_boundary or {}).get("page_experience") or {}).get("status") == "partial":
        return "当前证据以服务端与拓扑侧为主，页面侧需要明确能力边界后再下结论。"
    return "当前时间窗未发现足够强的正文主问题，可先以观察项和能力边界为主。"


def _manual_review_items(
    capability_boundary: dict[str, Any],
    issues: list[dict[str, Any]],
    sql_main_candidates: list[dict[str, Any]],
    page_payload: dict[str, Any],
) -> list[str]:
    items: list[str] = []
    page_boundary = (capability_boundary or {}).get("page_experience") or {}
    if page_boundary.get("status") == "partial":
        items.append("页面体验证据仍是降级版代理层，请在成稿中明确能力边界。")
    if not issues:
        items.append("当前没有进入正文主问题的对象，请确认是否需要以观察项为主组织报告。")
    if sql_main_candidates and not (page_payload.get("pages") or []):
        items.append("SQL 章节已有重点对象，但页面侧缺少对应上下文，请补充业务影响描述。")
    if any(item.get("report_priority") == "P0" for item in issues):
        items.append("存在 P0 问题，建议人工确认标题表述和影响范围后再定稿。")
    return items


def _render_issue_markdown(items: list[dict[str, Any]], *, fallback: str) -> list[str]:
    if not items:
        return [fallback]
    lines: list[str] = []
    for item in items[:8]:
        lines.append(
            f"- [{item.get('report_priority')}] {item.get('title')} | 类型: {item.get('issue_type')} | 证据: {item.get('evidence_strength')} | 原因: {item.get('selection_reason') or item.get('downgrade_reason')}"
        )
    return lines


def _render_sql_markdown(items: list[dict[str, Any]], *, fallback: str) -> list[str]:
    if not items:
        return [fallback]
    lines: list[str] = []
    for item in items[:8]:
        metrics = item.get("metrics") or {}
        lines.append(
            f"- [{item.get('report_recommendation')}] {item.get('sql_fingerprint')} | 平均耗时: {metrics.get('response_time_ms')} ms | 来源: {','.join(item.get('candidate_source') or [])} | trace 绑定: {item.get('trace_binding_strength')}"
        )
    return lines


def _safe_int(value: Any) -> int:
    try:
        return int(float(value or 0))
    except (TypeError, ValueError):
        return 0


def _safe_float(value: Any) -> float:
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0
