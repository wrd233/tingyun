from __future__ import annotations

from typing import Any, Optional

from tingyun_adapter.domain.models.entities import Relation


def build_relation(
    *,
    subject_type: str,
    subject_id: str,
    relation_type: str,
    object_type: str,
    object_id: str,
    attributes: Optional[dict[str, Any]] = None,
) -> Relation:
    return Relation(
        subject_type=subject_type,
        subject_id=subject_id,
        relation_type=relation_type,
        object_type=object_type,
        object_id=object_id,
        attributes=attributes or {},
    )
