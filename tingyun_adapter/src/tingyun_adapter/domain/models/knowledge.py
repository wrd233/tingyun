from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


def knowledge_now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


@dataclass
class KnowledgeProvenance:
    source_type: str = "system"
    source_refs: list[dict[str, Any]] = field(default_factory=list)
    created_at: str = field(default_factory=knowledge_now)
    updated_at: str = field(default_factory=knowledge_now)
    confidence: float = 0.5
    author_kind: str = "system"
    creation_method: str = "system_inference"


@dataclass
class KnowledgeEntry:
    entry_id: str
    entry_type: str
    object_ref: dict[str, Any] = field(default_factory=dict)
    title: str | None = None
    summary: str = ""
    attributes: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    status: str = "confirmed"
    staleness: str = "active"
    provenance: KnowledgeProvenance = field(default_factory=KnowledgeProvenance)


@dataclass
class KnowledgeProposal:
    proposal_id: str
    proposal_type: str
    target_file_hint: str
    object_ref: dict[str, Any] = field(default_factory=dict)
    title: str | None = None
    summary: str = ""
    attributes: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    status: str = "pending"
    staleness: str = "active"
    reasoning_summary: str = ""
    conflicts: list[dict[str, Any]] = field(default_factory=list)
    duplicate_of: list[str] = field(default_factory=list)
    dedupe_key: str = ""
    provenance: KnowledgeProvenance = field(default_factory=KnowledgeProvenance)


@dataclass
class JudgmentLogEntry:
    log_id: str
    entry_type: str
    summary: str
    related_refs: list[dict[str, Any]] = field(default_factory=list)
    outcome: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    provenance: KnowledgeProvenance = field(default_factory=KnowledgeProvenance)
