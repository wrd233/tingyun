from __future__ import annotations

import hashlib
import json
from typing import Any

from tingyun_adapter.domain.enums import PackType
from tingyun_adapter.domain.models.common import AnalysisContext, Evidence, PackEnvelope, WarningMessage, dataclass_to_dict
from tingyun_adapter.domain.models.knowledge import KnowledgeProposal, KnowledgeProvenance, knowledge_now
from tingyun_adapter.domain.models.packs import KnowledgeContextPackPayload, KnowledgeUpdateProposalPackPayload
from tingyun_adapter.sources.knowledge_repository import CONFIRMED_FILE_TYPES, KnowledgeRepository
from tingyun_adapter.usecases.builders import _coerce_evidence_list, _pack


def build_knowledge_context_pack(
    adapter: Any,
    context: AnalysisContext,
    *,
    source_mode: str = "auto",
    recent_log_limit: int = 5,
) -> PackEnvelope:
    warnings: list[WarningMessage] = []
    snapshot = load_knowledge_context_snapshot(adapter, context, recent_log_limit=recent_log_limit)
    if snapshot["knowledge_scope"].get("repository_status") != "configured":
        warnings.append(
            WarningMessage(
                code="knowledge_repository_unavailable",
                message="Knowledge repository is not configured; returning an empty but stable knowledge context pack.",
                source_api="knowledge_repository",
            )
        )
    payload = KnowledgeContextPackPayload(
        scope=_knowledge_scope(context, source_mode, recent_log_limit),
        knowledge_scope=snapshot["knowledge_scope"],
        confirmed_knowledge_summary=snapshot["confirmed_knowledge_summary"],
        pending_proposals_summary=snapshot["pending_proposals_summary"],
        recent_judgment_logs=snapshot["recent_judgment_logs"],
        core_context=snapshot["core_context"],
        missing_items=snapshot["missing_items"],
        source_summary=snapshot["source_summary"],
        input_dependencies=["knowledge_repository"],
        evidence_refs=snapshot["evidence_refs"],
        derivation_notes=[
            "Knowledge context is read-before-infer support for LLM workflows and enhanced packs.",
            "Missing files degrade to empty sections instead of failing the pack build.",
        ],
        evidence=snapshot["evidence"],
    )
    return _pack(
        PackType.KNOWLEDGE_CONTEXT.value,
        context,
        payload,
        evidence=_coerce_evidence_list(payload.evidence),
        warnings=warnings,
        source_mode=source_mode,
        missing_inputs=snapshot["missing_items"],
        confidence_notes=["Knowledge context reflects persisted files and does not invent missing business memory."],
        build_stats={
            "confirmed_entry_count": snapshot["confirmed_knowledge_summary"].get("entry_count", 0),
            "pending_entry_count": snapshot["pending_proposals_summary"].get("pending_count", 0),
            "recent_log_count": len(snapshot["recent_judgment_logs"]),
        },
    )


def build_knowledge_update_proposal_pack(
    adapter: Any,
    context: AnalysisContext,
    *,
    proposals: list[dict[str, Any]] | None = None,
    source_mode: str = "auto",
    persist: bool = True,
) -> PackEnvelope:
    warnings: list[WarningMessage] = []
    missing_inputs: list[str] = []
    repo = _knowledge_repo(adapter)
    if repo is None:
        warnings.append(
            WarningMessage(
                code="knowledge_repository_unavailable",
                message="Knowledge repository is not configured; proposals are normalized but not persisted.",
                source_api="knowledge_repository",
            )
        )
    normalized = normalize_knowledge_proposals(context, proposals or [])
    if not normalized:
        missing_inputs.append("proposal_items")

    merge_result = {
        "review_queue": _empty_review_queue(context.biz_system_id, repo),
        "merge_summary": {
            "received_count": len(normalized),
            "created_count": 0,
            "merged_count": 0,
            "deduplicated_count": 0,
            "conflict_count": 0,
            "persisted": False,
        },
        "conflicts": [],
    }
    if repo is not None and normalized and persist:
        merge_result = repo.merge_pending_proposals(context.biz_system_id, normalized)
        merge_result["merge_summary"]["persisted"] = True

    snapshot = load_knowledge_context_snapshot(adapter, context, recent_log_limit=5)
    payload = KnowledgeUpdateProposalPackPayload(
        scope=_knowledge_scope(context, source_mode, len(normalized)),
        knowledge_scope=snapshot["knowledge_scope"],
        received_proposals=proposals or [],
        normalized_proposals=normalized,
        merge_summary=merge_result["merge_summary"],
        conflicts=merge_result["conflicts"],
        pending_proposals=(merge_result["review_queue"].get("pending") or [])[:50],
        review_queue_snapshot={
            "pending_count": len(merge_result["review_queue"].get("pending") or []),
            "rejected_count": len(merge_result["review_queue"].get("rejected") or []),
            "obsolete_count": len(merge_result["review_queue"].get("obsolete") or []),
            "file_path": str(repo.file_path(context.biz_system_id, "review_queue")) if repo is not None else None,
        },
        input_dependencies=["knowledge_repository"],
        evidence_refs=snapshot["evidence_refs"],
        derivation_notes=[
            "Incoming knowledge updates are normalized into pending proposals, never directly into confirmed knowledge.",
            "Deduplication and merge-not-overwrite use target file hint plus existing object identity.",
        ],
        evidence=snapshot["evidence"],
    )
    return _pack(
        PackType.KNOWLEDGE_UPDATE_PROPOSAL.value,
        context,
        payload,
        evidence=_coerce_evidence_list(payload.evidence),
        warnings=warnings,
        source_mode=source_mode,
        missing_inputs=missing_inputs,
        confidence_notes=["Pending proposals still require later confirmation or approval before they become confirmed knowledge."],
        build_stats={
            "received_proposal_count": len(proposals or []),
            "normalized_proposal_count": len(normalized),
            "conflict_count": len(merge_result["conflicts"]),
        },
    )


def load_knowledge_context_snapshot(adapter: Any, context: AnalysisContext, *, recent_log_limit: int = 5) -> dict[str, Any]:
    repo = _knowledge_repo(adapter)
    if repo is None:
        return _empty_snapshot(context)

    bundle = repo.load_bundle(context.biz_system_id)
    confirmed = bundle["confirmed"]
    review_queue = bundle["review_queue"]
    judgment_log = bundle["judgment_log"]

    confirmed_counts = {file_type: len(confirmed[file_type].get("entries") or []) for file_type in CONFIRMED_FILE_TYPES}
    stale_counts = {file_type: len(confirmed[file_type].get("stale_entries") or []) for file_type in CONFIRMED_FILE_TYPES}
    missing_items = [file_type for file_type, count in confirmed_counts.items() if count == 0]
    if not (review_queue.get("pending") or []):
        missing_items.append("review_queue.pending")
    if not (judgment_log.get("entries") or []):
        missing_items.append("judgment_log.entries")

    evidence = _knowledge_evidence(repo, context.biz_system_id, bundle)
    recent_logs = list(reversed(judgment_log.get("entries") or []))[:recent_log_limit]
    snapshot = {
        "knowledge_scope": {
            "biz_system_id": context.biz_system_id,
            "knowledge_key": bundle["biz_system"]["key"],
            "knowledge_dir": bundle["biz_system"]["directory"],
            "repository_status": "configured",
            "read_before_infer": True,
        },
        "confirmed": confirmed,
        "review_queue": review_queue,
        "judgment_log": judgment_log,
        "confirmed_indexes": {file_type: _index_entries_by_ref(confirmed[file_type].get("entries") or []) for file_type in CONFIRMED_FILE_TYPES},
        "pending_index": _index_entries_by_ref(review_queue.get("pending") or []),
        "confirmed_knowledge_summary": {
            "entry_count": sum(confirmed_counts.values()),
            "file_entry_counts": confirmed_counts,
            "stale_entry_counts": stale_counts,
            "files_with_content": [file_type for file_type, count in confirmed_counts.items() if count > 0],
        },
        "pending_proposals_summary": {
            "pending_count": len(review_queue.get("pending") or []),
            "rejected_count": len(review_queue.get("rejected") or []),
            "obsolete_count": len(review_queue.get("obsolete") or []),
            "target_file_counts": _target_file_counts(review_queue.get("pending") or []),
        },
        "recent_judgment_logs": recent_logs,
        "core_context": {
            "system_profile": _limit_entries(confirmed["system_profile"].get("entries") or [], 5),
            "glossary": _limit_entries(confirmed["glossary"].get("entries") or [], 10),
            "critical_paths": _limit_entries(confirmed["critical_paths"].get("entries") or [], 10),
            "action_labels": _limit_entries(confirmed["action_labels"].get("entries") or [], 10),
            "dependency_annotations": _limit_entries(confirmed["dependency_annotations"].get("entries") or [], 10),
            "known_patterns": _limit_entries(confirmed["known_patterns"].get("entries") or [], 10),
            "baseline_notes": _limit_entries(confirmed["baseline_notes"].get("entries") or [], 10),
            "page_route_map": _limit_entries(confirmed["page_route_map"].get("entries") or [], 10),
        },
        "missing_items": missing_items,
        "source_summary": {
            "confirmed_files": {
                file_type: {
                    "file_path": str(repo.file_path(context.biz_system_id, file_type)),
                    "entry_count": confirmed_counts[file_type],
                    "stale_entry_count": stale_counts[file_type],
                }
                for file_type in CONFIRMED_FILE_TYPES
            },
            "review_queue_file": str(repo.file_path(context.biz_system_id, "review_queue")),
            "judgment_log_file": str(repo.file_path(context.biz_system_id, "judgment_log")),
        },
        "evidence": evidence,
        "evidence_refs": [item["id"] for item in evidence],
    }
    return snapshot


def lookup_confirmed_knowledge(snapshot: dict[str, Any], file_type: str, target_ref: dict[str, Any]) -> list[dict[str, Any]]:
    return list((snapshot.get("confirmed_indexes") or {}).get(file_type, {}).get(knowledge_ref_key(target_ref), []))


def lookup_pending_proposals(snapshot: dict[str, Any], target_ref: dict[str, Any], *, target_file_hint: str | None = None) -> list[dict[str, Any]]:
    items = list((snapshot.get("pending_index") or {}).get(knowledge_ref_key(target_ref), []))
    if target_file_hint is None:
        return items
    return [item for item in items if item.get("target_file_hint") == target_file_hint]


def knowledge_ref_key(target_ref: Any) -> str:
    if not isinstance(target_ref, dict):
        return str(target_ref)
    kind = str(target_ref.get("kind") or "unknown")
    ordered = [f"{key}={target_ref[key]}" for key in sorted(target_ref.keys()) if key != "kind"]
    return f"{kind}|" + "|".join(ordered)


def normalize_knowledge_proposals(context: AnalysisContext, proposals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in proposals:
        proposal = _normalize_single_proposal(context, item)
        identity = str(proposal.dedupe_key)
        if identity in seen:
            continue
        seen.add(identity)
        normalized.append(dataclass_to_dict(proposal))
    return normalized


def _normalize_single_proposal(context: AnalysisContext, item: dict[str, Any]) -> KnowledgeProposal:
    object_ref = dict(item.get("object_ref") or item.get("target_ref") or {})
    target_file_hint = _infer_target_file_hint(item, object_ref)
    proposal_type = str(item.get("proposal_type") or target_file_hint)
    title = item.get("title")
    summary = str(item.get("summary") or item.get("reasoning_summary") or "").strip()
    attributes = dict(item.get("attributes") or {})
    tags = list(item.get("tags") or [])
    source_refs = list(item.get("source_refs") or [])
    if not source_refs:
        source_refs = [
            {
                "kind": "analysis_context",
                "biz_system_id": context.biz_system_id,
                "end_time": context.time_window.end_time,
                "period_minutes": context.time_window.period_minutes,
            }
        ]
    provenance = KnowledgeProvenance(
        source_type=str(item.get("source_type") or "adapter_pack"),
        source_refs=source_refs,
        created_at=str(item.get("created_at") or knowledge_now()),
        updated_at=str(item.get("updated_at") or knowledge_now()),
        confidence=float(item.get("confidence", 0.6)),
        author_kind=str(item.get("author_kind") or "model"),
        creation_method=str(item.get("creation_method") or "model_suggestion"),
    )
    identity_seed = {
        "target_file_hint": target_file_hint,
        "proposal_type": proposal_type,
        "object_key": knowledge_ref_key(object_ref) or str(title or summary or target_file_hint),
    }
    dedupe_key = hashlib.sha1(json.dumps(identity_seed, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()[:16]
    return KnowledgeProposal(
        proposal_id=str(item.get("proposal_id") or f"proposal:{target_file_hint}:{dedupe_key}"),
        proposal_type=proposal_type,
        target_file_hint=target_file_hint,
        object_ref=object_ref,
        title=str(title) if title else None,
        summary=summary,
        attributes=attributes,
        tags=tags,
        status=str(item.get("status") or "pending"),
        staleness=str(item.get("staleness") or "active"),
        reasoning_summary=str(item.get("reasoning_summary") or summary),
        conflicts=list(item.get("conflicts") or []),
        duplicate_of=list(item.get("duplicate_of") or []),
        dedupe_key=dedupe_key,
        provenance=provenance,
    )


def _knowledge_scope(context: AnalysisContext, source_mode: str, limit: int) -> dict[str, Any]:
    return {
        "bizSystemId": context.biz_system_id,
        "endTime": context.time_window.end_time,
        "periodMinutes": context.time_window.period_minutes,
        "sourceMode": source_mode,
        "limit": limit,
    }


def _knowledge_repo(adapter: Any) -> KnowledgeRepository | None:
    repo = getattr(adapter, "knowledge_repository", None)
    if isinstance(repo, KnowledgeRepository):
        return repo
    return None


def _index_entries_by_ref(entries: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    indexed: dict[str, list[dict[str, Any]]] = {}
    for entry in entries:
        key = knowledge_ref_key(entry.get("object_ref") or {})
        indexed.setdefault(key, []).append(entry)
    return indexed


def _target_file_counts(entries: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for entry in entries:
        file_type = str(entry.get("target_file_hint") or "unknown")
        counts[file_type] = counts.get(file_type, 0) + 1
    return counts


def _limit_entries(entries: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    return entries[:limit]


def _knowledge_evidence(repo: KnowledgeRepository, biz_system_id: int, bundle: dict[str, Any]) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []
    for file_type in CONFIRMED_FILE_TYPES:
        entries = (bundle["confirmed"].get(file_type) or {}).get("entries") or []
        evidence.append(
            _evidence(
                evidence_id=f"knowledge_{file_type}",
                source_path=str(repo.file_path(biz_system_id, file_type)),
                response_excerpt={"entry_count": len(entries), "sample_entries": entries[:3]},
            )
        )
    review_queue = bundle["review_queue"]
    evidence.append(
        _evidence(
            evidence_id="knowledge_review_queue",
            source_path=str(repo.file_path(biz_system_id, "review_queue")),
            response_excerpt={
                "pending_count": len(review_queue.get("pending") or []),
                "rejected_count": len(review_queue.get("rejected") or []),
                "obsolete_count": len(review_queue.get("obsolete") or []),
            },
        )
    )
    judgment_log = bundle["judgment_log"]
    evidence.append(
        _evidence(
            evidence_id="knowledge_judgment_log",
            source_path=str(repo.file_path(biz_system_id, "judgment_log")),
            response_excerpt={"entry_count": len(judgment_log.get("entries") or []), "recent_entries": (judgment_log.get("entries") or [])[-3:]},
        )
    )
    return evidence


def _evidence(*, evidence_id: str, source_path: str, response_excerpt: Any) -> dict[str, Any]:
    evidence = Evidence(
        id=evidence_id,
        source_api="knowledge_repository",
        source_path=source_path,
        source_method="READ",
        request_signature={},
        request_params={},
        response_excerpt=response_excerpt,
        confidence=1.0,
    )
    return dataclass_to_dict(evidence)


def _infer_target_file_hint(item: dict[str, Any], object_ref: dict[str, Any]) -> str:
    if item.get("target_file_hint"):
        return str(item["target_file_hint"])
    proposal_type = str(item.get("proposal_type") or "")
    if proposal_type in CONFIRMED_FILE_TYPES:
        return proposal_type
    kind = str(object_ref.get("kind") or "")
    if kind == "action":
        return "action_labels"
    if kind in {"external_dependency", "database_component", "nosql_component"}:
        return "dependency_annotations"
    if kind == "page":
        return "page_route_map"
    if kind == "critical_path":
        return "critical_paths"
    if kind == "pattern":
        return "known_patterns"
    if kind == "glossary_term":
        return "glossary"
    return "baseline_notes"


def _empty_snapshot(context: AnalysisContext) -> dict[str, Any]:
    return {
        "knowledge_scope": {
            "biz_system_id": context.biz_system_id,
            "knowledge_key": f"biz_system_{context.biz_system_id}",
            "knowledge_dir": None,
            "repository_status": "unconfigured",
            "read_before_infer": False,
        },
        "confirmed": {file_type: {"entries": [], "stale_entries": []} for file_type in CONFIRMED_FILE_TYPES},
        "review_queue": _empty_review_queue(context.biz_system_id, None),
        "judgment_log": {"entries": []},
        "confirmed_indexes": {file_type: {} for file_type in CONFIRMED_FILE_TYPES},
        "pending_index": {},
        "confirmed_knowledge_summary": {
            "entry_count": 0,
            "file_entry_counts": {file_type: 0 for file_type in CONFIRMED_FILE_TYPES},
            "stale_entry_counts": {file_type: 0 for file_type in CONFIRMED_FILE_TYPES},
            "files_with_content": [],
        },
        "pending_proposals_summary": {
            "pending_count": 0,
            "rejected_count": 0,
            "obsolete_count": 0,
            "target_file_counts": {},
        },
        "recent_judgment_logs": [],
        "core_context": {file_type: [] for file_type in CONFIRMED_FILE_TYPES},
        "missing_items": list(CONFIRMED_FILE_TYPES) + ["review_queue.pending", "judgment_log.entries"],
        "source_summary": {"confirmed_files": {}, "review_queue_file": None, "judgment_log_file": None},
        "evidence": [],
        "evidence_refs": [],
    }


def _empty_review_queue(biz_system_id: int, repo: KnowledgeRepository | None) -> dict[str, Any]:
    if repo is not None:
        return repo._default_review_queue(biz_system_id)  # noqa: SLF001
    return {
        "schema_version": "v1",
        "biz_system": {"id": biz_system_id, "key": f"biz_system_{biz_system_id}"},
        "file_type": "review_queue",
        "pending": [],
        "rejected": [],
        "obsolete": [],
        "metadata": {"created_at": knowledge_now(), "updated_at": knowledge_now(), "entry_count": 0},
    }
