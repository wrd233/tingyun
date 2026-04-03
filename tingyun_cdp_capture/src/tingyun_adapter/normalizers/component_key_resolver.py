from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass(frozen=True)
class ResolvedComponentKeys:
    biz_system_id: Optional[int]
    component_type: Optional[str]
    component_subtype: Optional[str]
    component_name: Optional[str]
    metric_category: Optional[str]


def _int_or_none(value: Any) -> Optional[int]:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def resolve_component_keys(record: dict[str, Any], *, component_type: str | None = None) -> ResolvedComponentKeys:
    return ResolvedComponentKeys(
        biz_system_id=_int_or_none(record.get("bizSystemId")),
        component_type=component_type or record.get("componentType"),
        component_subtype=record.get("componentSubtype"),
        component_name=record.get("componentName") or record.get("addressSplit") or record.get("databaseName"),
        metric_category=record.get("metricCategory"),
    )
