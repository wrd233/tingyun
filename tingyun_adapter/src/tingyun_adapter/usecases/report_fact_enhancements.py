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


def build_candidate_registry(
    *,
    report_scope: dict[str, Any],
    snapshot_payload: dict[str, Any],
    diagnostic_payload: dict[str, Any],
    hotspot_payload: dict[str, Any],
    trace_candidates: list[dict[str, Any]],
    trace_case: dict[str, Any],
    sql_candidates: list[dict[str, Any]],
    external_payload: dict[str, Any],
    comparison_payload: dict[str, Any],
    labels_payload: dict[str, Any],
    stability_payload: dict[str, Any],
    impact_payload: dict[str, Any],
    knowledge_payload: dict[str, Any],
) -> list[dict[str, Any]]:
    registry: list[dict[str, Any]] = []
    registry.extend(_system_signal_candidates(report_scope, snapshot_payload, diagnostic_payload))
    registry.extend(_action_candidates(hotspot_payload, labels_payload, stability_payload, impact_payload))
    registry.extend(_trace_candidates(trace_candidates, trace_case))
    registry.extend(_sql_registry_candidates(sql_candidates))
    registry.extend(_dependency_candidates(external_payload))
    registry.extend(_comparison_candidates(comparison_payload))
    registry = _merge_candidate_registry(registry)
    registry = _enrich_candidate_registry_with_context(registry, labels_payload, stability_payload, impact_payload, comparison_payload, knowledge_payload)
    return sorted(registry, key=_candidate_sort_key)


def select_candidate_outcomes(candidate_registry: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    main_issue_selections: list[dict[str, Any]] = []
    observation_candidates: list[dict[str, Any]] = []
    sql_opportunity_candidates: list[dict[str, Any]] = []
    deep_dive_targets: list[dict[str, Any]] = []

    for candidate in candidate_registry:
        bucket = _candidate_selection_bucket(candidate)
        selected = dict(candidate)
        selected["selection_bucket"] = bucket
        selected["selection_reason"] = _candidate_selection_reason(candidate, bucket)
        if bucket == "main_issue":
            main_issue_selections.append(selected)
        elif bucket == "sql_opportunity":
            sql_opportunity_candidates.append(selected)
        elif bucket == "deep_dive":
            deep_dive_targets.append(selected)
        else:
            observation_candidates.append(selected)

    return {
        "main_issue_selections": main_issue_selections[:8],
        "observation_candidates": observation_candidates[:12],
        "sql_opportunity_candidates": sql_opportunity_candidates[:12],
        "deep_dive_targets": deep_dive_targets[:6],
    }


def build_codex_review_input(
    *,
    report_scope: dict[str, Any],
    summary: dict[str, Any],
    candidate_registry: list[dict[str, Any]],
    main_issue_selections: list[dict[str, Any]],
    observation_candidates: list[dict[str, Any]],
    sql_opportunity_candidates: list[dict[str, Any]],
    deep_dive_targets: list[dict[str, Any]],
    knowledge_payload: dict[str, Any],
) -> dict[str, Any]:
    return {
        "scope": report_scope,
        "summary": summary,
        "candidate_registry_count": len(candidate_registry),
        "main_issue_candidates": main_issue_selections,
        "observation_candidates": observation_candidates,
        "sql_candidates": {
            "main_issue_level": [item for item in main_issue_selections if item.get("candidate_type") == "sql"],
            "optimization_level": sql_opportunity_candidates,
        },
        "deep_dive_targets": deep_dive_targets,
        "knowledge_context": {
            "confirmed_entry_count": ((knowledge_payload.get("confirmed_knowledge_summary") or {}).get("entry_count")),
            "pending_count": ((knowledge_payload.get("pending_proposals_summary") or {}).get("pending_count")),
            "missing_items": knowledge_payload.get("missing_items") or [],
        },
    }


def render_codex_review_input_markdown(review_input: dict[str, Any]) -> str:
    lines = [
        "# Codex Review Input",
        "",
        "## 巡检范围",
        f"- 业务系统: {((review_input.get('scope') or {}).get('bizSystemId'))}",
        f"- 时间窗: {((review_input.get('scope') or {}).get('endTime'))}",
        f"- 候选总数: {review_input.get('candidate_registry_count') or 0}",
        "",
        "## 主问题高可信候选",
    ]
    lines.extend(_render_candidate_markdown(review_input.get("main_issue_candidates") or [], fallback="- 当前没有高可信主问题候选。"))
    lines.extend(["", "## 观察项候选"])
    lines.extend(_render_candidate_markdown(review_input.get("observation_candidates") or [], fallback="- 当前没有 observation 候选。"))
    lines.extend(["", "## SQL 候选"])
    sql_candidates = review_input.get("sql_candidates") or {}
    lines.append("### 主问题级 SQL 候选")
    lines.extend(_render_candidate_markdown((sql_candidates.get("main_issue_level") or []), fallback="- 当前没有主问题级 SQL 候选。"))
    lines.append("")
    lines.append("### 优化机会级 SQL 候选")
    lines.extend(_render_candidate_markdown((sql_candidates.get("optimization_level") or []), fallback="- 当前没有优化机会级 SQL 候选。"))
    lines.extend(["", "## 建议进一步深挖的对象"])
    lines.extend(_render_candidate_markdown(review_input.get("deep_dive_targets") or [], fallback="- 当前没有建议进一步深挖的对象。"))
    return "\n".join(lines).strip() + "\n"


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
    candidate_registry: list[dict[str, Any]],
    sql_candidates: list[dict[str, Any]],
    sql_opportunities: list[dict[str, Any]],
    main_issue_selections: list[dict[str, Any]],
    deep_dive_targets: list[dict[str, Any]],
    codex_review_input: dict[str, Any],
    codex_review_markdown: str,
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
        "03_issues/main_issue_selections.json": {"format": "json", "data": main_issue_selections},
        "03_issues/deep_dive_targets.json": {"format": "json", "data": deep_dive_targets},
        "04_raw/candidate_registry.json": {"format": "json", "data": candidate_registry},
        "04_raw/issue_candidates.json": {"format": "json", "data": issue_candidates},
        "04_raw/sql_candidates.json": {"format": "json", "data": sql_candidates},
        "00_internal/codex_review_input.json": {"format": "json", "data": codex_review_input},
        "00_internal/codex_review_input.md": {"format": "markdown", "content": codex_review_markdown},
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


def _system_signal_candidates(report_scope: dict[str, Any], snapshot_payload: dict[str, Any], diagnostic_payload: dict[str, Any]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for index, signal in enumerate(diagnostic_payload.get("system_signals") or [], start=1):
        signal_type = str(signal.get("type") or f"signal_{index}")
        level = str(signal.get("level") or "medium")
        candidates.append(
            {
                "candidate_key": f"signal:{signal_type}:{index}",
                "candidate_type": "regression_signal",
                "target_ref": {"kind": "system_signal", "signal_type": signal_type, "biz_system_id": report_scope.get("bizSystemId")},
                "display_name": signal_type,
                "source_packs": ["diagnostic_candidate_pack", "system_snapshot"],
                "source_basis": ["system_signal"],
                "evidence_refs": [str(signal.get("source_api") or "system_snapshot")],
                "evidence_strength": "medium" if level in {"medium", "high"} else "weak",
                "occurrence_count": max(1, _safe_int(signal.get("value"))),
                "active_windows": 1,
                "impact_scope": "cross_object" if level == "high" else "local",
                "review_hints": [signal_type, level],
                "recommended_next_packs": ["system_snapshot"],
            }
        )
    health = (snapshot_payload.get("health") or {}).get("action") or {}
    if _safe_int(health.get("warn")) > 0:
        candidates.append(
            {
                "candidate_key": f"signal:action_warn:{_safe_int(health.get('warn'))}",
                "candidate_type": "regression_signal",
                "target_ref": {"kind": "system_health", "metric": "action_warn", "biz_system_id": report_scope.get("bizSystemId")},
                "display_name": "action_warn",
                "source_packs": ["system_snapshot"],
                "source_basis": ["health_warning"],
                "evidence_refs": ["health_level_statistics"],
                "evidence_strength": "strong",
                "occurrence_count": _safe_int(health.get("warn")),
                "active_windows": 1,
                "impact_scope": "cross_object",
                "review_hints": ["action_health_warn", "high"],
                "recommended_next_packs": ["system_snapshot", "diagnostic_candidate_pack"],
            }
        )
    return candidates


def _action_candidates(
    hotspot_payload: dict[str, Any],
    labels_payload: dict[str, Any],
    stability_payload: dict[str, Any],
    impact_payload: dict[str, Any],
) -> list[dict[str, Any]]:
    label_map = {_target_ref_signature(item.get("target_ref") or {}): item for item in labels_payload.get("objects") or []}
    stability_map = {_target_ref_signature(item.get("target_ref") or {}): item for item in stability_payload.get("objects") or []}
    impact_map = {_target_ref_signature(item.get("target_ref") or {}): item for item in impact_payload.get("objects") or []}
    candidates: list[dict[str, Any]] = []
    for hotspot in hotspot_payload.get("hotspots") or []:
        action = hotspot.get("action") or {}
        target_ref = {
            "kind": "action",
            "biz_system_id": action.get("biz_system_id"),
            "application_id": action.get("application_id"),
            "action_id": action.get("id"),
            "action_type": action.get("type"),
        }
        signature = _target_ref_signature(target_ref)
        labels = label_map.get(signature) or {}
        stability = stability_map.get(signature) or {}
        impact = impact_map.get(signature) or {}
        review_hints = [signal.get("type") for signal in hotspot.get("suspect_signals") or []]
        review_hints.extend(list(labels.get("candidate_labels") or [])[:3])
        if (impact.get("priority_hints") or {}).get("review_priority"):
            review_hints.append(str((impact.get("priority_hints") or {}).get("review_priority")))
        if stability.get("stability_class"):
            review_hints.append(str(stability.get("stability_class")))
        candidates.append(
            {
                "candidate_key": f"action:{action.get('application_id')}:{action.get('id')}:{action.get('type')}",
                "candidate_type": "action",
                "target_ref": target_ref,
                "display_name": action.get("name") or action.get("alias"),
                "source_packs": ["action_hotspot_pack"],
                "source_basis": ["top_hotspot"],
                "evidence_refs": ["action_list", "action_overview"],
                "evidence_strength": "strong" if hotspot.get("overview") else "medium",
                "occurrence_count": max(
                    _safe_int((action.get("metrics") or {}).get("slow_count")),
                    _safe_int((action.get("metrics") or {}).get("error_count")),
                    1,
                ),
                "active_windows": 2 if _safe_int((action.get("metrics") or {}).get("slow_count")) >= 3 else 1,
                "impact_scope": _impact_scope_from_action(labels, impact),
                "review_hints": _unique_strings(review_hints),
                "recommended_next_packs": ["action_fact_sheet", "action_dependency_breakdown_pack"],
            }
        )
    return candidates


def _trace_candidates(trace_candidates: list[dict[str, Any]], trace_case: dict[str, Any]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for item in trace_candidates:
        review_hints = [signal.get("type") for signal in item.get("suspect_signals") or []]
        if _safe_float(item.get("duration_ms")) >= 1000:
            review_hints.append("high_latency")
        candidates.append(
            {
                "candidate_key": f"trace:{item.get('trace_id_numeric') or item.get('trace_guid')}",
                "candidate_type": "trace",
                "target_ref": {
                    "kind": "trace",
                    "trace_id_numeric": item.get("trace_id_numeric"),
                    "trace_guid": item.get("trace_guid"),
                    "action_guid": item.get("action_guid"),
                    "query_timestamp": item.get("query_timestamp"),
                },
                "display_name": item.get("trace_id_numeric") or item.get("trace_guid"),
                "source_packs": ["trace_case_pack"],
                "source_basis": ["trace_candidate"],
                "evidence_refs": ["graph/query/overview"],
                "evidence_strength": "strong" if item.get("suspect_signals") else "medium",
                "occurrence_count": 1,
                "active_windows": 1,
                "impact_scope": "core_path" if review_hints else "local",
                "review_hints": _unique_strings(review_hints),
                "recommended_next_packs": ["trace_fact_sheet"],
            }
        )
    trace_info = (trace_case or {}).get("trace") or {}
    if trace_info:
        candidates.append(
            {
                "candidate_key": f"trace:{trace_info.get('trace_id_numeric') or trace_info.get('trace_guid')}",
                "candidate_type": "trace",
                "target_ref": {
                    "kind": "trace",
                    "trace_id_numeric": trace_info.get("trace_id_numeric"),
                    "trace_guid": trace_info.get("trace_guid"),
                    "action_guid": trace_info.get("action_guid"),
                    "query_timestamp": trace_info.get("timestamp"),
                },
                "display_name": trace_info.get("trace_id_numeric") or trace_info.get("trace_guid"),
                "source_packs": ["trace_case_pack"],
                "source_basis": ["representative_trace"],
                "evidence_refs": ["trace_detail", "trace_call_tree"],
                "evidence_strength": "strong" if trace_info.get("suspected_problems") else "medium",
                "occurrence_count": max(1, len(trace_info.get("suspected_problems") or [])),
                "active_windows": 1,
                "impact_scope": "core_path" if trace_info.get("suspected_problems") else "local",
                "review_hints": _unique_strings(["representative_trace"] + [item.get("type") for item in trace_info.get("suspected_problems") or [] if item.get("type")]),
                "recommended_next_packs": ["trace_fact_sheet"],
            }
        )
    return candidates


def _sql_registry_candidates(sql_candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for item in sql_candidates:
        hints = list(item.get("candidate_source") or []) + list(item.get("sql_feature_tags") or [])
        target_ref = {
            "kind": "sql",
            "sql_fingerprint": item.get("sql_fingerprint"),
            "component_name": item.get("component_name"),
            "component_subtype": item.get("component_subtype"),
            "op_name": item.get("sql_text"),
        }
        candidates.append(
            {
                "candidate_key": f"sql:{item.get('sql_fingerprint')}",
                "candidate_type": "sql",
                "target_ref": target_ref,
                "display_name": item.get("sql_fingerprint"),
                "source_packs": ["slow_sql_pack"] + (["trace_case_pack"] if "trace_bound" in (item.get("candidate_source") or []) else []),
                "source_basis": item.get("candidate_source") or [],
                "evidence_refs": ["slow_sql_analysis", "component/database/actionList", "component/database/actionTraceList"],
                "evidence_strength": "strong" if item.get("trace_binding_strength") == "strong" else ("medium" if item.get("trace_binding_strength") == "medium" else "weak"),
                "occurrence_count": _safe_int((item.get("metrics") or {}).get("count")) or 1,
                "active_windows": 2 if item.get("trace_binding_strength") in {"strong", "medium"} else 1,
                "impact_scope": "core_path" if len(item.get("impact_objects") or []) >= 2 else ("cross_object" if len(item.get("impact_objects") or []) >= 1 else "local"),
                "review_hints": _unique_strings(hints),
                "recommended_next_packs": ["sql_fact_sheet"],
                "report_recommendation": item.get("report_recommendation"),
            }
        )
    return candidates


def _dependency_candidates(external_payload: dict[str, Any]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for item in external_payload.get("external_dependencies") or []:
        review_hints = [str(item.get("protocol") or "external_dependency")]
        if _safe_float(item.get("response_time_ms")) >= 1000:
            review_hints.append("high_latency")
        if _safe_float(item.get("error_rate")) > 0:
            review_hints.append("error_present")
        candidates.append(
            {
                "candidate_key": f"dependency:{item.get('node_id')}",
                "candidate_type": "dependency",
                "target_ref": {"kind": "dependency", "node_id": item.get("node_id"), "protocol": item.get("protocol")},
                "display_name": item.get("node_id"),
                "source_packs": ["external_dependency_pack"],
                "source_basis": ["dependency_latency"],
                "evidence_refs": ["external_topology", "external_protocol_analysis"],
                "evidence_strength": "strong" if _safe_float(item.get("response_time_ms")) >= 1000 else "medium",
                "occurrence_count": max(1, _safe_int(item.get("link_count"))),
                "active_windows": 1,
                "impact_scope": "cross_object" if _safe_int(item.get("link_count")) > 1 else "local",
                "review_hints": review_hints,
                "recommended_next_packs": ["external_dependency_pack", "topology_dependency_pack"],
            }
        )
    return candidates


def _comparison_candidates(comparison_payload: dict[str, Any]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for item in comparison_payload.get("objects") or []:
        target_ref = item.get("target_ref") or {}
        change_class = str(item.get("change_class") or "stable_risk")
        candidates.append(
            {
                "candidate_key": f"regression:{_target_ref_signature(target_ref)}:{change_class}",
                "candidate_type": "regression_signal",
                "target_ref": target_ref,
                "display_name": item.get("display_name"),
                "source_packs": ["comparison_signals_pack"],
                "source_basis": ["comparison_regression"],
                "evidence_refs": item.get("evidence_refs") or [],
                "evidence_strength": "medium" if item.get("trend_confidence") in {"medium", "high"} else "weak",
                "occurrence_count": 1,
                "active_windows": 2,
                "impact_scope": "cross_object" if change_class in {"new_risk", "regressed"} else "local",
                "review_hints": _unique_strings([change_class, item.get("trend_confidence")]),
                "recommended_next_packs": _recommended_next_packs_for_target_ref(target_ref),
            }
        )
    return candidates


def _merge_candidate_registry(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged_by_key: dict[str, dict[str, Any]] = {}
    by_target_signature: dict[str, str] = {}
    for candidate in candidates:
        candidate_key = str(candidate.get("candidate_key") or "candidate:unknown")
        target_signature = _target_ref_signature(candidate.get("target_ref") or {})
        existing_key = merged_by_key.get(candidate_key) and candidate_key or by_target_signature.get(target_signature)
        if existing_key is None or _should_keep_regression_separate(candidate, merged_by_key.get(existing_key, {})):
            merged_by_key[candidate_key] = dict(candidate)
            if target_signature:
                by_target_signature[target_signature] = candidate_key
            continue
        current = merged_by_key[existing_key]
        current["source_packs"] = sorted(set((current.get("source_packs") or []) + (candidate.get("source_packs") or [])))
        current["source_basis"] = sorted(set((current.get("source_basis") or []) + (candidate.get("source_basis") or [])))
        current["evidence_refs"] = sorted(set((current.get("evidence_refs") or []) + (candidate.get("evidence_refs") or [])))
        current["review_hints"] = _unique_strings((current.get("review_hints") or []) + (candidate.get("review_hints") or []))
        current["recommended_next_packs"] = _unique_strings((current.get("recommended_next_packs") or []) + (candidate.get("recommended_next_packs") or []))
        current["occurrence_count"] = max(_safe_int(current.get("occurrence_count")), _safe_int(candidate.get("occurrence_count")))
        current["active_windows"] = max(_safe_int(current.get("active_windows")), _safe_int(candidate.get("active_windows")))
        current["evidence_strength"] = _better_evidence_strength(current.get("evidence_strength"), candidate.get("evidence_strength"))
        current["impact_scope"] = _better_impact_scope(current.get("impact_scope"), candidate.get("impact_scope"))
    return list(merged_by_key.values())


def _enrich_candidate_registry_with_context(
    registry: list[dict[str, Any]],
    labels_payload: dict[str, Any],
    stability_payload: dict[str, Any],
    impact_payload: dict[str, Any],
    comparison_payload: dict[str, Any],
    knowledge_payload: dict[str, Any],
) -> list[dict[str, Any]]:
    label_map = {_target_ref_signature(item.get("target_ref") or {}): item for item in labels_payload.get("objects") or []}
    stability_map = {_target_ref_signature(item.get("target_ref") or {}): item for item in stability_payload.get("objects") or []}
    impact_map = {_target_ref_signature(item.get("target_ref") or {}): item for item in impact_payload.get("objects") or []}
    comparison_map = {_target_ref_signature(item.get("target_ref") or {}): item for item in comparison_payload.get("objects") or []}
    knowledge_context = knowledge_payload.get("core_context") or {}
    for item in registry:
        signature = _target_ref_signature(item.get("target_ref") or {})
        labels = label_map.get(signature) or {}
        stability = stability_map.get(signature) or {}
        impact = impact_map.get(signature) or {}
        comparison = comparison_map.get(signature) or {}
        item["source_packs"] = _unique_strings((item.get("source_packs") or []) + _extra_pack_names(labels, stability, impact, comparison))
        item["review_hints"] = _unique_strings(
            (item.get("review_hints") or [])
            + list(labels.get("candidate_labels") or [])[:3]
            + [stability.get("stability_class"), comparison.get("change_class"), (impact.get("priority_hints") or {}).get("review_priority")]
        )
        item["source_basis"] = _unique_strings(
            (item.get("source_basis") or [])
            + [basis.get("value") for basis in comparison.get("source_basis") or [] if basis.get("value")]
        )
        item["knowledge_context"] = {
            "confirmed_labels": labels.get("confirmed_labels") or [],
            "stability_class": stability.get("stability_class"),
            "review_priority": (impact.get("priority_hints") or {}).get("review_priority"),
            "change_class": comparison.get("change_class"),
            "known_patterns": knowledge_context.get("known_patterns", [])[:2] if isinstance(knowledge_context, dict) else [],
        }
    return registry


def _candidate_selection_bucket(candidate: dict[str, Any]) -> str:
    candidate_type = str(candidate.get("candidate_type") or "")
    evidence_strength = str(candidate.get("evidence_strength") or "weak")
    impact_scope = str(candidate.get("impact_scope") or "local")
    review_hints = {str(item) for item in candidate.get("review_hints") or []}
    report_recommendation = str(candidate.get("report_recommendation") or "")

    if candidate_type == "sql":
        if report_recommendation == "main_issue" and evidence_strength in {"strong", "medium"}:
            return "main_issue"
        if "optimization" in review_hints or report_recommendation == "appendix_candidate":
            return "sql_opportunity"
        if evidence_strength == "weak":
            return "deep_dive"
        return "observation"

    if evidence_strength == "strong" and impact_scope in {"core_path", "cross_object"}:
        return "main_issue"
    if {"new_risk", "regressed", "high_review", "high_latency", "error_present"} & review_hints and evidence_strength != "weak":
        return "main_issue"
    if "low_frequency" in review_hints or "needs_confirmation" in review_hints or evidence_strength == "weak":
        return "observation"
    if candidate.get("recommended_next_packs"):
        return "deep_dive"
    return "observation"


def _candidate_selection_reason(candidate: dict[str, Any], bucket: str) -> str:
    hints = ", ".join([str(item) for item in (candidate.get("review_hints") or [])[:4]])
    if bucket == "main_issue":
        return f"证据强度={candidate.get('evidence_strength')}，影响范围={candidate.get('impact_scope')}，review_hints={hints}"
    if bucket == "sql_opportunity":
        return f"SQL 已进入优化机会池，推荐后续用 {', '.join(candidate.get('recommended_next_packs') or [])} 补证。"
    if bucket == "deep_dive":
        return f"当前证据不足以下最终结论，建议继续构建 {', '.join(candidate.get('recommended_next_packs') or [])}。"
    return f"当前更适合作为 observation 保留，主要提示为 {hints or '弱证据或低频'}。"


def _render_candidate_markdown(items: list[dict[str, Any]], *, fallback: str) -> list[str]:
    if not items:
        return [fallback]
    lines: list[str] = []
    for item in items[:8]:
        lines.append(
            f"- {item.get('display_name')} | 类型: {item.get('candidate_type')} | 来源: {','.join(item.get('source_packs') or [])} | hints: {','.join(item.get('review_hints') or [])} | 推荐深挖: {','.join(item.get('recommended_next_packs') or [])}"
        )
    return lines


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


def _target_ref_signature(target_ref: dict[str, Any]) -> str:
    if not target_ref:
        return ""
    return json.dumps(target_ref, ensure_ascii=False, sort_keys=True)


def _impact_scope_from_action(labels: dict[str, Any], impact: dict[str, Any]) -> str:
    candidate_labels = set(str(item) for item in labels.get("candidate_labels") or [])
    review_priority = str((impact.get("priority_hints") or {}).get("review_priority") or "")
    if {"core_business_path", "real_user_visible", "user_entry"} & candidate_labels:
        return "core_path"
    if review_priority == "high_review":
        return "cross_object"
    return "local"


def _recommended_next_packs_for_target_ref(target_ref: dict[str, Any]) -> list[str]:
    kind = str((target_ref or {}).get("kind") or "")
    if kind == "action":
        return ["action_fact_sheet", "action_dependency_breakdown_pack"]
    if kind == "trace":
        return ["trace_fact_sheet"]
    if kind == "sql":
        return ["sql_fact_sheet"]
    if kind == "dependency":
        return ["external_dependency_pack", "topology_dependency_pack"]
    if kind == "instance":
        return ["instance_analysis_pack"]
    return []


def _extra_pack_names(*objects: dict[str, Any]) -> list[str]:
    names: list[str] = []
    mapping = {
        "candidate_labels": "business_labels_pack",
        "stability_class": "stability_signals_pack",
        "priority_hints": "impact_signals_pack",
        "change_class": "comparison_signals_pack",
    }
    for item in objects:
        for key, value in mapping.items():
            if item.get(key):
                names.append(value)
    return names


def _should_keep_regression_separate(candidate: dict[str, Any], current: dict[str, Any]) -> bool:
    return candidate.get("candidate_type") == "regression_signal" and current.get("candidate_type") == "regression_signal"


def _better_evidence_strength(current: Any, other: Any) -> str:
    ranking = {"strong": 0, "medium": 1, "weak": 2}
    current_value = str(current or "weak")
    other_value = str(other or "weak")
    return current_value if ranking.get(current_value, 9) <= ranking.get(other_value, 9) else other_value


def _better_impact_scope(current: Any, other: Any) -> str:
    ranking = {"core_path": 0, "cross_object": 1, "local": 2}
    current_value = str(current or "local")
    other_value = str(other or "local")
    return current_value if ranking.get(current_value, 9) <= ranking.get(other_value, 9) else other_value


def _candidate_sort_key(item: dict[str, Any]) -> tuple[int, int, int, str]:
    scope_ranking = {"core_path": 0, "cross_object": 1, "local": 2}
    strength_ranking = {"strong": 0, "medium": 1, "weak": 2}
    return (
        strength_ranking.get(str(item.get("evidence_strength")), 9),
        scope_ranking.get(str(item.get("impact_scope")), 9),
        -_safe_int(item.get("occurrence_count")),
        str(item.get("display_name") or ""),
    )


def _unique_strings(items: list[Any]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for item in items:
        text = str(item or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


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
