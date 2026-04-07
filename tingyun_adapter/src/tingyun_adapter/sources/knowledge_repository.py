from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from tingyun_adapter.domain.models.common import dataclass_to_dict
from tingyun_adapter.domain.models.knowledge import JudgmentLogEntry, knowledge_now


CONFIRMED_FILE_TYPES = (
    "system_profile",
    "glossary",
    "critical_paths",
    "action_labels",
    "dependency_annotations",
    "known_patterns",
    "baseline_notes",
    "page_route_map",
)
REVIEW_QUEUE_FILE = "review_queue"
JUDGMENT_LOG_FILE = "judgment_log"


class KnowledgeRepository:
    def __init__(self, base_dir: str | Path) -> None:
        self.base_dir = Path(base_dir)

    def exists(self) -> bool:
        return self.base_dir.exists()

    def biz_system_key(self, biz_system_id: int) -> str:
        return f"biz_system_{int(biz_system_id)}"

    def biz_system_dir(self, biz_system_id: int) -> Path:
        return self.base_dir / self.biz_system_key(biz_system_id)

    def file_path(self, biz_system_id: int, file_type: str) -> Path:
        return self.biz_system_dir(biz_system_id) / f"{file_type}.json"

    def load_bundle(self, biz_system_id: int) -> dict[str, Any]:
        confirmed = {file_type: self.load_confirmed_document(biz_system_id, file_type) for file_type in CONFIRMED_FILE_TYPES}
        return {
            "biz_system": {
                "id": int(biz_system_id),
                "key": self.biz_system_key(biz_system_id),
                "directory": str(self.biz_system_dir(biz_system_id)),
            },
            "confirmed": confirmed,
            "review_queue": self.load_review_queue(biz_system_id),
            "judgment_log": self.load_judgment_log(biz_system_id),
        }

    def load_confirmed_document(self, biz_system_id: int, file_type: str) -> dict[str, Any]:
        path = self.file_path(biz_system_id, file_type)
        if not path.exists():
            return self._default_confirmed_document(biz_system_id, file_type)
        return self._read_json(path)

    def load_review_queue(self, biz_system_id: int) -> dict[str, Any]:
        path = self.file_path(biz_system_id, REVIEW_QUEUE_FILE)
        if not path.exists():
            return self._default_review_queue(biz_system_id)
        return self._read_json(path)

    def load_judgment_log(self, biz_system_id: int) -> dict[str, Any]:
        path = self.file_path(biz_system_id, JUDGMENT_LOG_FILE)
        if not path.exists():
            return self._default_judgment_log(biz_system_id)
        return self._read_json(path)

    def merge_pending_proposals(self, biz_system_id: int, proposals: list[dict[str, Any]]) -> dict[str, Any]:
        bundle = self.load_bundle(biz_system_id)
        confirmed = bundle["confirmed"]
        review_queue = bundle["review_queue"]
        pending_index = {self._proposal_identity(item): dict(item) for item in (review_queue.get("pending") or [])}
        seen_input_keys: set[str] = set()
        created_count = 0
        merged_count = 0
        deduplicated_count = 0
        conflicts: list[dict[str, Any]] = []

        for proposal in proposals:
            identity = self._proposal_identity(proposal)
            if identity in seen_input_keys:
                deduplicated_count += 1
                continue
            seen_input_keys.add(identity)
            conflict_items = self._find_conflicts(confirmed, proposal)
            proposal["conflicts"] = conflict_items
            conflicts.extend(conflict_items)
            current = pending_index.get(identity)
            if current is None:
                pending_index[identity] = proposal
                created_count += 1
                continue
            pending_index[identity] = self._merge_proposals(current, proposal)
            merged_count += 1

        pending = list(pending_index.values())
        review_queue["pending"] = sorted(pending, key=lambda item: str(item.get("proposal_id") or ""))
        review_queue["metadata"] = self._updated_metadata(review_queue.get("metadata"), entry_count=len(review_queue["pending"]))
        self._write_json(self.file_path(biz_system_id, REVIEW_QUEUE_FILE), review_queue)

        if proposals:
            log_entry = JudgmentLogEntry(
                log_id=f"log:{self.biz_system_key(biz_system_id)}:{len(bundle['judgment_log'].get('entries') or []) + 1}",
                entry_type="proposal_ingested",
                summary=(
                    f"ingested {len(proposals)} proposal(s), created={created_count}, "
                    f"merged={merged_count}, deduplicated={deduplicated_count}"
                ),
                related_refs=[proposal.get("object_ref") or {} for proposal in proposals if proposal.get("object_ref")],
                outcome={
                    "created_count": created_count,
                    "merged_count": merged_count,
                    "deduplicated_count": deduplicated_count,
                    "conflict_count": len(conflicts),
                },
            )
            self.append_judgment_log(biz_system_id, dataclass_to_dict(log_entry))

        refreshed = self.load_review_queue(biz_system_id)
        return {
            "review_queue": refreshed,
            "merge_summary": {
                "received_count": len(proposals),
                "created_count": created_count,
                "merged_count": merged_count,
                "deduplicated_count": deduplicated_count,
                "conflict_count": len(conflicts),
            },
            "conflicts": conflicts,
        }

    def append_judgment_log(self, biz_system_id: int, entry: dict[str, Any]) -> None:
        document = self.load_judgment_log(biz_system_id)
        entries = list(document.get("entries") or [])
        entries.append(entry)
        document["entries"] = entries
        document["metadata"] = self._updated_metadata(document.get("metadata"), entry_count=len(entries))
        self._write_json(self.file_path(biz_system_id, JUDGMENT_LOG_FILE), document)

    def _default_confirmed_document(self, biz_system_id: int, file_type: str) -> dict[str, Any]:
        return {
            "schema_version": "v1",
            "biz_system": {"id": int(biz_system_id), "key": self.biz_system_key(biz_system_id)},
            "file_type": file_type,
            "entries": [],
            "stale_entries": [],
            "metadata": self._updated_metadata(None, entry_count=0),
        }

    def _default_review_queue(self, biz_system_id: int) -> dict[str, Any]:
        return {
            "schema_version": "v1",
            "biz_system": {"id": int(biz_system_id), "key": self.biz_system_key(biz_system_id)},
            "file_type": REVIEW_QUEUE_FILE,
            "pending": [],
            "rejected": [],
            "obsolete": [],
            "metadata": self._updated_metadata(None, entry_count=0),
        }

    def _default_judgment_log(self, biz_system_id: int) -> dict[str, Any]:
        return {
            "schema_version": "v1",
            "biz_system": {"id": int(biz_system_id), "key": self.biz_system_key(biz_system_id)},
            "file_type": JUDGMENT_LOG_FILE,
            "entries": [],
            "metadata": self._updated_metadata(None, entry_count=0),
        }

    def _merge_proposals(self, current: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
        merged = dict(current)
        merged["title"] = incoming.get("title") or current.get("title")
        merged["summary"] = incoming.get("summary") or current.get("summary") or ""
        merged["attributes"] = {**(current.get("attributes") or {}), **(incoming.get("attributes") or {})}
        merged["tags"] = self._unique_list([*(current.get("tags") or []), *(incoming.get("tags") or [])])
        merged["reasoning_summary"] = incoming.get("reasoning_summary") or current.get("reasoning_summary") or ""
        merged["duplicate_of"] = self._unique_list([*(current.get("duplicate_of") or []), *(incoming.get("duplicate_of") or [])])
        merged["conflicts"] = self._merge_dict_list(current.get("conflicts") or [], incoming.get("conflicts") or [])
        current_provenance = dict(current.get("provenance") or {})
        incoming_provenance = dict(incoming.get("provenance") or {})
        merged["provenance"] = {
            **current_provenance,
            **incoming_provenance,
            "source_refs": self._merge_dict_list(current_provenance.get("source_refs") or [], incoming_provenance.get("source_refs") or []),
            "created_at": current_provenance.get("created_at") or incoming_provenance.get("created_at") or knowledge_now(),
            "updated_at": knowledge_now(),
            "confidence": max(float(current_provenance.get("confidence", 0.0)), float(incoming_provenance.get("confidence", 0.0))),
        }
        return merged

    def _find_conflicts(self, confirmed_docs: dict[str, Any], proposal: dict[str, Any]) -> list[dict[str, Any]]:
        target_file_hint = str(proposal.get("target_file_hint") or "")
        if target_file_hint not in confirmed_docs:
            return []
        proposal_ref = proposal.get("object_ref") or {}
        proposal_key = self._ref_key(proposal_ref)
        proposal_attributes = proposal.get("attributes") or {}
        proposal_summary = str(proposal.get("summary") or "").strip()
        conflicts: list[dict[str, Any]] = []
        for entry in confirmed_docs[target_file_hint].get("entries") or []:
            if proposal_key and proposal_key != self._ref_key(entry.get("object_ref") or {}):
                continue
            difference_keys: list[str] = []
            entry_attributes = entry.get("attributes") or {}
            for key in sorted(set(entry_attributes.keys()) & set(proposal_attributes.keys())):
                if entry_attributes.get(key) != proposal_attributes.get(key):
                    difference_keys.append(key)
            entry_summary = str(entry.get("summary") or "").strip()
            if not difference_keys and entry_summary and proposal_summary and entry_summary != proposal_summary:
                difference_keys.append("summary")
            if not difference_keys:
                continue
            conflicts.append(
                {
                    "target_file_hint": target_file_hint,
                    "object_ref": proposal_ref,
                    "confirmed_entry_id": entry.get("entry_id"),
                    "difference_keys": difference_keys,
                    "staleness": entry.get("staleness") or "active",
                }
            )
        return conflicts

    def _proposal_identity(self, proposal: dict[str, Any]) -> str:
        target_file_hint = str(proposal.get("target_file_hint") or "")
        proposal_type = str(proposal.get("proposal_type") or "")
        object_key = self._ref_key(proposal.get("object_ref") or {})
        if target_file_hint or proposal_type or object_key:
            canonical = {
                "target_file_hint": target_file_hint,
                "proposal_type": proposal_type,
                "object_key": object_key or str(proposal.get("title") or proposal.get("summary") or ""),
            }
            return hashlib.sha1(json.dumps(canonical, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()[:16]
        return str(proposal.get("dedupe_key") or proposal.get("proposal_id") or "")

    def _updated_metadata(self, current: dict[str, Any] | None, *, entry_count: int) -> dict[str, Any]:
        current = current or {}
        return {
            "created_at": current.get("created_at") or knowledge_now(),
            "updated_at": knowledge_now(),
            "entry_count": entry_count,
        }

    def _merge_dict_list(self, left: list[dict[str, Any]], right: list[dict[str, Any]]) -> list[dict[str, Any]]:
        merged: list[dict[str, Any]] = []
        seen: set[str] = set()
        for item in [*left, *right]:
            key = json.dumps(item, sort_keys=True, ensure_ascii=False)
            if key in seen:
                continue
            seen.add(key)
            merged.append(item)
        return merged

    def _ref_key(self, target_ref: Any) -> str:
        if not isinstance(target_ref, dict):
            return str(target_ref)
        kind = str(target_ref.get("kind") or "unknown")
        ordered = [f"{key}={target_ref[key]}" for key in sorted(target_ref.keys()) if key != "kind"]
        return f"{kind}|" + "|".join(ordered)

    def _unique_list(self, items: list[str]) -> list[str]:
        return list(dict.fromkeys(item for item in items if item))

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def _write_json(self, path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
