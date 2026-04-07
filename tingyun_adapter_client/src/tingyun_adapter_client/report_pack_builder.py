from __future__ import annotations

import csv
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from .http_client import AdapterRemoteClient

CORE_PACK_TYPES = [
    "knowledge_context_pack",
    "system_snapshot",
    "diagnostic_candidate_pack",
    "report_fact_pack",
    "page_experience_pack",
    "topology_dependency_pack",
    "external_dependency_pack",
    "slow_sql_pack",
    "business_labels_pack",
    "stability_signals_pack",
    "impact_signals_pack",
    "comparison_signals_pack",
    "screenshot_index_pack",
]
OPTIONAL_CORE_PACK_TYPES = {"business_labels_pack", "stability_signals_pack", "impact_signals_pack", "comparison_signals_pack", "screenshot_index_pack"}

SECTION_PAGE_TYPE_MAP = {
    "business_system_overview": "overview",
    "business_system_topology": "system_overview",
    "action_hotspot_list": "interface",
    "action_overview": "interface",
    "trace_detail": "trace_cases",
    "database_component_overview": "sql",
    "database_sql_analysis": "sql",
    "sql_detail": "sql",
    "sql_related_actions": "sql",
    "instance_overview": "application",
    "page_experience_proxy": "page",
}


def build_report_pack(
    client: AdapterRemoteClient,
    *,
    biz_system_id: int,
    start_time: str,
    end_time: str,
    source_mode: str,
    limit: int,
    output_dir: str,
    command_display: str,
) -> dict[str, Any]:
    start_dt = _parse_user_time(start_time, end_of_day=False)
    end_dt = _parse_user_time(end_time, end_of_day=True)
    if end_dt < start_dt:
        raise RuntimeError("end_time must be later than start_time")
    period_minutes = int((end_dt - start_dt).total_seconds() // 60)
    end_time_text = end_dt.strftime("%Y-%m-%d %H:%M")

    root = Path(output_dir).expanduser().resolve()
    internal_dir = root / "00_internal"
    foundation_dir = root / "01_foundation"
    sections_dir = root / "02_sections"
    issues_dir = root / "03_issues"
    raw_dir = root / "04_raw"
    knowledge_dir = root / "05_knowledge"
    proposal_dir = knowledge_dir / "proposals"
    for path in (internal_dir, foundation_dir, sections_dir, issues_dir, raw_dir, knowledge_dir, proposal_dir):
        path.mkdir(parents=True, exist_ok=True)

    command_log: list[str] = [
        f"- build-report-pack: `{command_display}`",
        f"- time_window: `{start_dt.strftime('%Y-%m-%d %H:%M')} -> {end_dt.strftime('%Y-%m-%d %H:%M')}`",
        f"- source_mode: `{source_mode}`",
    ]
    fetch_failures: dict[str, str] = {}

    try:
        healthz = client.healthz()
        command_log.append("- fetched `healthz` from remote adapter service")
    except Exception as exc:
        healthz = {"status": "unavailable", "error": str(exc)}
        fetch_failures["healthz"] = str(exc)
        command_log.append(f"- failed `healthz`: `{exc}`")
    try:
        meta = client.meta()
        command_log.append("- fetched `meta` from remote adapter service")
    except Exception as exc:
        meta = {"service": "tingyun-adapter", "pack_types": [], "error": str(exc)}
        fetch_failures["meta"] = str(exc)
        command_log.append(f"- failed `meta`: `{exc}`")

    base_payload = {
        "bizSystemId": biz_system_id,
        "endTime": end_time_text,
        "periodMinutes": period_minutes,
        "sourceMode": source_mode,
        "limit": limit,
    }

    fetched: dict[str, dict[str, Any]] = {}
    raw_files: list[str] = []
    for pack_type in CORE_PACK_TYPES:
        try:
            fetched_pack, raw_path = _fetch_pack(client, raw_dir, pack_type, dict(base_payload))
        except Exception as exc:
            if pack_type in OPTIONAL_CORE_PACK_TYPES:
                fetch_failures[pack_type] = str(exc)
                command_log.append(f"- failed optional `{pack_type}`: `{exc}`")
                continue
            raise
        fetched[pack_type] = fetched_pack
        raw_files.append(str(raw_path.relative_to(root)))
        command_log.append(f"- fetched `{pack_type}` -> `{raw_path.relative_to(root)}`")

    report_fact_payload = fetched["report_fact_pack"]["payload"]
    system_snapshot_payload = fetched["system_snapshot"]["payload"]
    slow_sql_payload = fetched["slow_sql_pack"]["payload"]

    action_refs = _select_focus_action_refs(report_fact_payload, limit=max(limit + 3, 8))
    action_facts: list[dict[str, Any]] = []
    trace_facts: list[dict[str, Any]] = []
    for action_ref in action_refs:
        payload = dict(base_payload)
        payload.update(
            {
                "applicationId": action_ref["application_id"],
                "actionId": action_ref["action_id"],
                "actionType": action_ref["action_type"],
            }
        )
        try:
            action_pack, raw_path = _fetch_pack(client, raw_dir, "action_fact_sheet", payload)
        except Exception as exc:
            fetch_failures[f"action_fact_sheet:{action_ref['application_id']}:{action_ref['action_id']}"] = str(exc)
            command_log.append(
                f"- failed optional `action_fact_sheet` for `{action_ref['application_id']}/{action_ref['action_id']}`: `{exc}`"
            )
            continue
        action_facts.append(action_pack)
        raw_files.append(str(raw_path.relative_to(root)))
        command_log.append(f"- fetched `action_fact_sheet` -> `{raw_path.relative_to(root)}`")

        trace_selector = _first_trace_selector(action_pack.get("payload") or {})
        if not trace_selector:
            continue
        trace_payload = dict(base_payload)
        trace_payload.update(
            {
                "applicationId": action_ref["application_id"],
                "actionId": action_ref["action_id"],
                "actionType": action_ref["action_type"],
                "traceId": trace_selector.get("trace_id_numeric"),
                "queryTimestamp": trace_selector.get("query_timestamp"),
                "traceGuid": trace_selector.get("trace_guid"),
                "actionGuid": trace_selector.get("action_guid"),
                "requestId": trace_selector.get("request_id"),
            }
        )
        try:
            trace_pack, raw_path = _fetch_pack(client, raw_dir, "trace_fact_sheet", trace_payload)
        except Exception as exc:
            fetch_failures[f"trace_fact_sheet:{trace_selector.get('trace_id_numeric')}"] = str(exc)
            command_log.append(f"- failed optional `trace_fact_sheet` for `{trace_selector.get('trace_id_numeric')}`: `{exc}`")
            continue
        trace_facts.append(trace_pack)
        raw_files.append(str(raw_path.relative_to(root)))
        command_log.append(f"- fetched `trace_fact_sheet` -> `{raw_path.relative_to(root)}`")

    database_pack: dict[str, Any] | None = None
    sql_fact_pack: dict[str, Any] | None = None
    primary_component_ref = _primary_database_component_ref(slow_sql_payload)
    if primary_component_ref:
        database_payload = dict(base_payload)
        database_payload.update(primary_component_ref)
        try:
            database_pack, raw_path = _fetch_pack(client, raw_dir, "database_component_pack", database_payload)
        except Exception as exc:
            fetch_failures["database_component_pack"] = str(exc)
            command_log.append(f"- failed optional `database_component_pack`: `{exc}`")
            database_pack = None
        else:
            raw_files.append(str(raw_path.relative_to(root)))
            command_log.append(f"- fetched `database_component_pack` -> `{raw_path.relative_to(root)}`")

        op_name = _primary_sql_op_name(slow_sql_payload)
        if op_name and database_pack is not None:
            sql_payload = dict(base_payload)
            sql_payload.update(primary_component_ref)
            sql_payload["opName"] = op_name
            try:
                sql_fact_pack, raw_path = _fetch_pack(client, raw_dir, "sql_fact_sheet", sql_payload)
            except Exception as exc:
                fetch_failures["sql_fact_sheet"] = str(exc)
                command_log.append(f"- failed optional `sql_fact_sheet`: `{exc}`")
                sql_fact_pack = None
            else:
                raw_files.append(str(raw_path.relative_to(root)))
                command_log.append(f"- fetched `sql_fact_sheet` -> `{raw_path.relative_to(root)}`")

    instance_packs: list[dict[str, Any]] = []
    for application_id in _application_ids(system_snapshot_payload):
        instance_payload = dict(base_payload)
        instance_payload["applicationId"] = application_id
        try:
            instance_pack, raw_path = _fetch_pack(client, raw_dir, "instance_analysis_pack", instance_payload)
        except Exception as exc:
            fetch_failures[f"instance_analysis_pack:{application_id}"] = str(exc)
            command_log.append(f"- failed optional `instance_analysis_pack` for `{application_id}`: `{exc}`")
            continue
        instance_packs.append(instance_pack)
        raw_files.append(str(raw_path.relative_to(root)))
        command_log.append(f"- fetched `instance_analysis_pack` -> `{raw_path.relative_to(root)}`")

    catalog = _build_object_catalog(
        fetched=fetched,
        action_facts=action_facts,
        trace_facts=trace_facts,
        database_pack=database_pack,
        sql_fact_pack=sql_fact_pack,
        instance_packs=instance_packs,
    )
    if "screenshot_index_pack" in fetched:
        screenshot_payload = fetched["screenshot_index_pack"]["payload"]
    else:
        screenshot_payload = _fallback_screenshot_payload(fetched, base_payload)
        screenshot_pack_path = raw_dir / "screenshot_index_pack.json"
        _write_json(
            screenshot_pack_path,
            {
                "pack_type": "screenshot_index_pack",
                "context": {
                    "biz_system_id": biz_system_id,
                    "time_window": {"end_time": end_time_text, "period_minutes": period_minutes},
                },
                "payload": screenshot_payload,
                "meta": {"source_mode": source_mode, "build_stats": {"fallback_generated": True}},
            },
        )
        fetched["screenshot_index_pack"] = {"payload": screenshot_payload}
        raw_files.append(str(screenshot_pack_path.relative_to(root)))
        command_log.append("- generated fallback `screenshot_index_pack` from locally available core packs")
    screenshot_rows = _build_screenshot_rows(screenshot_payload, catalog)
    issues = _build_issue_rows(
        fetched=fetched,
        report_fact_payload=report_fact_payload,
        action_facts=action_facts,
        trace_facts=trace_facts,
        database_pack=database_pack,
        sql_fact_pack=sql_fact_pack,
        instance_packs=instance_packs,
    )

    url_status_counts = Counter(row["url_status"] for row in screenshot_rows)
    biz_system_name = (
        report_fact_payload.get("summary", {}).get("biz_system_name")
        or system_snapshot_payload.get("biz_system", {}).get("name")
        or f"bizSystem-{biz_system_id}"
    )

    _write_json(
        internal_dir / "run_config.json",
        {
            "biz_system_id": biz_system_id,
            "biz_system_name": biz_system_name,
            "start_time": start_dt.strftime("%Y-%m-%d %H:%M"),
            "end_time": end_dt.strftime("%Y-%m-%d %H:%M"),
            "period_minutes": period_minutes,
            "source_mode": source_mode,
            "limit": limit,
            "output_dir": str(root),
            "packs_fetched": sorted(fetched),
            "fetch_failures": fetch_failures,
            "additional_pack_files": [Path(path).name for path in raw_files if "action_fact" in path or "trace_fact" in path or "instance_analysis" in path],
        },
    )
    _write_json(
        internal_dir / "client_meta.json",
        {
            "healthz": healthz,
            "meta": meta,
            "pack_availability": {pack_type: pack_type in set(meta.get("pack_types") or []) for pack_type in CORE_PACK_TYPES},
            "fetch_failures": fetch_failures,
            "generated_raw_files": raw_files,
            "url_status_summary": dict(url_status_counts),
        },
    )
    _write_text(internal_dir / "command_log.md", "\n".join(command_log) + "\n")
    _write_json(
        internal_dir / "internal_map.json",
        {
            "raw_files": raw_files,
            "fetch_failures": fetch_failures,
            "section_files": {
                "overview": ["02_sections/overview.md", "04_raw/report_fact_pack.json", "04_raw/system_snapshot.json"],
                "system_overview": ["02_sections/system_overview.md", "04_raw/topology_dependency_pack.json", "04_raw/external_dependency_pack.json"],
                "application": ["02_sections/application.md"] + [f"04_raw/{Path(item).name}" for item in raw_files if "instance_analysis_" in item],
                "interface": ["02_sections/interface.md"] + [f"04_raw/{Path(item).name}" for item in raw_files if "action_fact_" in item],
                "sql": ["02_sections/sql.md"] + [f"04_raw/{Path(item).name}" for item in raw_files if "database_component_" in item or "sql_fact_sheet" in item or "slow_sql_pack" in item],
                "trace_cases": ["02_sections/trace_cases.md"] + [f"04_raw/{Path(item).name}" for item in raw_files if "trace_fact_" in item],
                "page": ["02_sections/page.md", "04_raw/page_experience_pack.json", "04_raw/screenshot_index_pack.json"],
            },
            "issue_files": ["03_issues/issues.csv", "03_issues/recommendations.md"],
            "knowledge_files": [
                "05_knowledge/knowledge_context.md",
                "05_knowledge/proposal_summary.md",
                "05_knowledge/judgment_notes.md",
            ],
        },
    )

    _write_text(
        foundation_dir / "scope.md",
        _build_scope_markdown(
            biz_system_name=biz_system_name,
            biz_system_id=biz_system_id,
            start_dt=start_dt,
            end_dt=end_dt,
            period_minutes=period_minutes,
            source_mode=source_mode,
            fetched=fetched,
            fetch_failures=fetch_failures,
        ),
    )
    _write_text(
        foundation_dir / "capability_boundary.md",
        _build_capability_boundary_markdown(
            fetched=fetched,
            url_status_counts=url_status_counts,
        ),
    )
    _write_csv(
        foundation_dir / "screenshot_index.csv",
        [
            "section",
            "object_type",
            "object_name",
            "page_type",
            "url_status",
            "direct_url",
            "fallback_url",
            "navigation_path",
            "url_source",
            "suggested_capture",
            "suggested_annotation",
            "why_relevant",
            "evidence_linkage",
            "priority",
        ],
        screenshot_rows,
    )

    _write_text(
        sections_dir / "overview.md",
        _build_overview_markdown(
            biz_system_name=biz_system_name,
            biz_system_id=biz_system_id,
            start_dt=start_dt,
            end_dt=end_dt,
            report_fact_payload=report_fact_payload,
            issues=issues,
        ),
    )
    _write_text(
        sections_dir / "system_overview.md",
        _build_system_overview_markdown(
            system_snapshot_payload=system_snapshot_payload,
            topology_payload=fetched["topology_dependency_pack"]["payload"],
            external_payload=fetched["external_dependency_pack"]["payload"],
            issues=issues,
        ),
    )
    _write_text(
        sections_dir / "application.md",
        _build_application_markdown(instance_packs=instance_packs, issues=issues),
    )
    _write_text(
        sections_dir / "interface.md",
        _build_interface_markdown(action_facts=action_facts, trace_facts=trace_facts, report_fact_payload=report_fact_payload, issues=issues),
    )
    _write_text(
        sections_dir / "sql.md",
        _build_sql_markdown(
            slow_sql_payload=slow_sql_payload,
            database_pack=database_pack,
            sql_fact_pack=sql_fact_pack,
            trace_facts=trace_facts,
            issues=issues,
        ),
    )
    _write_text(
        sections_dir / "trace_cases.md",
        _build_trace_cases_markdown(trace_facts=trace_facts, report_fact_payload=report_fact_payload, issues=issues),
    )
    _write_text(
        sections_dir / "page.md",
        _build_page_markdown(page_payload=fetched["page_experience_pack"]["payload"], issues=issues),
    )

    _write_csv(
        issues_dir / "issues.csv",
        [
            "issue_id",
            "canonical_issue_key",
            "primary_section",
            "duplicate_of",
            "evidence_role",
            "title",
            "display_name",
            "raw_name",
            "short_name",
            "naming_consistency",
            "naming_review_required",
            "naming_review_reason",
            "symptom",
            "impact",
            "evidence_chain",
            "suspected_root_cause",
            "scope",
            "priority_candidate",
            "owner_candidate",
            "verification_hint",
        ],
        issues,
    )
    _write_text(issues_dir / "recommendations.md", _build_recommendations_markdown(issues))

    knowledge_payload = fetched["knowledge_context_pack"]["payload"]
    _write_text(knowledge_dir / "knowledge_context.md", _build_knowledge_context_markdown(knowledge_payload))
    _write_text(knowledge_dir / "proposal_summary.md", _build_proposal_summary_markdown(knowledge_payload))
    _write_text(knowledge_dir / "judgment_notes.md", _build_judgment_notes_markdown(knowledge_payload, issues))

    _write_text(
        root / "README.md",
        _build_root_readme(
            biz_system_name=biz_system_name,
            biz_system_id=biz_system_id,
            start_dt=start_dt,
            end_dt=end_dt,
            fetched=fetched,
            issues=issues,
            url_status_counts=url_status_counts,
            raw_files=raw_files,
            fetch_failures=fetch_failures,
        ),
    )

    return {
        "output_dir": str(root),
        "biz_system_id": biz_system_id,
        "biz_system_name": biz_system_name,
        "start_time": start_dt.strftime("%Y-%m-%d %H:%M"),
        "end_time": end_dt.strftime("%Y-%m-%d %H:%M"),
        "period_minutes": period_minutes,
        "source_mode": source_mode,
        "issue_count": len(issues),
        "screenshot_row_count": len(screenshot_rows),
        "raw_file_count": len(raw_files),
        "knowledge_proposals_generated": False,
        "url_status_summary": dict(url_status_counts),
        "fetch_failures": fetch_failures,
    }


def _fetch_pack(
    client: AdapterRemoteClient,
    raw_dir: Path,
    pack_type: str,
    payload: dict[str, Any],
) -> tuple[dict[str, Any], Path]:
    raw_path = raw_dir / _planned_raw_file_name(pack_type, payload)
    try:
        pack = client.build_pack(pack_type, payload)
    except Exception:
        cached = _load_cached_pack(raw_path, payload)
        if cached is not None:
            return cached, raw_path
        raise
    raw_path = raw_dir / _raw_file_name(pack_type, pack)
    _write_json(raw_path, pack)
    return pack, raw_path


def _planned_raw_file_name(pack_type: str, payload: dict[str, Any]) -> str:
    if pack_type == "action_fact_sheet":
        return f"action_fact_{payload.get('applicationId')}_{payload.get('actionId')}.json"
    if pack_type == "trace_fact_sheet":
        return f"trace_fact_{payload.get('traceId')}.json"
    if pack_type == "database_component_pack":
        return f"database_component_{_safe_slug(payload.get('componentName') or 'component')}.json"
    if pack_type == "instance_analysis_pack":
        return f"instance_analysis_{payload.get('applicationId')}.json"
    if pack_type == "sql_fact_sheet":
        return "sql_fact_sheet_primary.json"
    return f"{pack_type}.json"


def _load_cached_pack(raw_path: Path, payload: dict[str, Any]) -> dict[str, Any] | None:
    if not raw_path.exists():
        return None
    try:
        pack = json.loads(raw_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    context = pack.get("context") or {}
    time_window = context.get("time_window") or {}
    if int(context.get("biz_system_id") or 0) != int(payload.get("bizSystemId") or 0):
        return None
    if str(time_window.get("end_time") or "") != str(payload.get("endTime") or ""):
        return None
    if int(time_window.get("period_minutes") or 0) != int(payload.get("periodMinutes") or 0):
        return None
    source_mode = ((pack.get("meta") or {}).get("source_mode") or "").lower()
    if payload.get("sourceMode") and source_mode and str(payload.get("sourceMode")).lower() != source_mode:
        return None
    return pack


def _raw_file_name(pack_type: str, pack: dict[str, Any]) -> str:
    payload = pack.get("payload") or {}
    if pack_type == "action_fact_sheet":
        action_ref = payload.get("action_ref") or {}
        return f"action_fact_{action_ref.get('application_id')}_{action_ref.get('action_id')}.json"
    if pack_type == "trace_fact_sheet":
        selector = payload.get("selector") or {}
        return f"trace_fact_{selector.get('trace_id_numeric')}.json"
    if pack_type == "database_component_pack":
        component = payload.get("component") or {}
        return f"database_component_{_safe_slug(component.get('name') or component.get('component_name') or 'component')}.json"
    if pack_type == "instance_analysis_pack":
        application = payload.get("application") or {}
        return f"instance_analysis_{application.get('id') or application.get('application_id') or application.get('applicationId')}.json"
    if pack_type == "sql_fact_sheet":
        return "sql_fact_sheet_primary.json"
    return f"{pack_type}.json"


def _parse_user_time(value: str, *, end_of_day: bool) -> datetime:
    text = value.strip()
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            parsed = datetime.strptime(text, fmt)
        except ValueError:
            continue
        if fmt == "%Y-%m-%d":
            if end_of_day:
                return parsed.replace(hour=23, minute=59)
            return parsed.replace(hour=0, minute=0)
        return parsed
    raise RuntimeError(f"Unsupported time format: {value}")


def _select_focus_action_refs(report_fact_payload: dict[str, Any], limit: int) -> list[dict[str, Any]]:
    rows = report_fact_payload.get("hotspots", {}).get("actions") or []
    selected: list[dict[str, Any]] = []
    seen: set[tuple[int, int]] = set()
    for row in rows:
        action = row.get("action") or {}
        key = (int(action.get("application_id") or 0), int(action.get("id") or 0))
        if key in seen or key == (0, 0):
            continue
        seen.add(key)
        selected.append(
            {
                "application_id": key[0],
                "action_id": key[1],
                "action_type": str(action.get("type") or "TX"),
            }
        )
        if len(selected) >= limit:
            break
    return selected


def _first_trace_selector(action_payload: dict[str, Any]) -> dict[str, Any] | None:
    candidates = action_payload.get("trace_candidates") or []
    return candidates[0] if candidates else None


def _primary_database_component_ref(slow_sql_payload: dict[str, Any]) -> dict[str, Any] | None:
    sql = (slow_sql_payload.get("top_sqls") or [None])[0] or {}
    component_name = sql.get("component_name") or sql.get("componentName")
    if not component_name:
        return None
    return {
        "componentName": component_name,
        "componentSubtype": sql.get("component_subtype") or sql.get("componentSubtype"),
    }


def _primary_sql_op_name(slow_sql_payload: dict[str, Any]) -> str | None:
    sql = (slow_sql_payload.get("top_sqls") or [None])[0] or {}
    return sql.get("op_name_decoded") or sql.get("opName") or sql.get("op_name_raw")


def _application_ids(system_snapshot_payload: dict[str, Any]) -> list[int]:
    biz_system = system_snapshot_payload.get("biz_system") or {}
    applications = biz_system.get("applications") or []
    return [int(item) for item in applications if item is not None]


def _build_object_catalog(
    *,
    fetched: dict[str, dict[str, Any]],
    action_facts: list[dict[str, Any]],
    trace_facts: list[dict[str, Any]],
    database_pack: dict[str, Any] | None,
    sql_fact_pack: dict[str, Any] | None,
    instance_packs: list[dict[str, Any]],
) -> dict[str, Any]:
    actions: dict[tuple[int, int], dict[str, Any]] = {}
    for pack in action_facts:
        payload = pack.get("payload") or {}
        action = payload.get("action") or {}
        detail = _action_identity(action, _trace_uri_for_action(action, trace_facts))
        actions[(int(action.get("application_id") or 0), int(action.get("id") or 0))] = detail

    instances: dict[int, dict[str, Any]] = {}
    for pack in instance_packs:
        payload = pack.get("payload") or {}
        application = payload.get("application") or {}
        selected = payload.get("selected_instance") or {}
        instances[int(application.get("id") or 0)] = {
            "display_name": selected.get("name") or selected.get("instanceName") or application.get("name"),
            "raw_name": selected.get("name") or selected.get("instanceName"),
            "short_name": selected.get("name") or selected.get("instanceName"),
            "object_type": "instance",
        }

    sql_entry: dict[str, Any] | None = None
    if sql_fact_pack:
        sql_payload = sql_fact_pack.get("payload") or {}
        sql = sql_payload.get("sql") or {}
        sql_text = sql.get("op_name_decoded") or sql.get("opName") or sql.get("sql_text")
        sql_entry = {
            "display_name": _sql_display_name(sql_text),
            "raw_name": sql_text,
            "short_name": _sql_display_name(sql_text),
            "object_type": "sql",
        }

    dependency_catalog: dict[str, dict[str, Any]] = {}
    external_payload = fetched["external_dependency_pack"]["payload"]
    for dep in external_payload.get("external_dependencies") or []:
        node_id = str(dep.get("node_id") or dep.get("protocol") or "external_dependency")
        protocol = str(dep.get("protocol") or "").lower()
        dependency_catalog[node_id] = {
            "display_name": f"外部依赖 {protocol or node_id}",
            "raw_name": node_id,
            "short_name": protocol or node_id,
            "object_type": "external_dependency",
        }

    return {
        "actions": actions,
        "instances": instances,
        "sql": sql_entry,
        "dependencies": dependency_catalog,
    }


def _trace_uri_for_action(action: dict[str, Any], trace_facts: list[dict[str, Any]]) -> str | None:
    for pack in trace_facts:
        payload = pack.get("payload") or {}
        detail = payload.get("detail_summary") or {}
        if int(detail.get("applicationId") or 0) == int(action.get("application_id") or 0) and int(detail.get("actionId") or 0) == int(action.get("id") or 0):
            return detail.get("uri")
    return None


def _action_identity(action: dict[str, Any], trace_uri: str | None) -> dict[str, Any]:
    raw_name = str(action.get("name") or "")
    route = raw_name[4:] if raw_name.startswith("URI/") else (trace_uri or raw_name)
    short_name = _route_short_name(route)
    if short_name.endswith(".dwr"):
        display_name = f"DWR 接口 {short_name}"
    elif short_name == "upload":
        display_name = "上传接口 upload"
    elif short_name:
        display_name = f"接口 {short_name}" if route.startswith("/") else f"事务 {short_name}"
    else:
        display_name = raw_name
    naming_consistency = "aligned"
    naming_review_required = False
    naming_review_reason = ""
    if trace_uri and not raw_name.startswith("URI/"):
        naming_consistency = "conflict"
        naming_review_required = True
        naming_review_reason = "action_name_uri_mismatch"
        display_name = f"事务 {short_name or raw_name}（URI待复核）"
    return {
        "display_name": display_name,
        "raw_name": raw_name,
        "short_name": short_name or raw_name,
        "route_suffix": short_name,
        "naming_consistency": naming_consistency,
        "naming_review_required": naming_review_required,
        "naming_review_reason": naming_review_reason,
        "object_type": "action",
    }


def _route_short_name(route: str) -> str:
    text = str(route or "").strip("/")
    if not text:
        return ""
    return text.split("/")[-1]


def _sql_display_name(sql_text: str | None) -> str:
    text = str(sql_text or "").strip()
    if not text:
        return "SQL"
    compact = " ".join(text.split())
    return compact[:80] + ("..." if len(compact) > 80 else "")


def _build_screenshot_rows(screenshot_payload: dict[str, Any], catalog: dict[str, Any]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    page_links = screenshot_payload.get("page_links") or []
    for card in screenshot_payload.get("screenshot_cards") or []:
        link = _merge_card_link(card, _best_page_link(card, page_links))
        target_ref = card.get("target_ref") or {}
        object_info = _object_info_from_target(target_ref, catalog)
        rows.append(
            {
                "section": SECTION_PAGE_TYPE_MAP.get(str(card.get("page_type") or ""), "overview"),
                "object_type": object_info.get("object_type") or str(target_ref.get("kind") or "object"),
                "object_name": object_info.get("display_name") or str(card.get("title") or "对象"),
                "page_type": str(card.get("page_type") or ""),
                "url_status": str(link["url_status"]),
                "direct_url": str(link["direct_url"] or ""),
                "fallback_url": str(link["fallback_url"] or ""),
                "navigation_path": " > ".join(str(item) for item in (link["navigation_path"] or [])),
                "url_source": str(link["url_source"] or ""),
                "suggested_capture": ";".join(str(item) for item in (card.get("recommended_capture") or [])),
                "suggested_annotation": ";".join(str(item) for item in (card.get("recommended_annotations") or [])),
                "why_relevant": str(card.get("why_relevant") or card.get("usage_in_report") or ""),
                "evidence_linkage": f"{card.get('figure_id')} -> {card.get('suggested_report_section') or card.get('page_type')}",
                "priority": str(card.get("priority") or "medium"),
            }
        )
    return rows


def _fallback_screenshot_payload(fetched: dict[str, dict[str, Any]], base_payload: dict[str, Any]) -> dict[str, Any]:
    screenshot_cards: list[dict[str, Any]] = []
    page_links: list[dict[str, Any]] = []
    seen_cards: set[tuple[str, str]] = set()
    for pack_type in ("system_snapshot", "report_fact_pack", "page_experience_pack", "slow_sql_pack", "topology_dependency_pack", "external_dependency_pack"):
        payload = (fetched.get(pack_type) or {}).get("payload") or {}
        page_links.extend(payload.get("page_links") or [])
        for index, hint in enumerate(payload.get("screenshot_hints") or [], start=1):
            key = (str(hint.get("title") or ""), str(hint.get("url") or ""))
            if key in seen_cards:
                continue
            seen_cards.add(key)
            screenshot_cards.append(
                {
                    "figure_id": f"FIG-{len(screenshot_cards) + 1:02d}",
                    "title": hint.get("title"),
                    "page_type": hint.get("page_type"),
                    "url": hint.get("url"),
                    "recommended_capture": hint.get("recommended_capture") or [],
                    "recommended_annotations": hint.get("recommended_annotations") or [],
                    "usage_in_report": hint.get("usage_in_report"),
                    "suggested_report_section": hint.get("suggested_report_section"),
                    "priority": hint.get("priority", "medium"),
                    "target_ref": hint.get("target_ref") or {},
                }
            )
    return {
        "scope": {
            "bizSystemId": base_payload.get("bizSystemId"),
            "endTime": base_payload.get("endTime"),
            "periodMinutes": base_payload.get("periodMinutes"),
            "sourceMode": base_payload.get("sourceMode"),
            "limit": base_payload.get("limit"),
        },
        "screenshot_cards": screenshot_cards,
        "page_links": page_links,
        "primary_console_url": next((link.get("url") for link in page_links if link.get("url")), None),
        "related_console_urls": [link.get("url") for link in page_links if link.get("url")],
        "coverage_boundary": {},
        "evidence_linkage": {},
        "input_dependencies": [name for name in fetched if name != "screenshot_index_pack"],
        "derivation_notes": ["Fallback screenshot index generated locally because remote screenshot_index_pack was unavailable."],
        "evidence": [],
    }


def _build_issue_rows(
    *,
    fetched: dict[str, dict[str, Any]],
    report_fact_payload: dict[str, Any],
    action_facts: list[dict[str, Any]],
    trace_facts: list[dict[str, Any]],
    database_pack: dict[str, Any] | None,
    sql_fact_pack: dict[str, Any] | None,
    instance_packs: list[dict[str, Any]],
) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    issues.extend(_build_upload_issue_rows(action_facts, trace_facts, report_fact_payload))
    issues.extend(_build_dwr_issue_rows(action_facts, trace_facts, database_pack, sql_fact_pack, report_fact_payload))
    issues.extend(_build_naming_issue_rows(action_facts, trace_facts, report_fact_payload))
    issues.extend(_build_external_dependency_issue_rows(fetched["external_dependency_pack"]["payload"]))
    issues.extend(_build_observability_issue_rows(fetched["page_experience_pack"]["payload"], instance_packs))
    for index, issue in enumerate(issues, start=1):
        issue["issue_id"] = f"ISS-{index:03d}"
    return issues


def _build_upload_issue_rows(action_facts: list[dict[str, Any]], trace_facts: list[dict[str, Any]], report_fact_payload: dict[str, Any]) -> list[dict[str, str]]:
    candidates = []
    for pack in action_facts:
        payload = pack.get("payload") or {}
        action = payload.get("action") or {}
        identity = _action_identity(action, _trace_uri_for_action(action, trace_facts))
        if identity["short_name"] != "upload":
            continue
        metrics = action.get("metrics") or {}
        candidates.append((pack, identity, metrics, False))
    if not candidates:
        for row in report_fact_payload.get("hotspots", {}).get("actions") or []:
            action = row.get("action") or {}
            identity = _action_identity(action, None)
            if identity["short_name"] != "upload":
                continue
            candidates.append(({"payload": {"action": action, "action_ref": {"application_id": action.get("application_id"), "action_id": action.get("id")}}}, identity, action.get("metrics") or {}, True))
    if not candidates:
        return []
    candidates.sort(key=lambda item: (_as_float(item[2].get("error_count")), _as_float(item[2].get("response_time_ms"))), reverse=True)
    pack, identity, metrics, is_fallback = candidates[0]
    trace_pack = _trace_for_action(pack, trace_facts)
    problems = _suspected_problem_names(trace_pack)
    root_cause = "认证/过滤器链路阻塞或异常包装放大了上传失败。" if any("CwSSOFilter" in item for item in problems) else "上传入口存在高错误和长耗时，需要结合 trace 继续核对过滤器、依赖与异常链。"
    applications = sorted({str((item[0].get("payload") or {}).get("action", {}).get("application_id")) for item in candidates})
    evidence_chain = _evidence_chain("report_fact_pack.json", "page_experience_pack.json") if is_fallback else _evidence_chain(_raw_file_name("action_fact_sheet", pack), _trace_file_name(trace_pack), "page_experience_pack.json")
    return [
        _issue_row(
            canonical_issue_key="upload_chain_failure",
            primary_section="interface",
            title="上传链路失败且耗时过长",
            identity=identity,
            symptom=f"重点上传 action 平均响应 {_fmt_ms(metrics.get('response_time_ms'))}，错误数 {_fmt_int(metrics.get('error_count'))}，调用数 {_fmt_int(metrics.get('count'))}。",
            impact="直接影响上传相关用户功能可用性，并会在页面代理视图里放大为慢路由。",
            evidence_chain=evidence_chain,
            suspected_root_cause=root_cause,
            scope=f"applications {', '.join(applications)} / route {identity['raw_name']}",
            priority_candidate="P0",
            owner_candidate="应用开发/认证与会话链路负责人",
            verification_hint="补抓 upload 入口分段耗时，核对过滤器链、单点登录和 Redis/会话依赖超时。",
        )
    ]


def _build_dwr_issue_rows(
    action_facts: list[dict[str, Any]],
    trace_facts: list[dict[str, Any]],
    database_pack: dict[str, Any] | None,
    sql_fact_pack: dict[str, Any] | None,
    report_fact_payload: dict[str, Any],
) -> list[dict[str, str]]:
    candidates = []
    for pack in action_facts:
        payload = pack.get("payload") or {}
        action = payload.get("action") or {}
        identity = _action_identity(action, _trace_uri_for_action(action, trace_facts))
        if "lawyerEorkTimeTop10Data.dwr" not in identity["raw_name"]:
            continue
        candidates.append((pack, identity, action.get("metrics") or {}, False))
    if not candidates:
        for row in report_fact_payload.get("hotspots", {}).get("actions") or []:
            action = row.get("action") or {}
            identity = _action_identity(action, None)
            if "lawyerEorkTimeTop10Data.dwr" not in identity["raw_name"]:
                continue
            candidates.append(({"payload": {"action": action, "action_ref": {"application_id": action.get("application_id"), "action_id": action.get("id")}}}, identity, action.get("metrics") or {}, True))
    if not candidates:
        return []
    candidates.sort(key=lambda item: _as_float(item[2].get("response_time_ms")), reverse=True)
    pack, identity, metrics, is_fallback = candidates[0]
    trace_pack = _trace_for_action(pack, trace_facts)
    db_detail = ""
    if database_pack:
        db_component = (database_pack.get("payload") or {}).get("component") or {}
        db_detail = str(db_component.get("name") or db_component.get("component_name") or "")
    sql_detail = ""
    if sql_fact_pack:
        sql = (sql_fact_pack.get("payload") or {}).get("sql") or {}
        sql_detail = _sql_display_name(sql.get("op_name_decoded") or sql.get("opName"))
    symptom = f"DWR 平均响应 {_fmt_ms(metrics.get('response_time_ms'))}，主 trace 出现数据库独占长耗时。"
    if sql_detail:
        symptom += f" 重点 SQL: {sql_detail}。"
    evidence_parts = ["report_fact_pack.json"] if is_fallback else [_raw_file_name("action_fact_sheet", pack), _trace_file_name(trace_pack)]
    if database_pack:
        evidence_parts.append(_raw_file_name("database_component_pack", database_pack))
    if sql_fact_pack:
        evidence_parts.append(_raw_file_name("sql_fact_sheet", sql_fact_pack))
    return [
        _issue_row(
            canonical_issue_key="dwr_minute_level_database_wait",
            primary_section="sql",
            title="DWR 分钟级数据库等待",
            identity=identity,
            symptom=symptom,
            impact="跨应用复现的 DWR 长尾会直接拖慢法务查询/统计类页面与接口。",
            evidence_chain=_evidence_chain(*evidence_parts),
            suspected_root_cause=f"数据库组件 {db_detail or 'MySQL'} 与重点 SQL 同时出现高耗时，优先怀疑执行计划、索引或数据量退化。",
            scope=f"cross-application route {identity['raw_name']}",
            priority_candidate="P1",
            owner_candidate="应用开发/DBA",
            verification_hint="补核 trace 对 SQL 的一一绑定、执行计划和高峰时段数据量变化。",
        )
    ]


def _build_naming_issue_rows(action_facts: list[dict[str, Any]], trace_facts: list[dict[str, Any]], report_fact_payload: dict[str, Any]) -> list[dict[str, str]]:
    for pack in action_facts:
        payload = pack.get("payload") or {}
        action = payload.get("action") or {}
        trace_pack = _trace_for_action(pack, trace_facts)
        trace_uri = _detail_summary(trace_pack).get("uri")
        identity = _action_identity(action, trace_uri)
        if identity["naming_consistency"] != "conflict":
            continue
        return [
            _issue_row(
                canonical_issue_key="transaction_name_uri_mismatch",
                primary_section="interface",
                title="事务命名与真实 URI 不一致",
                identity=identity,
                symptom=f"action 名为 `{identity['raw_name']}`，但代表性 trace 真实 URI 为 `{trace_uri}`。",
                impact="会污染热点、trace 与治理对象命名，正式报告中需要单独标注命名冲突。",
                evidence_chain=_evidence_chain(_raw_file_name('action_fact_sheet', pack), _trace_file_name(trace_pack)),
                suspected_root_cause="事务命名被框架方法或初始化阶段方法覆盖，没有稳定落到真实用户 URI。",
                scope=f"application {(action.get('application_id') or '')} / action {(action.get('id') or '')}",
                priority_candidate="P1",
                owner_candidate="应用开发/框架治理",
                verification_hint="核对事务命名规则、首请求初始化逻辑和 URI 归一化策略。",
            )
        ]
    for row in report_fact_payload.get("hotspots", {}).get("actions") or []:
        action = row.get("action") or {}
        identity = _action_identity(action, None)
        if identity["raw_name"].startswith("URI/"):
            continue
        return [
            _issue_row(
                canonical_issue_key="transaction_name_uri_mismatch",
                primary_section="interface",
                title="事务命名与真实 URI 不一致",
                identity=identity,
                symptom=f"热点对象 `{identity['raw_name']}` 不是 URI 风格命名，当前需要进一步核对其真实业务路由。",
                impact="会污染热点、trace 与治理对象命名，正式报告中需要单独标注命名冲突。",
                evidence_chain=_evidence_chain("report_fact_pack.json"),
                suspected_root_cause="事务命名被框架方法或初始化阶段方法覆盖，没有稳定落到真实用户 URI。",
                scope=f"application {(action.get('application_id') or '')} / action {(action.get('id') or '')}",
                priority_candidate="P1",
                owner_candidate="应用开发/框架治理",
                verification_hint="待远端 trace 详情恢复后补抓代表性 trace，核对 URI 归一化策略。",
            )
        ]
    return []


def _build_external_dependency_issue_rows(external_payload: dict[str, Any]) -> list[dict[str, str]]:
    candidates = []
    for dep in external_payload.get("external_dependencies") or []:
        protocol = str(dep.get("protocol") or "").lower()
        if protocol not in {"http", "https"}:
            continue
        candidates.append(dep)
    if not candidates:
        return []
    candidates.sort(key=lambda item: (_as_float(item.get("avg_response_time_ms")), _as_float(item.get("error_rate"))), reverse=True)
    dep = candidates[0]
    raw_name = str(dep.get("node_id") or dep.get("protocol") or "external_dependency")
    identity = {
        "display_name": f"外部依赖 {dep.get('protocol')}",
        "raw_name": raw_name,
        "short_name": str(dep.get("protocol") or raw_name),
        "naming_consistency": "",
        "naming_review_required": False,
        "naming_review_reason": "",
    }
    return [
        _issue_row(
            canonical_issue_key="shared_http_dependency_high_latency_error",
            primary_section="system_overview",
            title="跨应用共享 HTTP 外部依赖高时延/高错误",
            identity=identity,
            symptom=f"协议 {dep.get('protocol')} 平均响应 {_fmt_ms(dep.get('avg_response_time_ms') or dep.get('response_time_ms'))}，错误率 {_fmt_rate(dep.get('error_rate'))}，上游节点数 {_fmt_int(dep.get('upstream_node_count') or len(dep.get('upstream_nodes') or []))}。",
            impact="会跨应用放大用户入口的时延和失败风险，且责任边界可能跨系统。",
            evidence_chain=_evidence_chain("external_dependency_pack.json", "topology_dependency_pack.json"),
            suspected_root_cause="下游 HTTP 服务性能差、重试/超时不合理，或依赖映射仍未补全。",
            scope=f"shared dependency {raw_name}",
            priority_candidate="P2",
            owner_candidate="集成/中间件/网络协同",
            verification_hint="补充真实目标系统映射，核对超时、重试、熔断和错误码分布。",
        )
    ]


def _build_observability_issue_rows(page_payload: dict[str, Any], instance_packs: list[dict[str, Any]]) -> list[dict[str, str]]:
    missing_items = set(page_payload.get("coverage_boundary", {}).get("page_experience", {}).get("missing_evidence") or [])
    jvm_missing = 0
    for pack in instance_packs:
        jvm_chart = (pack.get("payload") or {}).get("jvm_chart") or {}
        if int(jvm_chart.get("point_count") or 0) == 0:
            jvm_missing += 1
    if not missing_items and not jvm_missing:
        return []
    jvm_text = str(jvm_missing) if instance_packs else "当前未拉取实例分析包"
    identity = {
        "display_name": "页面/JVM 观测空洞",
        "raw_name": "page_and_jvm_observability_gap",
        "short_name": "observability_gap",
        "naming_consistency": "",
        "naming_review_required": False,
        "naming_review_reason": "",
    }
    return [
        _issue_row(
            canonical_issue_key="observability_gap_page_and_jvm",
            primary_section="application",
            title="页面与 JVM 观测存在空洞",
            identity=identity,
            symptom=f"页面侧缺少 {', '.join(sorted(missing_items)) or '关键 RUM 指标'}；JVM 图空缺情况 {jvm_text}。",
            impact="会降低应用与页面章节的归因置信度，只能输出保守结论。",
            evidence_chain=_evidence_chain("page_experience_pack.json", "instance_analysis_*.json"),
            suspected_root_cause="页面侧埋点或 JVM 采集未开启，或当前 adapter 尚未暴露对应能力。",
            scope="all applications / page chapter",
            priority_candidate="P2",
            owner_candidate="APM 平台/SRE",
            verification_hint="补齐页面侧埋点和 JVM 采集，再回收集同一时间窗的数据。",
        )
    ]


def _issue_row(
    *,
    canonical_issue_key: str,
    primary_section: str,
    title: str,
    identity: dict[str, Any],
    symptom: str,
    impact: str,
    evidence_chain: str,
    suspected_root_cause: str,
    scope: str,
    priority_candidate: str,
    owner_candidate: str,
    verification_hint: str,
) -> dict[str, str]:
    return {
        "issue_id": "",
        "canonical_issue_key": canonical_issue_key,
        "primary_section": primary_section,
        "duplicate_of": "",
        "evidence_role": "primary",
        "title": title,
        "display_name": str(identity.get("display_name") or ""),
        "raw_name": str(identity.get("raw_name") or ""),
        "short_name": str(identity.get("short_name") or ""),
        "naming_consistency": str(identity.get("naming_consistency") or ""),
        "naming_review_required": str(bool(identity.get("naming_review_required"))).lower(),
        "naming_review_reason": str(identity.get("naming_review_reason") or ""),
        "symptom": symptom,
        "impact": impact,
        "evidence_chain": evidence_chain,
        "suspected_root_cause": suspected_root_cause,
        "scope": scope,
        "priority_candidate": priority_candidate,
        "owner_candidate": owner_candidate,
        "verification_hint": verification_hint,
    }


def _trace_for_action(action_pack: dict[str, Any], trace_facts: list[dict[str, Any]]) -> dict[str, Any] | None:
    payload = action_pack.get("payload") or {}
    action_ref = payload.get("action_ref") or {}
    for pack in trace_facts:
        detail = _detail_summary(pack)
        if int(detail.get("applicationId") or 0) == int(action_ref.get("application_id") or 0) and int(detail.get("actionId") or 0) == int(action_ref.get("action_id") or 0):
            return pack
    return None


def _detail_summary(trace_pack: dict[str, Any] | None) -> dict[str, Any]:
    if not trace_pack:
        return {}
    return (trace_pack.get("payload") or {}).get("detail_summary") or {}


def _suspected_problem_names(trace_pack: dict[str, Any] | None) -> list[str]:
    trace = ((trace_pack or {}).get("payload") or {}).get("trace") or {}
    items = []
    for problem in trace.get("suspected_problems") or []:
        name = problem.get("metricName")
        if name:
            items.append(str(name))
    return items


def _best_page_link(card: dict[str, Any], page_links: list[dict[str, Any]]) -> dict[str, Any]:
    target_ref = card.get("target_ref") or {}
    page_type = card.get("page_type")
    url = card.get("url")
    best: dict[str, Any] = {}
    score = -1
    for link in page_links:
        current = 0
        if page_type and link.get("page_type") == page_type:
            current += 4
        if url and link.get("url") == url:
            current += 3
        if _target_ref_key(target_ref) and _target_ref_key(target_ref) == _target_ref_key(link.get("target_ref") or {}):
            current += 5
        if current > score:
            best = link
            score = current
    return best if score > 0 else {}


def _merge_card_link(card: dict[str, Any], page_link: dict[str, Any]) -> dict[str, Any]:
    url = card.get("url") or page_link.get("url")
    direct_url = card.get("direct_url") or page_link.get("direct_url")
    fallback_url = card.get("fallback_url") or page_link.get("fallback_url") or (url if not direct_url else None)
    url_status = card.get("url_status") or page_link.get("url_status")
    page_type = str(card.get("page_type") or page_link.get("page_type") or "")
    if direct_url and "/trace-detail/" in str(direct_url) and page_type != "trace_detail":
        fallback_url = fallback_url or url or str(direct_url)
        direct_url = None
        url_status = "navigation_only"
    if not url_status:
        if direct_url:
            url_status = "direct"
        elif fallback_url or url:
            url_status = "navigation_only"
        else:
            url_status = "unavailable"
    return {
        "url_status": url_status,
        "direct_url": direct_url,
        "fallback_url": fallback_url,
        "navigation_path": card.get("navigation_path") or page_link.get("navigation_path") or [],
        "url_source": card.get("url_source") or page_link.get("url_source") or ("fallback_root_navigation" if fallback_url else "unknown"),
    }


def _object_info_from_target(target_ref: dict[str, Any], catalog: dict[str, Any]) -> dict[str, Any]:
    kind = str(target_ref.get("kind") or "")
    if kind == "action":
        return catalog.get("actions", {}).get((int(target_ref.get("application_id") or 0), int(target_ref.get("action_id") or 0)), {})
    if kind == "instance":
        return catalog.get("instances", {}).get(int(target_ref.get("application_id") or 0), {})
    if kind == "sql" and catalog.get("sql"):
        return catalog["sql"]
    if kind == "external_dependency":
        return catalog.get("dependencies", {}).get(str(target_ref.get("node_id") or target_ref.get("protocol") or ""), {})
    if kind == "biz_system":
        return {"display_name": "集团法务", "object_type": "biz_system"}
    return {}


def _target_ref_key(target_ref: dict[str, Any]) -> tuple[tuple[str, str], ...]:
    items = []
    for key in sorted(target_ref):
        value = target_ref.get(key)
        if value is None:
            continue
        items.append((str(key), str(value)))
    return tuple(items)


def _build_scope_markdown(
    *,
    biz_system_name: str,
    biz_system_id: int,
    start_dt: datetime,
    end_dt: datetime,
    period_minutes: int,
    source_mode: str,
    fetched: dict[str, dict[str, Any]],
    fetch_failures: dict[str, str],
) -> str:
    return "\n".join(
        [
            "# Scope",
            "",
            f"- 目标业务系统：`{biz_system_name}` (`bizSystemId={biz_system_id}`)",
            f"- 时间范围：`{start_dt.strftime('%Y-%m-%d %H:%M')}` 至 `{end_dt.strftime('%Y-%m-%d %H:%M')}`",
            f"- 等效查询窗口：`periodMinutes={period_minutes}`",
            f"- 数据来源：远端 `tingyun_adapter` 服务，`sourceMode={source_mode}`",
            "- 目标：输出给上层报告生成器直接消费的中间素材，不在本层输出最终定稿报告。",
            "",
            "## 已拉取的核心 packs",
            "",
            *(f"- `{pack_type}`" for pack_type in sorted(fetched)),
            "",
            "## 未成功拉取的增强 packs",
            "",
            *(f"- `{name}`: `{reason}`" for name, reason in fetch_failures.items()),
        ]
    ) + "\n"


def _build_capability_boundary_markdown(*, fetched: dict[str, dict[str, Any]], url_status_counts: Counter[str]) -> str:
    page_payload = fetched["page_experience_pack"]["payload"]
    coverage = page_payload.get("coverage_boundary", {})
    page_boundary = coverage.get("page_experience", {})
    return "\n".join(
        [
            "# Capability Boundary",
            "",
            "## URL 能力",
            "",
            *(f"- `{status}`: {count}" for status, count in sorted(url_status_counts.items())),
            "",
            "## 页面能力边界",
            "",
            f"- status: `{page_boundary.get('status')}`",
            f"- reason: `{page_boundary.get('reason')}`",
            f"- available_evidence: `{', '.join(page_boundary.get('available_evidence') or [])}`",
            f"- missing_evidence: `{', '.join(page_boundary.get('missing_evidence') or [])}`",
            "",
            "## Knowledge 边界",
            "",
            "- confirmed knowledge 与 pending proposals 已在 `05_knowledge/` 分开输出。",
            "- 本次未自动生成新的 knowledge proposals，也没有把 proposal 直接提升为 confirmed knowledge。",
        ]
    ) + "\n"


def _build_overview_markdown(
    *,
    biz_system_name: str,
    biz_system_id: int,
    start_dt: datetime,
    end_dt: datetime,
    report_fact_payload: dict[str, Any],
    issues: list[dict[str, str]],
) -> str:
    summary = report_fact_payload.get("summary") or {}
    lines = [
        "# Overview",
        "",
        f"- 业务系统：`{biz_system_name}` (`{biz_system_id}`)",
        f"- 时间范围：`{start_dt.strftime('%Y-%m-%d')}` 至 `{end_dt.strftime('%Y-%m-%d')}`",
        f"- 平均响应：`{summary.get('avg_response_time_ms')}ms`",
        f"- 平均吞吐：`{summary.get('avg_throughput')}`",
        f"- Apdex：`{summary.get('apdex')}`",
        f"- 当前最慢热点对象：`{summary.get('top_action_name')}`",
        "",
        "## 当前主问题",
        "",
    ]
    for issue in issues:
        lines.append(f"- `{issue['priority_candidate']}` `{issue['canonical_issue_key']}`: {issue['title']}")
    return "\n".join(lines) + "\n"


def _build_system_overview_markdown(
    *,
    system_snapshot_payload: dict[str, Any],
    topology_payload: dict[str, Any],
    external_payload: dict[str, Any],
    issues: list[dict[str, str]],
) -> str:
    biz_system = system_snapshot_payload.get("biz_system") or {}
    overview = system_snapshot_payload.get("overview") or {}
    external_deps = external_payload.get("external_dependencies") or []
    lines = [
        "# System Overview",
        "",
        f"- 业务系统名：`{biz_system.get('name')}`",
        f"- 应用数：`{len(biz_system.get('applications') or [])}`",
        f"- 实例数：`{len(biz_system.get('instances') or [])}`",
        f"- 事务数：`{len(biz_system.get('actions') or [])}`",
        f"- 总体响应：`{overview.get('response') or overview.get('avg_response_time_ms')}`",
        "",
        "## 外部依赖摘要",
        "",
    ]
    for dep in external_deps[:5]:
        lines.append(
            f"- `{dep.get('protocol')}` `{dep.get('node_id')}`: avg `{_fmt_ms(dep.get('avg_response_time_ms') or dep.get('response_time_ms'))}`, errorRate `{_fmt_rate(dep.get('error_rate'))}`"
        )
    lines.extend(["", "## 主展开问题", ""])
    for issue in issues:
        if issue["primary_section"] == "system_overview":
            lines.append(f"- `{issue['canonical_issue_key']}`: {issue['symptom']}")
    lines.extend(["", "## 证据链", "", "- `system_snapshot -> topology_dependency_pack -> external_dependency_pack`"])
    return "\n".join(lines) + "\n"


def _build_application_markdown(*, instance_packs: list[dict[str, Any]], issues: list[dict[str, str]]) -> str:
    lines = ["# Application", "", "## 实例概况", ""]
    for pack in instance_packs:
        payload = pack.get("payload") or {}
        application = payload.get("application") or {}
        selected = payload.get("selected_instance") or {}
        cpu_chart = payload.get("cpu_chart") or {}
        jvm_chart = payload.get("jvm_chart") or {}
        lines.append(
            f"- 应用 `{application.get('id') or application.get('application_id')}` / 实例 `{selected.get('name') or selected.get('instanceName')}`: CPU 点数 `{cpu_chart.get('point_count', 0)}`, JVM 点数 `{jvm_chart.get('point_count', 0)}`"
        )
    lines.extend(["", "## 能力边界与问题", ""])
    for issue in issues:
        if issue["primary_section"] == "application":
            lines.append(f"- `{issue['canonical_issue_key']}`: {issue['symptom']}")
    return "\n".join(lines) + "\n"


def _build_interface_markdown(
    *,
    action_facts: list[dict[str, Any]],
    trace_facts: list[dict[str, Any]],
    report_fact_payload: dict[str, Any],
    issues: list[dict[str, str]],
) -> str:
    lines = ["# Interface", "", "## 重点接口对象", ""]
    source_rows = []
    if action_facts:
        for pack in action_facts:
            payload = pack.get("payload") or {}
            source_rows.append((payload.get("action") or {}, _detail_summary(_trace_for_action(pack, trace_facts)).get("uri")))
    else:
        for row in report_fact_payload.get("hotspots", {}).get("actions") or []:
            source_rows.append((row.get("action") or {}, None))
    for action, trace_uri in source_rows:
        identity = _action_identity(action, trace_uri)
        metrics = action.get("metrics") or {}
        lines.append(f"- display_name: `{identity['display_name']}`")
        lines.append(f"  raw_name: `{identity['raw_name']}`")
        lines.append(f"  short_name: `{identity['short_name']}`")
        lines.append(f"  avg_response: `{_fmt_ms(metrics.get('response_time_ms'))}` / error_count `{_fmt_int(metrics.get('error_count'))}` / count `{_fmt_int(metrics.get('count'))}`")
        if identity["naming_review_required"] or (trace_uri is None and not identity["raw_name"].startswith("URI/")):
            lines.append(
                f"  naming_consistency: `{identity['naming_consistency']}` / naming_review_reason: `{identity['naming_review_reason']}` / trace_uri: `{trace_uri or 'pending_trace_fetch'}`"
            )
    lines.extend(["", "## 主展开问题", ""])
    for issue in issues:
        if issue["primary_section"] == "interface":
            lines.append(f"- `{issue['canonical_issue_key']}`: {issue['symptom']}")
    lines.extend(["", "## 证据链", "", "- `report_fact_pack -> action_fact_sheet -> trace_fact_sheet`"])
    return "\n".join(lines) + "\n"


def _build_sql_markdown(
    *,
    slow_sql_payload: dict[str, Any],
    database_pack: dict[str, Any] | None,
    sql_fact_pack: dict[str, Any] | None,
    trace_facts: list[dict[str, Any]],
    issues: list[dict[str, str]],
) -> str:
    component = ((database_pack or {}).get("payload") or {}).get("component") or {}
    summary = ((database_pack or {}).get("payload") or {}).get("summary") or {}
    operation_overview = slow_sql_payload.get("operation_overview") or {}
    top_sql = (slow_sql_payload.get("top_sqls") or [None])[0] or {}
    sql_payload = (sql_fact_pack or {}).get("payload") or {}
    sql = sql_payload.get("sql") or {}
    related_actions = sql_payload.get("related_actions") or []
    dwr_trace = next((pack for pack in trace_facts if "lawyerEorkTimeTop10Data.dwr" in str(_detail_summary(pack).get("uri") or "")), None)
    caller_names = []
    for item in related_actions[:5]:
        caller_names.append(
            str(
                item.get("actionName")
                or item.get("actionAlias")
                or item.get("display_name")
                or item.get("action_id")
                or "unknown_action"
            )
        )
    lines = [
        "# SQL",
        "",
        "## 组件层",
        "",
        f"- 组件：`{component.get('name') or component.get('component_name')}`",
        f"- 平均响应：`{_fmt_ms(summary.get('avg_response_time_ms') or summary.get('response_time_ms'))}`",
        f"- 总耗时：`{_fmt_ms(summary.get('total_response_time_ms'))}`",
        f"- traceCount：`{_fmt_int(summary.get('trace_count') or summary.get('traceCount'))}`",
        "",
        "## SQL 排序层",
        "",
        f"- 组件数：`{_fmt_int(operation_overview.get('component_count'))}`",
        f"- SQL 数：`{_fmt_int(operation_overview.get('sql_count'))}`",
        f"- 高 trace SQL 数：`{_fmt_int(operation_overview.get('high_trace_sql_count'))}`",
        f"- 当前最慢 SQL：`{_sql_display_name(top_sql.get('op_name_decoded') or top_sql.get('opName'))}`",
        "",
        "## 单条 SQL 层",
        "",
        f"- SQL 文本/指纹：`{_sql_display_name(sql.get('op_name_decoded') or sql.get('opName'))}`",
        f"- 平均耗时：`{_fmt_ms(sql.get('avg_response_time_ms') or sql.get('response_time_ms'))}`",
        f"- 总耗时：`{_fmt_ms(sql.get('total_response_time_ms'))}`",
        f"- 调用次数：`{_fmt_int(sql.get('count'))}`",
        f"- traceCount：`{_fmt_int(sql.get('trace_count') or sql.get('traceCount'))}`",
        f"- 语句特征：`{', '.join(sql_payload.get('sql_features', {}).get('features') or [])}`",
        f"- 调用者：`{', '.join(caller_names)}`",
    ]
    if dwr_trace:
        detail = _detail_summary(dwr_trace)
        lines.extend(
            [
                "",
                "## Trace 绑定补强",
                "",
                f"- trace `{detail.get('requestId')}` / URI `{detail.get('uri')}` / duration `{_fmt_ms(detail.get('respTime') or detail.get('duration'))}`",
            ]
        )
    lines.extend(["", "## 主展开问题", ""])
    for issue in issues:
        if issue["primary_section"] == "sql":
            lines.append(f"- `{issue['canonical_issue_key']}`: {issue['symptom']}")
    lines.extend(["", "## 能力边界", "", "- 可确认数据库组件、SQL 排序、重点 SQL 与调用者。", "- 仍需补 trace 与单条 SQL 的一一绑定来提升结论置信度。"])
    return "\n".join(lines) + "\n"


def _build_trace_cases_markdown(*, trace_facts: list[dict[str, Any]], report_fact_payload: dict[str, Any], issues: list[dict[str, str]]) -> str:
    lines = ["# Trace Cases", "", "## 代表性 trace", ""]
    if trace_facts:
        source_rows = [(_detail_summary(pack), ((pack.get("payload") or {}).get("trace") or {})) for pack in trace_facts]
    else:
        trace_case = report_fact_payload.get("trace_case") or {}
        source_rows = []
        if trace_case:
            source_rows.append((trace_case.get("detail_summary") or {}, trace_case.get("trace") or {}))
    for detail, trace in source_rows:
        suspect_names = [str(item.get("metricName")) for item in (trace.get("suspected_problems") or []) if item.get("metricName")]
        lines.append(
            f"- trace `{detail.get('requestId')}` / action `{detail.get('actionName')}` / URI `{detail.get('uri')}` / duration `{_fmt_ms(detail.get('respTime') or detail.get('duration'))}` / suspect `{', '.join(suspect_names[:3])}`"
        )
        if trace.get("status"):
            lines.append(f"  status: `{trace.get('status')}`")
    lines.extend(["", "## 命名冲突与下钻提示", ""])
    for issue in issues:
        if issue["canonical_issue_key"] == "transaction_name_uri_mismatch":
            lines.append(f"- `{issue['symptom']}`")
    return "\n".join(lines) + "\n"


def _build_page_markdown(*, page_payload: dict[str, Any], issues: list[dict[str, str]]) -> str:
    summary = page_payload.get("performance_summary") or {}
    coverage = page_payload.get("coverage_boundary", {}).get("page_experience", {})
    lines = [
        "# Page",
        "",
        "## 页面章节类型",
        "",
        "- 本章节仅输出页面代理证据，不是前端 RUM 真实页面指标。",
        f"- status: `{coverage.get('status')}`",
        f"- reason: `{coverage.get('reason')}`",
        "",
        "## 代理页面对象摘要",
        "",
        f"- page_count: `{_fmt_int(summary.get('page_count'))}`",
        f"- user_entry_count: `{_fmt_int(summary.get('user_entry_count'))}`",
        f"- max_user_entry_response_ms: `{_fmt_ms(summary.get('max_user_entry_response_ms'))}`",
        f"- max_page_response_ms: `{_fmt_ms(summary.get('max_page_response_ms'))}`",
        "",
        "## 章节限制",
        "",
        "- 不得写成真实慢页面占比、JS 错误、浏览器/地域分布、首屏时间或完全加载时间。",
    ]
    for issue in issues:
        if issue["canonical_issue_key"] in {"upload_chain_failure", "dwr_minute_level_database_wait"}:
            lines.append(f"- supporting issue `{issue['canonical_issue_key']}`: `{issue['display_name']}`")
    return "\n".join(lines) + "\n"


def _build_recommendations_markdown(issues: list[dict[str, str]]) -> str:
    lines = ["# Recommendations", ""]
    for issue in issues:
        lines.append(f"- `{issue['canonical_issue_key']}` / `{issue['priority_candidate']}`: {issue['verification_hint']}")
    return "\n".join(lines) + "\n"


def _build_knowledge_context_markdown(knowledge_payload: dict[str, Any]) -> str:
    confirmed = knowledge_payload.get("confirmed_knowledge_summary") or {}
    pending = knowledge_payload.get("pending_proposals_summary") or {}
    recent_logs = knowledge_payload.get("recent_judgment_logs") or []
    return "\n".join(
        [
            "# Knowledge Context",
            "",
            "## Confirmed Knowledge",
            "",
            f"- entry_count: `{_fmt_int(confirmed.get('entry_count'))}`",
            f"- source_files: `{', '.join(confirmed.get('source_files') or [])}`",
            "",
            "## Pending Proposals",
            "",
            f"- pending_count: `{_fmt_int(pending.get('pending_count'))}`",
            f"- source_files: `{', '.join(pending.get('source_files') or [])}`",
            "",
            "## Recent Judgment Logs",
            "",
            *(f"- `{item.get('timestamp')}` `{item.get('summary') or item.get('message')}`" for item in recent_logs[:10]),
        ]
    ) + "\n"


def _build_proposal_summary_markdown(knowledge_payload: dict[str, Any]) -> str:
    pending = knowledge_payload.get("pending_proposals_summary") or {}
    return "\n".join(
        [
            "# Proposal Summary",
            "",
            f"- 当前 pending proposal 数：`{_fmt_int(pending.get('pending_count'))}`",
            "- 本次 `build-report-pack` 没有新建或回写 proposal。",
            "- report_pack 里若引用 proposal，只能作为待审核线索，不能覆盖 confirmed knowledge。",
        ]
    ) + "\n"


def _build_judgment_notes_markdown(knowledge_payload: dict[str, Any], issues: list[dict[str, str]]) -> str:
    return "\n".join(
        [
            "# Judgment Notes",
            "",
            "- 当前 report_pack 里的问题项都是 evidence-backed issue candidates，不是最终业务结论。",
            "- pending proposals 只保留在 knowledge 语境中，不自动提升为 confirmed knowledge。",
            "- 上层正式报告生成时，建议优先按 `canonical_issue_key` 去重，再按 `primary_section` 主展开。",
            "",
            "## 当前 issue keys",
            "",
            *(f"- `{issue['canonical_issue_key']}` -> `{issue['primary_section']}`" for issue in issues),
        ]
    ) + "\n"


def _build_root_readme(
    *,
    biz_system_name: str,
    biz_system_id: int,
    start_dt: datetime,
    end_dt: datetime,
    fetched: dict[str, dict[str, Any]],
    issues: list[dict[str, str]],
    url_status_counts: Counter[str],
    raw_files: list[str],
    fetch_failures: dict[str, str],
) -> str:
    return "\n".join(
        [
            f"# report_pack for {biz_system_name} ({biz_system_id})",
            "",
            "## 本次产物说明",
            "",
            f"- 时间范围：`{start_dt.strftime('%Y-%m-%d %H:%M')}` 至 `{end_dt.strftime('%Y-%m-%d %H:%M')}`",
            "- 目标：为上层报告生成器提供可直接消费的中间素材，不替代最终正式巡检报告定稿。",
            "",
            "## 本次使用的 packs",
            "",
            *(f"- `{pack_type}`" for pack_type in sorted(fetched)),
            "",
            "## 本次未生成或未写回的 packs",
            "",
            "- `knowledge_update_proposal_pack`",
            "  - 本次没有生成新的 proposals，也没有写回远端 review queue。",
            *(f"- `{name}`" for name in sorted(fetch_failures)),
            "",
            "## 章节覆盖情况",
            "",
            "- 证据充分：`overview`、`system_overview`、`interface`、`sql`、`trace_cases`",
            "- 部分覆盖：`application`、`page`",
            "- 明显缺失：真实 page-side RUM 指标、稳定对象级直达 URL",
            "",
            "## URL 质量摘要",
            "",
            *(f"- `{status}`: {count}" for status, count in sorted(url_status_counts.items())),
            "",
            "## Knowledge / Proposal 状态",
            "",
            "- 已输出 `knowledge_context.md`、`proposal_summary.md`、`judgment_notes.md`。",
            "- 本次未生成新的 knowledge proposals。",
            "- pending proposals 仍需 ChatGPT 或人工审核，不能直接当 confirmed knowledge。",
            *(f"- `{name}` 本次未成功拉取，相关增强证据需要单独补抓或重跑。" for name in sorted(fetch_failures)),
            "",
            "## 使用本包时必须注意",
            "",
            "- 页面章节只能写成“页面代理证据”，不得伪造成真实 RUM。",
            "- 问题去重请优先看 `03_issues/issues.csv` 里的 `canonical_issue_key`、`primary_section`、`duplicate_of`、`evidence_role`。",
            "- 最终报告成文、reader-friendly 命名、业务优先级和最终结论，仍需由 ChatGPT 或人工完成。",
            "",
            "## 当前 raw 文件",
            "",
            *(f"- `{path}`" for path in raw_files),
        ]
    ) + "\n"


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def _trace_file_name(trace_pack: dict[str, Any] | None) -> str:
    if not trace_pack:
        return "trace_fact_sheet.json"
    return _raw_file_name("trace_fact_sheet", trace_pack)


def _evidence_chain(*parts: str) -> str:
    return " -> ".join(part for part in parts if part)


def _safe_slug(value: Any) -> str:
    text = re.sub(r"[^A-Za-z0-9._-]+", "_", str(value or "").strip()).strip("._-")
    return text or "item"


def _as_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _fmt_ms(value: Any) -> str:
    number = _as_float(value)
    if number <= 0:
        return "0ms"
    if abs(number - int(number)) < 0.001:
        return f"{int(number)}ms"
    return f"{number:.3f}ms"


def _fmt_int(value: Any) -> str:
    try:
        return str(int(value))
    except (TypeError, ValueError):
        return "0"


def _fmt_rate(value: Any) -> str:
    number = _as_float(value)
    return f"{number:.2f}%"
