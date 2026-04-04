from __future__ import annotations

import base64
from dataclasses import dataclass


@dataclass(frozen=True)
class DecodedOpName:
    raw: str
    decoded: str
    is_encoded: bool


def decode_op_name(value: str | None) -> DecodedOpName:
    if not value:
        return DecodedOpName(raw="", decoded="", is_encoded=False)
    if not value.startswith("tyBase64_"):
        return DecodedOpName(raw=value, decoded=value, is_encoded=False)
    encoded = value[len("tyBase64_") :]
    padding = "=" * ((4 - len(encoded) % 4) % 4)
    decoded = base64.b64decode(encoded + padding).decode("utf-8", errors="replace")
    return DecodedOpName(raw=value, decoded=decoded, is_encoded=True)
