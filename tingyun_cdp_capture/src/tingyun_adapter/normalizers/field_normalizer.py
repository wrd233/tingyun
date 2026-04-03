from __future__ import annotations

from typing import Any

from .metric_normalizer import normalize_metric_fields
from .op_name_decoder import decode_op_name


def normalize_record(record: dict[str, Any]) -> dict[str, Any]:
    normalized = normalize_metric_fields(record)
    if "throught" in normalized and "throughput" not in normalized:
        normalized["throughput"] = normalized["throught"]
    op_name = normalized.get("opName") or normalized.get("op_name")
    if op_name:
        decoded = decode_op_name(str(op_name))
        normalized["op_name_raw"] = decoded.raw
        normalized["op_name_decoded"] = decoded.decoded
        normalized["op_name_is_encoded"] = decoded.is_encoded
    return normalized


def normalize_records(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [normalize_record(item) for item in items]


def unwrap_data(payload: Any) -> Any:
    if isinstance(payload, dict) and "data" in payload:
        return payload["data"]
    return payload
