from __future__ import annotations

from typing import Any, Optional


def _to_float(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return float(int(value))
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return None


def _to_int(value: Any) -> Optional[int]:
    numeric = _to_float(value)
    if numeric is None:
        return None
    return int(numeric)


def normalize_response_time(record: dict[str, Any]) -> Optional[float]:
    for key in ("response_time_ms", "response", "respTime", "responseTime", "responseTimeMillisecondAvg", "actionRespTime"):
        numeric = _to_float(record.get(key))
        if numeric is not None:
            return numeric
    return None


def normalize_total_response_time(record: dict[str, Any]) -> Optional[float]:
    for key in ("total_response_time_ms", "totalResponse", "totalResptime", "totalResponseTime"):
        numeric = _to_float(record.get(key))
        if numeric is not None:
            return numeric
    return None


def normalize_throughput(record: dict[str, Any]) -> Optional[float]:
    for key in ("throughput", "throught", "tps", "productthrought", "maxThrought"):
        numeric = _to_float(record.get(key))
        if numeric is not None:
            return numeric
    return None


def normalize_error_count(record: dict[str, Any]) -> Optional[int]:
    for key in ("error_count", "errorCount", "exceptionCount"):
        numeric = _to_int(record.get(key))
        if numeric is not None:
            return numeric
    return None


def normalize_slow_count(record: dict[str, Any]) -> Optional[int]:
    for key in ("slow_count", "slowCount"):
        numeric = _to_int(record.get(key))
        if numeric is not None:
            return numeric
    return None


def normalize_trace_status(record: dict[str, Any]) -> Optional[bool]:
    for key in ("is_slow_trace", "isSlowTrace", "traceStatus", "status"):
        value = record.get(key)
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"true", "false"}:
                return normalized == "true"
    return None


def normalize_metric_fields(record: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(record)
    response_time = normalize_response_time(record)
    if response_time is not None:
        normalized["response_time_ms"] = response_time
    total_response_time = normalize_total_response_time(record)
    if total_response_time is not None:
        normalized["total_response_time_ms"] = total_response_time
    throughput = normalize_throughput(record)
    if throughput is not None:
        normalized["throughput"] = throughput
    error_count = normalize_error_count(record)
    if error_count is not None:
        normalized["error_count"] = error_count
    slow_count = normalize_slow_count(record)
    if slow_count is not None:
        normalized["slow_count"] = slow_count
    trace_status = normalize_trace_status(record)
    if trace_status is not None:
        normalized["trace_status"] = trace_status
    return normalized
