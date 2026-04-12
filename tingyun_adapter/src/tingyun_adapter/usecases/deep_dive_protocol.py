from __future__ import annotations

import hashlib
import json
from typing import Any


MASTER_TABLE_BY_OBJECT_TYPE = {
    "application": "application_master.csv",
    "request": "request_master.csv",
    "interface_cluster": "interface_cluster_master.csv",
    "sql": "sql_master.csv",
    "nosql": "nosql_master.csv",
    "dependency": "dependency_master.csv",
}


def build_deep_dive_seed(candidate: dict[str, Any]) -> dict[str, Any]:
    object_type = infer_master_object_type(candidate)
    target_ref = candidate.get("target_ref") or {}
    candidate_key = str(candidate.get("candidate_key") or "")
    source_packs = _unique_strings(candidate.get("source_packs") or [])
    recommended_next_packs = _unique_strings(candidate.get("recommended_next_packs") or [])
    return {
        "deep_dive_seed_id": f"seed_{_hash_text(candidate_key or json.dumps(target_ref, ensure_ascii=False, sort_keys=True))[:12]}",
        "selected_for_deep_dive": True,
        "object_type": object_type,
        "source_master_table": MASTER_TABLE_BY_OBJECT_TYPE.get(object_type, ""),
        "deep_dive_kind": infer_deep_dive_kind(candidate, object_type=object_type),
        "deep_dive_scope": str(candidate.get("impact_scope") or "local"),
        "pack_source": ";".join(source_packs),
        "recommended_next_packs": recommended_next_packs,
        "master_match_hints": build_master_match_hints(candidate, object_type=object_type),
        "suspected_cluster_key": infer_suspected_cluster_key(candidate, object_type=object_type),
        "related_object_ids": infer_related_object_ids(candidate),
        "report_group_hint": infer_report_group_hint(candidate, object_type=object_type),
    }


def infer_master_object_type(candidate: dict[str, Any]) -> str:
    candidate_type = str(candidate.get("candidate_type") or "")
    target_kind = str((candidate.get("target_ref") or {}).get("kind") or "")
    if candidate_type in {"action", "trace"} or target_kind in {"action", "trace"}:
        return "request"
    if candidate_type == "sql" or target_kind == "sql":
        return "sql"
    if candidate_type == "dependency" or target_kind in {"dependency", "external_dependency"}:
        return "dependency"
    if candidate_type == "regression_signal" and target_kind in {"application", "instance"}:
        return "application"
    return "request"


def infer_deep_dive_kind(candidate: dict[str, Any], *, object_type: str | None = None) -> str:
    object_type = object_type or infer_master_object_type(candidate)
    candidate_type = str(candidate.get("candidate_type") or "")
    recommended_next_packs = set(_unique_strings(candidate.get("recommended_next_packs") or []))
    if candidate_type == "trace" or "trace_case_pack" in recommended_next_packs or "trace_fact_sheet" in recommended_next_packs:
        return "trace_primary"
    if candidate_type == "sql":
        return "sql_bottleneck"
    if "database_component_pack" in recommended_next_packs:
        return "database_component_context"
    if "nosql_component_pack" in recommended_next_packs:
        return "nosql_component_context"
    if "connection_pool_pack" in recommended_next_packs:
        return "connection_pool_context"
    if "external_dependency_pack" in recommended_next_packs or "topology_dependency_pack" in recommended_next_packs:
        return "dependency_chain"
    if "page_experience_pack" in recommended_next_packs:
        return "page_experience_context"
    if object_type == "dependency":
        return "problem_cluster_context"
    return f"{object_type}_context"


def build_master_match_hints(candidate: dict[str, Any], *, object_type: str | None = None) -> dict[str, Any]:
    object_type = object_type or infer_master_object_type(candidate)
    target_ref = candidate.get("target_ref") or {}
    hints: dict[str, Any] = {
        "candidate_key": candidate.get("candidate_key"),
        "display_name": candidate.get("display_name"),
        "target_ref": target_ref,
    }
    if object_type == "request":
        hints.update(
            {
                "application_name": candidate.get("application_name") or target_ref.get("application_name"),
                "action_name": candidate.get("action_name") or candidate.get("display_name") or target_ref.get("action_name"),
                "action_id": target_ref.get("action_id"),
                "trace_id": target_ref.get("trace_id") or candidate.get("trace_id_numeric") or candidate.get("trace_guid"),
            }
        )
    elif object_type == "sql":
        hints.update(
            {
                "sql_fingerprint": candidate.get("sql_fingerprint"),
                "component_name": candidate.get("component_name") or target_ref.get("component_name"),
                "component_subtype": candidate.get("component_subtype") or target_ref.get("component_subtype"),
            }
        )
    elif object_type == "dependency":
        hints.update(
            {
                "node_id": candidate.get("node_id") or target_ref.get("node_id"),
                "node_name": candidate.get("display_name") or target_ref.get("node_name"),
            }
        )
    return {key: value for key, value in hints.items() if value not in (None, "", [], {})}


def infer_suspected_cluster_key(candidate: dict[str, Any], *, object_type: str | None = None) -> str:
    object_type = object_type or infer_master_object_type(candidate)
    review_hints = _unique_strings(candidate.get("review_hints") or [])
    seed = "|".join([object_type, str(candidate.get("candidate_key") or ""), ",".join(review_hints[:3])])
    return f"{object_type}:{_hash_text(seed)[:10]}"


def infer_related_object_ids(candidate: dict[str, Any]) -> list[str]:
    related: list[str] = []
    for item in candidate.get("impact_objects") or []:
        action_id = item.get("action_id")
        action_name = item.get("action_name")
        component_name = item.get("component_name")
        if action_id or action_name:
            related.append(f"request_hint:{action_id or action_name}")
        elif component_name:
            related.append(f"component_hint:{component_name}")
    return related[:10]


def infer_report_group_hint(candidate: dict[str, Any], *, object_type: str | None = None) -> str:
    object_type = object_type or infer_master_object_type(candidate)
    impact_scope = str(candidate.get("impact_scope") or "local")
    evidence_strength = str(candidate.get("evidence_strength") or "weak")
    return f"{object_type}:{impact_scope}:{evidence_strength}"


def summarize_bundle_counts(payload: dict[str, Any]) -> dict[str, int]:
    page_links = payload.get("page_links") or []
    screenshot_hints = payload.get("screenshot_hints") or []
    evidence = payload.get("evidence") or []
    evidence_linkage = payload.get("evidence_linkage") or {}
    trace_links = evidence_linkage.get("related_traces") or []
    return {
        "evidence_count": len(evidence),
        "page_link_count": len(page_links),
        "screenshot_hint_count": len(screenshot_hints),
        "trace_link_count": len(trace_links),
    }


def _hash_text(text: str) -> str:
    return hashlib.sha1(str(text).encode("utf-8")).hexdigest()


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
