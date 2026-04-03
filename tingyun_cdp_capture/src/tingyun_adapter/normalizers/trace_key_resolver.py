from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass(frozen=True)
class ResolvedTraceKeys:
    trace_id_numeric: Optional[str]
    trace_guid: Optional[str]
    action_guid: Optional[str]
    request_id: Optional[str]
    query_timestamp: Optional[str]


def _string_or_none(value: Any) -> Optional[str]:
    if value is None or value == "":
        return None
    return str(value)


def _numeric_string_or_none(value: Any) -> Optional[str]:
    text = _string_or_none(value)
    if text and text.isdigit():
        return text
    return None


def resolve_trace_keys(record: dict[str, Any], *, query_timestamp: Any = None) -> ResolvedTraceKeys:
    numeric_trace_id = _numeric_string_or_none(record.get("traceId")) or _numeric_string_or_none(record.get("id"))
    trace_guid = _string_or_none(record.get("traceGuid"))
    action_guid = _string_or_none(record.get("actionGuid"))
    request_id = _string_or_none(record.get("requestId"))

    if trace_guid is None and request_id and not request_id.isdigit():
        trace_guid = request_id
    if action_guid is None and request_id and not request_id.isdigit():
        action_guid = request_id

    query_ts = _string_or_none(query_timestamp) or _string_or_none(record.get("queryTimestamp")) or _string_or_none(record.get("timestamp"))
    return ResolvedTraceKeys(
        trace_id_numeric=numeric_trace_id,
        trace_guid=trace_guid,
        action_guid=action_guid,
        request_id=request_id,
        query_timestamp=query_ts,
    )
