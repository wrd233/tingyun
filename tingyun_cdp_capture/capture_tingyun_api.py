#!/usr/bin/env python3
"""Capture browser requests from Chrome DevTools Protocol and catalog /server-api endpoints."""

import argparse
import asyncio
import base64
import hashlib
import json
import os
import re
import shlex
import signal
import sys
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import parse_qsl, urlencode, urlsplit
from urllib.request import urlopen


UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$"
)
JWT_RE = re.compile(r"^[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$")
HEX_RE = re.compile(r"^[0-9a-fA-F]{20,}$")
ISO_DATETIME_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}(?:[ T]\d{2}:\d{2}(?::\d{2})?(?:\.\d+)?)?(?:Z|[+-]\d{2}:\d{2})?$"
)
KEYWORDS_REQUEST = {
    "query": "query",
    "list": "list",
    "detail": "detail",
    "overview": "overview",
    "graph": "graph",
    "topology": "topology",
    "error": "error",
    "trace": "trace",
    "request": "request",
    "application": "application",
    "service": "service",
    "slow": "slow",
    "exception": "exception",
    "dashboard": "dashboard",
    "node": "node",
    "call": "call",
    "metric": "metric",
}
HEADER_SKIP = {
    "host",
    "connection",
    "content-length",
    "accept-encoding",
    "accept-language",
    "user-agent",
    "origin",
    "referer",
    "cookie",
    "sec-fetch-dest",
    "sec-fetch-mode",
    "sec-fetch-site",
    "sec-fetch-user",
    "sec-ch-ua",
    "sec-ch-ua-mobile",
    "sec-ch-ua-platform",
    "pragma",
    "cache-control",
}
SENSITIVE_KEY_PARTS = {
    "token",
    "authorization",
    "cookie",
    "secret",
    "password",
    "session",
    "ticket",
    "credential",
}
NORMALIZE_KEY_PARTS = {
    "time",
    "date",
    "timestamp",
    "id",
    "uuid",
    "trace",
    "span",
    "random",
    "nonce",
    "requestid",
    "builtinrequestid",
}
DEFAULT_RESPONSE_BYTES = 100_000
DEFAULT_EXAMPLE_COUNT = 3
DEFAULT_RAW_LOG_DIR = "./raw_logs"
DEFAULT_NETWORK_TOTAL_BUFFER_BYTES = 50_000_000
DEFAULT_NETWORK_RESOURCE_BUFFER_BYTES = 5_000_000


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def canonical_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def truncate_text(value: str, limit: int = 2000) -> str:
    if len(value) <= limit:
        return value
    return value[:limit] + "...<truncated>"


def looks_like_datetime(value: str) -> bool:
    return bool(ISO_DATETIME_RE.match(value.strip()))


def looks_like_hex(value: str) -> bool:
    return bool(HEX_RE.match(value.strip()))


def key_is_sensitive(key: str) -> bool:
    lowered = key.lower()
    return any(part in lowered for part in SENSITIVE_KEY_PARTS)


def key_is_dynamic(key: str) -> bool:
    lowered = key.lower().replace("_", "").replace("-", "")
    return any(part in lowered for part in NORMALIZE_KEY_PARTS)


def normalize_primitive(value: Any, key_path: str, dynamic_fields: List[str]) -> Any:
    key_name = key_path.split(".")[-1] if key_path else ""
    if isinstance(value, str):
        text = value.strip()
        if key_is_sensitive(key_name) or JWT_RE.match(text):
            dynamic_fields.append(key_path or "<root>")
            return "<REDACTED>"
        if UUID_RE.match(text):
            dynamic_fields.append(key_path or "<root>")
            return "<UUID>"
        if looks_like_datetime(text):
            dynamic_fields.append(key_path or "<root>")
            return "<DATETIME>"
        if looks_like_hex(text):
            dynamic_fields.append(key_path or "<root>")
            return "<HEX>"
        if key_is_dynamic(key_name):
            dynamic_fields.append(key_path or "<root>")
            return "<DYNAMIC>"
        return truncate_text(value)
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, (int, float)):
        if key_is_dynamic(key_name):
            dynamic_fields.append(key_path or "<root>")
            return "<DYNAMIC_NUMBER>"
        if isinstance(value, int) and value > 10_000_000_000:
            dynamic_fields.append(key_path or "<root>")
            return "<TIMESTAMP>"
        return value
    return value


def normalize_structure(value: Any, key_path: str = "", dynamic_fields: Optional[List[str]] = None) -> Any:
    dynamic_fields = dynamic_fields if dynamic_fields is not None else []
    if isinstance(value, dict):
        normalized: Dict[str, Any] = {}
        for key, item in value.items():
            next_path = f"{key_path}.{key}" if key_path else str(key)
            normalized[str(key)] = normalize_structure(item, next_path, dynamic_fields)
        return normalized
    if isinstance(value, list):
        normalized_list = []
        for index, item in enumerate(value):
            next_path = f"{key_path}[{index}]"
            normalized_list.append(normalize_structure(item, next_path, dynamic_fields))
        return normalized_list
    return normalize_primitive(value, key_path, dynamic_fields)


def redact_structure(value: Any, key_path: str = "") -> Any:
    key_name = key_path.split(".")[-1] if key_path else ""
    if isinstance(value, dict):
        redacted: Dict[str, Any] = {}
        for key, item in value.items():
            next_path = f"{key_path}.{key}" if key_path else str(key)
            redacted[str(key)] = redact_structure(item, next_path)
        return redacted
    if isinstance(value, list):
        return [redact_structure(item, f"{key_path}[{index}]") for index, item in enumerate(value)]
    if isinstance(value, str):
        if key_is_sensitive(key_name) or JWT_RE.match(value.strip()):
            return "<REDACTED>"
        return truncate_text(value)
    return value


def pairs_to_object(pairs: List[Tuple[str, str]]) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            existing = result[key]
            if isinstance(existing, list):
                existing.append(value)
            else:
                result[key] = [existing, value]
        else:
            result[key] = value
    return result


def parse_maybe_json(raw_text: str) -> Tuple[Any, str]:
    stripped = raw_text.strip()
    if not stripped:
        return None, "empty"
    try:
        return json.loads(stripped), "json"
    except json.JSONDecodeError:
        return stripped, "text"


def parse_body(content_type: str, post_data: Optional[str]) -> Tuple[Any, str]:
    if post_data is None:
        return None, "none"
    if "application/json" in content_type:
        return parse_maybe_json(post_data)
    if "application/x-www-form-urlencoded" in content_type:
        pairs = parse_qsl(post_data, keep_blank_values=True)
        return pairs_to_object(pairs), "form"
    return parse_maybe_json(post_data)


def parse_query(url: str) -> Dict[str, Any]:
    parsed = urlsplit(url)
    return pairs_to_object(parse_qsl(parsed.query, keep_blank_values=True))


def sanitize_header_value(name: str, value: str) -> str:
    lowered = name.lower()
    if lowered == "authorization":
        if value.lower().startswith("bearer "):
            return "Bearer ${TOKEN}"
        return "<REDACTED>"
    if lowered == "builtinrequestid":
        return "${BUILTIN_REQUEST_ID}"
    if lowered == "cookie":
        return "<REDACTED>"
    return truncate_text(value, 500)


def select_request_headers(headers: Dict[str, str]) -> Dict[str, str]:
    selected: Dict[str, str] = {}
    for name, value in headers.items():
        lowered = name.lower()
        if lowered in HEADER_SKIP:
            continue
        if lowered in {"accept", "content-type", "authorization", "builtinrequestid"} or lowered.startswith("x-"):
            selected[name] = sanitize_header_value(name, str(value))
    return dict(sorted(selected.items(), key=lambda item: item[0].lower()))


def build_sample_curl(url: str, method: str, headers: Dict[str, str], body: Any, body_kind: str) -> str:
    parts = ["curl", shlex.quote(url), "-X", shlex.quote(method)]
    for key, value in headers.items():
        parts.extend(["-H", shlex.quote(f"{key}: {value}")])
    if body is not None and method.upper() != "GET":
        if body_kind == "json":
            payload = canonical_json(body)
        elif body_kind == "form":
            if isinstance(body, dict):
                payload = urlencode(body, doseq=True)
            else:
                payload = str(body)
        elif isinstance(body, str):
            payload = body
        else:
            payload = canonical_json(body)
        parts.extend(["--data-raw", shlex.quote(payload)])
    return " ".join(parts)


def sanitize_path_fragment(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("._-") or "variant"


def count_populated_fields(value: Any) -> int:
    if value is None:
        return 0
    if isinstance(value, dict):
        score = 1 if value else 0
        for item in value.values():
            score += count_populated_fields(item)
        return score
    if isinstance(value, list):
        score = 1 if value else 0
        for item in value:
            score += count_populated_fields(item)
        return score
    if isinstance(value, str):
        return 1 if value.strip() else 0
    return 1


def purpose_from_metric(metric: str) -> str:
    text = metric.replace("_", " ").strip()
    return f"Likely used to query {text} related data"


def infer_purpose(relative_path: str, query_obj: Dict[str, Any], body: Any) -> Tuple[str, List[str]]:
    basis: List[str] = []
    if isinstance(body, dict) and isinstance(body.get("metric"), str):
        metric = body["metric"]
        basis.append(f"body.metric={metric}")
        if "labels" in body:
            basis.append("body.labels present")
        if "timePeriod" in body or "endTime" in body:
            basis.append("time range fields present")
        return purpose_from_metric(metric), basis

    tokens = [token for token in relative_path.split("/") if token]
    token_hints = [KEYWORDS_REQUEST[token] for token in tokens if token in KEYWORDS_REQUEST]
    if token_hints:
        purpose = "Likely related to " + " / ".join(token_hints)
    else:
        purpose = f"Likely related to {relative_path}"
    basis.append(f"path={relative_path}")
    if query_obj:
        basis.append("query params present")
    return purpose, basis


def summarize_body_keys(body: Any) -> List[str]:
    if isinstance(body, dict):
        return sorted(body.keys())
    return []


def ensure_parent_dir(path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)


def make_relative_path(api_prefix: str, full_url: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    parsed = urlsplit(full_url)
    prefix = urlsplit(api_prefix)
    if parsed.scheme != prefix.scheme or parsed.netloc != prefix.netloc:
        return None, None, None
    if not parsed.path.startswith(prefix.path):
        return None, None, None
    relative = parsed.path[len(prefix.path) :].lstrip("/") or "__root__"
    path_only = parsed.path
    host_base = f"{parsed.scheme}://{parsed.netloc}"
    return relative, path_only, host_base


@dataclass
class VariantRecord:
    key: str
    count_seen: int = 0
    example: Any = None
    normalized_example: Any = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    dynamic_fields: List[str] = field(default_factory=list)

    def observe(self, example: Any, normalized_example: Any, metadata: Dict[str, Any], dynamic_fields: List[str]) -> None:
        self.count_seen += 1
        if self.example is None:
            self.example = example
        if self.normalized_example is None:
            self.normalized_example = normalized_example
        if metadata:
            for key, value in metadata.items():
                self.metadata.setdefault(key, value)
        for field_name in dynamic_fields:
            if field_name not in self.dynamic_fields:
                self.dynamic_fields.append(field_name)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "count_seen": self.count_seen,
            "example": self.example,
            "normalized_example": self.normalized_example,
            "metadata": self.metadata,
            "dynamic_fields": sorted(self.dynamic_fields),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VariantRecord":
        return cls(
            key=data["key"],
            count_seen=int(data.get("count_seen", 0)),
            example=data.get("example"),
            normalized_example=data.get("normalized_example"),
            metadata=dict(data.get("metadata", {})),
            dynamic_fields=list(data.get("dynamic_fields", [])),
        )


@dataclass
class PageContextCandidate:
    captured_page_url: Optional[str] = None
    document_url: Optional[str] = None
    frame_url: Optional[str] = None
    page_title: Optional[str] = None
    request_url: Optional[str] = None
    request_method: Optional[str] = None
    request_timestamp: Optional[str] = None
    tab_target_id: Optional[str] = None
    frame_id: Optional[str] = None
    referrer: Optional[str] = None
    initiator_url: Optional[str] = None
    initiator_type: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "captured_page_url": self.captured_page_url,
            "document_url": self.document_url,
            "frame_url": self.frame_url,
            "page_title": self.page_title,
            "request_url": self.request_url,
            "request_method": self.request_method,
            "request_timestamp": self.request_timestamp,
            "tab_target_id": self.tab_target_id,
            "frame_id": self.frame_id,
            "referrer": self.referrer,
            "initiator_url": self.initiator_url,
            "initiator_type": self.initiator_type,
        }

    def populated_field_count(self) -> int:
        score = 0
        for key, value in self.to_dict().items():
            if key == "request_timestamp":
                continue
            if isinstance(value, str):
                score += 1 if value.strip() else 0
            elif value is not None:
                score += 1
        return score

    def has_page_location(self) -> bool:
        for value in (self.captured_page_url, self.document_url, self.frame_url):
            if isinstance(value, str) and value.strip():
                return True
        return False

    def identity_key(self) -> str:
        return canonical_json(
            {
                "captured_page_url": self.captured_page_url,
                "document_url": self.document_url,
                "frame_url": self.frame_url,
                "page_title": self.page_title,
                "tab_target_id": self.tab_target_id,
                "frame_id": self.frame_id,
                "referrer": self.referrer,
                "initiator_url": self.initiator_url,
                "initiator_type": self.initiator_type,
            }
        )

    @classmethod
    def from_mapping(cls, data: Optional[Dict[str, Any]]) -> "PageContextCandidate":
        payload = data or {}
        return cls(
            captured_page_url=payload.get("captured_page_url"),
            document_url=payload.get("document_url"),
            frame_url=payload.get("frame_url"),
            page_title=payload.get("page_title"),
            request_url=payload.get("request_url"),
            request_method=payload.get("request_method"),
            request_timestamp=payload.get("request_timestamp"),
            tab_target_id=payload.get("tab_target_id"),
            frame_id=payload.get("frame_id"),
            referrer=payload.get("referrer"),
            initiator_url=payload.get("initiator_url"),
            initiator_type=payload.get("initiator_type"),
        )


@dataclass
class PageContextSummary:
    latest: Optional[PageContextCandidate] = None
    latest_non_empty: Optional[PageContextCandidate] = None
    candidates: List[PageContextCandidate] = field(default_factory=list)

    def observe(self, candidate: PageContextCandidate, max_candidates: int) -> None:
        self.latest = candidate
        if candidate.has_page_location():
            self.latest_non_empty = candidate
        identity = candidate.identity_key()
        filtered = [item for item in self.candidates if item.identity_key() != identity]
        filtered.insert(0, candidate)
        self.candidates = filtered[:max_candidates]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "latest": self.latest.to_dict() if self.latest is not None else None,
            "latest_non_empty": self.latest_non_empty.to_dict() if self.latest_non_empty is not None else None,
            "candidates": [item.to_dict() for item in self.candidates],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PageContextSummary":
        return cls(
            latest=PageContextCandidate.from_mapping(data.get("latest")) if data.get("latest") else None,
            latest_non_empty=PageContextCandidate.from_mapping(data.get("latest_non_empty"))
            if data.get("latest_non_empty")
            else None,
            candidates=[PageContextCandidate.from_mapping(item) for item in data.get("candidates", [])],
        )


@dataclass
class MethodRecord:
    method: str
    count_seen: int = 0
    first_seen: Optional[str] = None
    last_seen: Optional[str] = None
    resource_types: Counter = field(default_factory=Counter)
    status_codes: Counter = field(default_factory=Counter)
    mime_types: Counter = field(default_factory=Counter)
    observed_metrics: List[str] = field(default_factory=list)
    request_headers_template: Dict[str, str] = field(default_factory=dict)
    query_variants: Dict[str, VariantRecord] = field(default_factory=dict)
    body_variants: Dict[str, VariantRecord] = field(default_factory=dict)
    sample_requests: List[Dict[str, Any]] = field(default_factory=list)
    sample_responses: List[Dict[str, Any]] = field(default_factory=list)
    inferred_purpose: str = ""
    inference_basis: List[str] = field(default_factory=list)
    replay: Dict[str, Any] = field(default_factory=dict)
    page_context_summary: PageContextSummary = field(default_factory=PageContextSummary)

    def observe(self, observation: Dict[str, Any], max_examples: int) -> None:
        seen_at = observation["seen_at"]
        self.count_seen += 1
        if self.first_seen is None:
            self.first_seen = seen_at
        self.last_seen = seen_at
        self.resource_types[observation["resource_type"]] += 1
        if observation.get("response_status") is not None:
            self.status_codes[str(observation["response_status"])] += 1
        if observation.get("response_mime_type"):
            self.mime_types[observation["response_mime_type"]] += 1

        for key, value in observation["request_headers_template"].items():
            self.request_headers_template.setdefault(key, value)

        metric = observation.get("metric")
        if metric and metric not in self.observed_metrics:
            self.observed_metrics.append(metric)
            self.observed_metrics.sort()

        query_variant_key = observation["query_variant_key"]
        query_variant = self.query_variants.setdefault(query_variant_key, VariantRecord(query_variant_key))
        query_variant.observe(
            observation["query_example"],
            observation["query_normalized"],
            observation["query_metadata"],
            observation["query_dynamic_fields"],
        )

        if observation["body_variant_key"] is not None:
            body_variant = self.body_variants.setdefault(
                observation["body_variant_key"], VariantRecord(observation["body_variant_key"])
            )
            body_variant.observe(
                observation["body_example"],
                observation["body_normalized"],
                observation["body_metadata"],
                observation["body_dynamic_fields"],
            )

        self._append_unique_sample(self.sample_requests, observation["sample_request"], max_examples)
        if observation.get("sample_response") is not None:
            self._append_unique_sample(self.sample_responses, observation["sample_response"], max_examples)
        self.page_context_summary.observe(
            PageContextCandidate.from_mapping(observation.get("page_context")),
            max_examples,
        )

        inferred_purpose, inference_basis = infer_purpose(
            observation["relative_path"], observation["query_example"], observation["body_example"]
        )
        if (not self.inferred_purpose) or ("body.metric" in " ".join(inference_basis) and "body.metric" not in " ".join(self.inference_basis)):
            self.inferred_purpose = inferred_purpose
            self.inference_basis = inference_basis

        if not self.replay:
            self.replay = {
                "sample_curl": build_sample_curl(
                    observation["full_url"],
                    observation["method"],
                    observation["request_headers_template"],
                    observation["body_example"],
                    observation["body_kind"],
                ),
                "url": observation["full_url"],
                "required_headers": observation["request_headers_template"],
                "body_template": observation["body_example"],
                "dynamic_fields": sorted(set(observation["query_dynamic_fields"] + observation["body_dynamic_fields"])),
            }

    @staticmethod
    def _append_unique_sample(bucket: List[Dict[str, Any]], sample: Dict[str, Any], max_examples: int) -> None:
        serialized = canonical_json(sample)
        for existing in bucket:
            if canonical_json(existing) == serialized:
                return
        bucket.append(sample)
        if len(bucket) > max_examples:
            del bucket[max_examples:]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "method": self.method,
            "count_seen": self.count_seen,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "resource_types": dict(self.resource_types),
            "status_codes": dict(self.status_codes),
            "mime_types": dict(self.mime_types),
            "observed_metrics": self.observed_metrics,
            "request_headers_template": self.request_headers_template,
            "query_variants": [variant.to_dict() for variant in sorted(self.query_variants.values(), key=lambda item: item.key)],
            "body_variants": [variant.to_dict() for variant in sorted(self.body_variants.values(), key=lambda item: item.key)],
            "sample_requests": self.sample_requests,
            "sample_responses": self.sample_responses,
            "inferred_purpose": self.inferred_purpose,
            "inference_basis": self.inference_basis,
            "replay": self.replay,
            "page_context_summary": self.page_context_summary.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MethodRecord":
        record = cls(
            method=data["method"],
            count_seen=int(data.get("count_seen", 0)),
            first_seen=data.get("first_seen"),
            last_seen=data.get("last_seen"),
            resource_types=Counter(data.get("resource_types", {})),
            status_codes=Counter(data.get("status_codes", {})),
            mime_types=Counter(data.get("mime_types", {})),
            observed_metrics=list(data.get("observed_metrics", [])),
            request_headers_template=dict(data.get("request_headers_template", {})),
            sample_requests=list(data.get("sample_requests", [])),
            sample_responses=list(data.get("sample_responses", [])),
            inferred_purpose=data.get("inferred_purpose", ""),
            inference_basis=list(data.get("inference_basis", [])),
            replay=dict(data.get("replay", {})),
            page_context_summary=PageContextSummary.from_dict(data.get("page_context_summary", {}))
            if data.get("page_context_summary")
            else PageContextSummary(),
        )
        for variant in data.get("query_variants", []):
            loaded = VariantRecord.from_dict(variant)
            record.query_variants[loaded.key] = loaded
        for variant in data.get("body_variants", []):
            loaded = VariantRecord.from_dict(variant)
            record.body_variants[loaded.key] = loaded
        return record


@dataclass
class EndpointRecord:
    relative_path: str
    path: str
    count_seen: int = 0
    first_seen: Optional[str] = None
    last_seen: Optional[str] = None
    hosts_seen: Counter = field(default_factory=Counter)
    methods: Dict[str, MethodRecord] = field(default_factory=dict)

    def observe(self, observation: Dict[str, Any], max_examples: int) -> None:
        seen_at = observation["seen_at"]
        self.count_seen += 1
        if self.first_seen is None:
            self.first_seen = seen_at
        self.last_seen = seen_at
        self.hosts_seen[observation["host_base"]] += 1
        method_record = self.methods.setdefault(observation["method"], MethodRecord(observation["method"]))
        method_record.observe(observation, max_examples)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "relative_path": self.relative_path,
            "path": self.path,
            "count_seen": self.count_seen,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "hosts_seen": dict(self.hosts_seen),
            "methods": {
                method: record.to_dict()
                for method, record in sorted(self.methods.items(), key=lambda item: item[0])
            },
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EndpointRecord":
        record = cls(
            relative_path=data["relative_path"],
            path=data["path"],
            count_seen=int(data.get("count_seen", 0)),
            first_seen=data.get("first_seen"),
            last_seen=data.get("last_seen"),
            hosts_seen=Counter(data.get("hosts_seen", {})),
        )
        for method, method_data in data.get("methods", {}).items():
            record.methods[method] = MethodRecord.from_dict(method_data)
        return record


class EndpointCatalog:
    def __init__(self, output_dir: str, max_examples: int):
        self.output_dir = output_dir
        self.max_examples = max_examples
        self.endpoints: Dict[str, EndpointRecord] = {}

    def load_existing(self) -> None:
        if not os.path.isdir(self.output_dir):
            return
        for root, _dirs, files in os.walk(self.output_dir):
            for filename in files:
                if not filename.endswith(".json") or filename == "index.json":
                    continue
                path = os.path.join(root, filename)
                with open(path, "r", encoding="utf-8") as handle:
                    data = json.load(handle)
                record = EndpointRecord.from_dict(data)
                self.endpoints[record.relative_path] = record

    def observe(self, observation: Dict[str, Any]) -> str:
        record = self.endpoints.setdefault(
            observation["relative_path"], EndpointRecord(observation["relative_path"], observation["path"])
        )
        record.observe(observation, self.max_examples)
        return self.write_endpoint(record)

    def endpoint_file_path(self, relative_path: str) -> str:
        return os.path.join(self.output_dir, f"{relative_path}.json")

    def write_endpoint(self, record: EndpointRecord) -> str:
        file_path = self.endpoint_file_path(record.relative_path)
        ensure_parent_dir(file_path)
        with open(file_path, "w", encoding="utf-8") as handle:
            json.dump(record.to_dict(), handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
        return file_path

    def write_index(self) -> str:
        index_data = {
            "generated_at": now_iso(),
            "total_endpoint_paths": len(self.endpoints),
            "endpoints": [],
        }
        for relative_path, record in sorted(self.endpoints.items(), key=lambda item: item[0]):
            methods = sorted(record.methods.keys())
            purposes = {
                method: record.methods[method].inferred_purpose
                for method in methods
                if record.methods[method].inferred_purpose
            }
            index_data["endpoints"].append(
                {
                    "relative_path": relative_path,
                    "path": record.path,
                    "count_seen": record.count_seen,
                    "methods": methods,
                    "file": os.path.relpath(self.endpoint_file_path(relative_path), self.output_dir),
                    "purposes": purposes,
                }
            )

        file_path = os.path.join(self.output_dir, "index.json")
        ensure_parent_dir(file_path)
        with open(file_path, "w", encoding="utf-8") as handle:
            json.dump(index_data, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
        return file_path


class RawLogCatalog:
    def __init__(self, raw_log_dir: str):
        self.raw_log_dir = raw_log_dir

    @staticmethod
    def build_signature(observation: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "method": observation["method"],
            "relative_path": observation["relative_path"],
            "query": observation["query_normalized"],
            "body": observation["body_normalized"],
        }

    @staticmethod
    def infer_variant_label(observation: Dict[str, Any]) -> str:
        if observation.get("metric"):
            return sanitize_path_fragment(str(observation["metric"]))
        query_keys = observation.get("query_metadata", {}).get("keys", [])
        if query_keys:
            return sanitize_path_fragment("__".join(query_keys[:3]))
        body_keys = observation.get("body_metadata", {}).get("top_level_keys", [])
        if body_keys:
            return sanitize_path_fragment("__".join(body_keys[:3]))
        return "variant"

    def raw_log_file_path(self, raw_record: Dict[str, Any]) -> str:
        signature_obj = raw_record.get("signature")
        if signature_obj is None:
            signature_obj = self.build_signature(raw_record)
        signature = canonical_json(signature_obj)
        short_hash = hashlib.sha1(signature.encode("utf-8")).hexdigest()[:12]
        label = self.infer_variant_label(raw_record)
        relative_dir = os.path.join(self.raw_log_dir, raw_record["relative_path"])
        filename = f"{raw_record['method']}__{label}__{short_hash}.json"
        return os.path.join(relative_dir, filename)

    @staticmethod
    def completeness_score(raw_record: Dict[str, Any]) -> int:
        request = raw_record.get("request", {})
        response = raw_record.get("response", {})
        score = 0
        score += 100 if response.get("status") is not None else 0
        score += 50 if response.get("body") is not None else 0
        score += 20 if request.get("body") is not None else 0
        score += min(int(response.get("encoded_data_length", 0) or 0), 100_000) // 200
        score += len(request.get("headers", {}))
        score += len(response.get("headers", {}))
        score += count_populated_fields(request.get("query")) * 2
        score += count_populated_fields(request.get("body")) * 2
        score += count_populated_fields(response.get("body")) * 3
        if response.get("error"):
            score += 5
        return score

    @staticmethod
    def _load_existing(path: str) -> Optional[Dict[str, Any]]:
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)

    @staticmethod
    def _merge_page_context(existing_record: Dict[str, Any], incoming_record: Dict[str, Any]) -> None:
        existing_summary = PageContextSummary.from_dict(
            existing_record.get("page_context_summary")
            or existing_record.get("capture", {}).get("page_context_summary")
            or {}
        )
        incoming_context = PageContextCandidate.from_mapping(incoming_record.get("page_context"))
        existing_summary.observe(incoming_context, max_candidates=10)
        summary_dict = existing_summary.to_dict()
        incoming_record["page_context_summary"] = summary_dict
        incoming_record.setdefault("capture", {})["page_context_summary"] = summary_dict

    def observe(self, raw_record: Dict[str, Any]) -> Tuple[str, bool]:
        file_path = self.raw_log_file_path(raw_record)
        ensure_parent_dir(file_path)
        raw_record["capture"]["raw_log_file"] = os.path.relpath(file_path, self.raw_log_dir)
        raw_record["capture"]["completeness_score"] = self.completeness_score(raw_record)

        existing = self._load_existing(file_path)
        self._merge_page_context(existing or {}, raw_record)
        if existing is not None:
            existing_score = int(existing.get("capture", {}).get("completeness_score", 0))
            existing_seen = int(existing.get("capture", {}).get("seen_count", 1))
            raw_record["capture"]["seen_count"] = existing_seen + 1
            raw_record["capture"]["first_seen_at"] = existing.get("capture", {}).get(
                "first_seen_at", raw_record["capture"]["captured_at"]
            )
            if raw_record["capture"]["completeness_score"] < existing_score:
                existing["capture"]["seen_count"] = existing_seen + 1
                existing["capture"]["last_seen_at"] = raw_record["capture"]["captured_at"]
                merged_summary = raw_record.get("page_context_summary") or raw_record.get("capture", {}).get(
                    "page_context_summary"
                )
                if merged_summary is not None:
                    existing["page_context_summary"] = merged_summary
                    existing.setdefault("capture", {})["page_context_summary"] = merged_summary
                with open(file_path, "w", encoding="utf-8") as handle:
                    json.dump(existing, handle, ensure_ascii=False, indent=2, sort_keys=True)
                    handle.write("\n")
                return file_path, False
        else:
            raw_record["capture"]["seen_count"] = 1
            raw_record["capture"]["first_seen_at"] = raw_record["capture"]["captured_at"]

        raw_record["capture"]["last_seen_at"] = raw_record["capture"]["captured_at"]
        with open(file_path, "w", encoding="utf-8") as handle:
            json.dump(raw_record, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
        return file_path, True


class CDPClient:
    def __init__(self, websocket_url: str):
        self.websocket_url = websocket_url
        self.websocket: Any = None
        self.message_id = 0
        self.pending: Dict[int, asyncio.Future] = {}
        self.event_queue: asyncio.Queue = asyncio.Queue()
        self.receiver_task: Optional[asyncio.Task] = None

    async def connect(self) -> None:
        try:
            import websockets
        except ImportError as exc:
            raise RuntimeError(
                "Missing dependency 'websockets'. Run: python3 -m pip install -r requirements.txt"
            ) from exc
        self.websocket = await websockets.connect(self.websocket_url, max_size=None)
        self.receiver_task = asyncio.create_task(self._receiver_loop())

    async def close(self) -> None:
        if self.receiver_task is not None:
            self.receiver_task.cancel()
            try:
                await self.receiver_task
            except asyncio.CancelledError:
                pass
        if self.websocket is not None:
            await self.websocket.close()

    async def send_command(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if self.websocket is None:
            raise RuntimeError("CDP client is not connected")
        self.message_id += 1
        payload = {"id": self.message_id, "method": method, "params": params or {}}
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        self.pending[self.message_id] = future
        await self.websocket.send(json.dumps(payload))
        result = await future
        return result

    async def _receiver_loop(self) -> None:
        assert self.websocket is not None
        try:
            async for raw_message in self.websocket:
                message = json.loads(raw_message)
                if "id" in message:
                    future = self.pending.pop(int(message["id"]), None)
                    if future is None:
                        continue
                    if "error" in message:
                        future.set_exception(RuntimeError(str(message["error"])))
                    else:
                        future.set_result(message.get("result", {}))
                else:
                    await self.event_queue.put(message)
        finally:
            for future in self.pending.values():
                if not future.done():
                    future.set_exception(RuntimeError("CDP connection closed"))
            self.pending.clear()
            await self.event_queue.put({"method": "__cdp_closed__", "params": {}})


@dataclass
class PendingRequest:
    request_id: str
    method: str
    url: str
    headers: Dict[str, str]
    post_data: Optional[str]
    resource_type: str
    wall_time: float
    response_status: Optional[int] = None
    response_mime_type: str = ""
    response_headers: Dict[str, Any] = field(default_factory=dict)
    encoded_data_length: int = 0
    response_body: Optional[Any] = None
    response_body_raw: Optional[Any] = None
    response_body_kind: str = "none"
    response_body_capture_error: Optional[str] = None
    response_error: Optional[str] = None
    document_url: Optional[str] = None
    frame_id: Optional[str] = None
    frame_url: Optional[str] = None
    page_title: Optional[str] = None
    captured_page_url: Optional[str] = None
    tab_target_id: Optional[str] = None
    referrer: Optional[str] = None
    initiator_url: Optional[str] = None
    initiator_type: Optional[str] = None


class CaptureSession:
    def __init__(
        self,
        cdp_client: CDPClient,
        catalog: EndpointCatalog,
        raw_log_catalog: RawLogCatalog,
        api_prefix: str,
        target_id: str,
        target_title: str,
        target_url: str,
        include_response_body: bool,
        max_response_bytes: int,
        network_total_buffer_bytes: int,
        network_resource_buffer_bytes: int,
        stop_requested: Optional[asyncio.Event],
        verbose: bool,
    ):
        self.cdp_client = cdp_client
        self.catalog = catalog
        self.raw_log_catalog = raw_log_catalog
        self.api_prefix = api_prefix.rstrip("/") + "/"
        self.target_id = target_id
        self.target_title = target_title
        self.target_url = target_url
        self.include_response_body = include_response_body
        self.max_response_bytes = max_response_bytes
        self.network_total_buffer_bytes = max(network_total_buffer_bytes, max_response_bytes * 4)
        self.network_resource_buffer_bytes = max(network_resource_buffer_bytes, max_response_bytes)
        self.verbose = verbose
        self.pending: Dict[str, PendingRequest] = {}
        self.stop_requested = stop_requested or asyncio.Event()
        self.frame_urls: Dict[str, str] = {}
        self.main_frame_id: Optional[str] = None
        self.cached_page_snapshot: Dict[str, Optional[str]] = {
            "href": target_url or None,
            "title": target_title or None,
            "referrer": None,
        }

    async def start(self) -> None:
        await self.cdp_client.send_command("Page.enable")
        try:
            await self.cdp_client.send_command("Runtime.enable")
        except Exception:
            pass
        network_params = {
            "maxPostDataSize": 1024 * 1024,
            "maxResourceBufferSize": self.network_resource_buffer_bytes,
            "maxTotalBufferSize": self.network_total_buffer_bytes,
        }
        try:
            await self.cdp_client.send_command(
                "Network.enable",
                {
                    **network_params,
                    "enableDurableMessages": True,
                },
            )
        except Exception:
            await self.cdp_client.send_command("Network.enable", network_params)
        await self._refresh_page_snapshot()

    async def run_forever(self) -> None:
        await self.start()
        while not self.stop_requested.is_set():
            try:
                event = await asyncio.wait_for(self.cdp_client.event_queue.get(), timeout=0.5)
            except asyncio.TimeoutError:
                continue
            await self.handle_event(event)
        self.catalog.write_index()

    async def handle_event(self, event: Dict[str, Any]) -> None:
        method = event.get("method")
        params = event.get("params", {})

        if method == "__cdp_closed__":
            print("CDP connection closed; stopping capture.", flush=True)
            self.stop_requested.set()
            return

        if method == "Network.requestWillBeSent":
            request = params.get("request", {})
            url = request.get("url", "")
            relative_path, _path, _host = make_relative_path(self.api_prefix, url)
            resource_type = params.get("type", "Unknown")
            if relative_path is None or resource_type not in {"XHR", "Fetch"}:
                return
            document_url = params.get("documentURL")
            frame_id = params.get("frameId")
            frame_url = self._frame_url_for(frame_id, document_url)
            page_snapshot = await self._snapshot_for_request(document_url=document_url, frame_id=frame_id)
            initiator = params.get("initiator", {})
            self.pending[params["requestId"]] = PendingRequest(
                request_id=params["requestId"],
                method=request.get("method", "GET").upper(),
                url=url,
                headers={str(key): str(value) for key, value in request.get("headers", {}).items()},
                post_data=request.get("postData"),
                resource_type=resource_type,
                wall_time=float(params.get("wallTime", 0.0)),
                document_url=document_url,
                frame_id=frame_id,
                frame_url=frame_url,
                page_title=page_snapshot.get("title"),
                captured_page_url=page_snapshot.get("href") or frame_url or document_url,
                tab_target_id=self.target_id,
                referrer=page_snapshot.get("referrer")
                or request.get("referrerPolicy")
                or request.get("headers", {}).get("Referer")
                or request.get("headers", {}).get("referer"),
                initiator_url=self._extract_initiator_url(initiator),
                initiator_type=initiator.get("type"),
            )
            return

        if method == "Page.frameNavigated":
            frame = params.get("frame", {})
            frame_id = frame.get("id")
            frame_url = frame.get("url")
            parent_id = frame.get("parentId")
            if frame_id and frame_url:
                self.frame_urls[str(frame_id)] = str(frame_url)
            if frame_id and not parent_id:
                self.main_frame_id = str(frame_id)
                self.cached_page_snapshot["href"] = str(frame_url) if frame_url else self.cached_page_snapshot.get("href")
                self.cached_page_snapshot["title"] = frame.get("name") or self.cached_page_snapshot.get("title")
                await self._refresh_page_snapshot()
            return

        if method == "Page.navigatedWithinDocument":
            frame_id = params.get("frameId")
            url = params.get("url")
            if frame_id and url:
                self.frame_urls[str(frame_id)] = str(url)
            if frame_id and str(frame_id) == self.main_frame_id and url:
                self.cached_page_snapshot["href"] = str(url)
                await self._refresh_page_snapshot()
            return

        if method == "Network.responseReceived":
            request_id = params.get("requestId")
            pending = self.pending.get(request_id)
            if pending is None:
                return
            response = params.get("response", {})
            pending.response_status = int(response.get("status", 0)) if response.get("status") is not None else None
            pending.response_mime_type = response.get("mimeType", "")
            pending.response_headers = dict(response.get("headers", {}))
            return

        if method == "Network.loadingFailed":
            request_id = params.get("requestId")
            pending = self.pending.get(request_id)
            if pending is None:
                return
            pending.response_error = params.get("errorText")
            await self._finalize_request(request_id)
            return

        if method == "Network.loadingFinished":
            request_id = params.get("requestId")
            pending = self.pending.get(request_id)
            if pending is None:
                return
            pending.encoded_data_length = int(params.get("encodedDataLength", 0))
            if pending.encoded_data_length <= self.max_response_bytes:
                await self._capture_response_body(pending)
            await self._finalize_request(request_id)

    async def _capture_response_body(self, pending: PendingRequest) -> None:
        mime_type = pending.response_mime_type or ""
        if mime_type and all(marker not in mime_type for marker in ("json", "text", "javascript")):
            pending.response_body_capture_error = f"skip_by_mime_type:{mime_type}"
            return
        last_error: Optional[str] = None
        for attempt in range(3):
            try:
                result = await self.cdp_client.send_command("Network.getResponseBody", {"requestId": pending.request_id})
                body_text = result.get("body", "")
                if result.get("base64Encoded"):
                    try:
                        decoded = base64.b64decode(body_text)
                        body_text = decoded.decode("utf-8")
                    except Exception as exc:
                        last_error = f"base64_decode_failed:{exc}"
                        await asyncio.sleep(0.1)
                        continue
                if body_text == "" and pending.encoded_data_length > 0:
                    last_error = f"empty_body_with_encoded_length:{pending.encoded_data_length}"
                    await asyncio.sleep(0.1)
                    continue
                parsed_body, parsed_kind = parse_maybe_json(body_text)
                pending.response_body_raw = parsed_body
                if isinstance(parsed_body, str):
                    parsed_body = truncate_text(parsed_body, 4000)
                else:
                    parsed_body = redact_structure(parsed_body)
                pending.response_body = parsed_body
                pending.response_body_kind = parsed_kind
                pending.response_body_capture_error = None
                return
            except Exception as exc:
                last_error = f"getResponseBody_failed:{exc}"
                await asyncio.sleep(0.1)
        pending.response_body_capture_error = last_error

    def _frame_url_for(self, frame_id: Optional[str], document_url: Optional[str]) -> Optional[str]:
        if frame_id and self.frame_urls.get(str(frame_id)):
            return self.frame_urls[str(frame_id)]
        if document_url:
            return document_url
        if frame_id and self.main_frame_id and str(frame_id) == self.main_frame_id:
            return self.cached_page_snapshot.get("href")
        return None

    async def _refresh_page_snapshot(self) -> None:
        try:
            result = await self.cdp_client.send_command(
                "Runtime.evaluate",
                {
                    "expression": "JSON.stringify({href: location.href, title: document.title, referrer: document.referrer})",
                    "returnByValue": True,
                },
            )
        except Exception:
            return
        value = result.get("result", {}).get("value")
        if not isinstance(value, str) or not value.strip():
            return
        try:
            payload = json.loads(value)
        except json.JSONDecodeError:
            return
        self.cached_page_snapshot["href"] = payload.get("href") or self.cached_page_snapshot.get("href")
        self.cached_page_snapshot["title"] = payload.get("title") or self.cached_page_snapshot.get("title")
        self.cached_page_snapshot["referrer"] = payload.get("referrer") or self.cached_page_snapshot.get("referrer")

    async def _snapshot_for_request(
        self,
        *,
        document_url: Optional[str],
        frame_id: Optional[str],
    ) -> Dict[str, Optional[str]]:
        if not self.cached_page_snapshot.get("href") and (document_url or frame_id):
            await self._refresh_page_snapshot()
        href = self.cached_page_snapshot.get("href") or self._frame_url_for(frame_id, document_url) or self.target_url or None
        return {
            "href": href,
            "title": self.cached_page_snapshot.get("title") or self.target_title or None,
            "referrer": self.cached_page_snapshot.get("referrer"),
        }

    @staticmethod
    def _extract_initiator_url(initiator: Dict[str, Any]) -> Optional[str]:
        if not initiator:
            return None
        if initiator.get("url"):
            return str(initiator.get("url"))
        stack = initiator.get("stack") or {}
        for frame in stack.get("callFrames", []) or []:
            url = frame.get("url")
            if url:
                return str(url)
        parent = stack.get("parent")
        while isinstance(parent, dict):
            for frame in parent.get("callFrames", []) or []:
                url = frame.get("url")
                if url:
                    return str(url)
            parent = parent.get("parent")
        return None

    async def _finalize_request(self, request_id: str) -> None:
        pending = self.pending.pop(request_id, None)
        if pending is None:
            return

        relative_path, path, host_base = make_relative_path(self.api_prefix, pending.url)
        if relative_path is None or path is None or host_base is None:
            return

        query_example = parse_query(pending.url)
        query_dynamic_fields: List[str] = []
        query_normalized = normalize_structure(query_example, "query", query_dynamic_fields)
        query_variant_key = canonical_json(query_normalized)

        content_type = pending.headers.get("Content-Type", pending.headers.get("content-type", ""))
        parsed_body, body_kind = parse_body(content_type, pending.post_data)
        body_example = redact_structure(parsed_body) if parsed_body is not None else None
        body_dynamic_fields: List[str] = []
        body_normalized = normalize_structure(parsed_body, "body", body_dynamic_fields) if parsed_body is not None else None
        body_variant_key = canonical_json(body_normalized) if parsed_body is not None else None
        headers_template = select_request_headers(pending.headers)

        metric = body_example.get("metric") if isinstance(body_example, dict) else None
        response_headers = {
            str(key): truncate_text(str(value), 2000) for key, value in pending.response_headers.items()
        }
        page_context = {
            "captured_page_url": pending.captured_page_url,
            "document_url": pending.document_url,
            "frame_url": pending.frame_url,
            "page_title": pending.page_title,
            "request_url": pending.url,
            "request_method": pending.method,
            "request_timestamp": now_iso(),
            "tab_target_id": pending.tab_target_id,
            "frame_id": pending.frame_id,
            "referrer": pending.referrer,
            "initiator_url": pending.initiator_url,
            "initiator_type": pending.initiator_type,
        }
        sample_request = {
            "seen_at": now_iso(),
            "url": pending.url,
            "resource_type": pending.resource_type,
            "query": query_example,
            "headers": headers_template,
            "body_kind": body_kind,
            "body": body_example,
            "page_context": page_context,
        }
        sample_response = None
        if pending.response_status is not None or pending.response_body is not None or pending.response_error is not None:
            sample_response = {
                "status": pending.response_status,
                "mime_type": pending.response_mime_type,
                "error": pending.response_error,
                "body_capture_error": pending.response_body_capture_error,
                "headers": response_headers,
                "body_kind": pending.response_body_kind,
                "body": pending.response_body,
            }

        observation = {
            "seen_at": now_iso(),
            "method": pending.method,
            "full_url": pending.url,
            "path": path,
            "relative_path": relative_path,
            "host_base": host_base,
            "resource_type": pending.resource_type,
            "request_headers_template": headers_template,
            "query_example": query_example,
            "query_normalized": query_normalized,
            "query_variant_key": query_variant_key,
            "query_dynamic_fields": sorted(set(query_dynamic_fields)),
            "query_metadata": {
                "keys": sorted(query_example.keys()),
                "signature": sorted(query_example.keys()),
            },
            "body_kind": body_kind,
            "body_example": body_example,
            "body_normalized": body_normalized,
            "body_variant_key": body_variant_key,
            "body_dynamic_fields": sorted(set(body_dynamic_fields)),
            "body_metadata": {
                "kind": body_kind,
                "top_level_keys": summarize_body_keys(body_example),
            }
            if body_example is not None
            else {},
            "metric": metric,
            "response_status": pending.response_status,
            "response_mime_type": pending.response_mime_type,
            "sample_request": sample_request,
            "sample_response": sample_response,
            "page_context": page_context,
        }

        output_path = self.catalog.observe(observation)
        raw_record = {
            "signature": self.raw_log_catalog.build_signature(observation),
            "relative_path": relative_path,
            "path": path,
            "method": pending.method,
            "metric": metric,
            "capture": {
                "captured_at": observation["seen_at"],
                "resource_type": pending.resource_type,
                "wall_time": pending.wall_time,
                "tab_target_id": pending.tab_target_id,
                "page_context": page_context,
            },
            "page_context": page_context,
            "request": {
                "url": pending.url,
                "host_base": host_base,
                "path": path,
                "query": query_example,
                "query_normalized": query_normalized,
                "headers": {str(key): truncate_text(str(value), 5000) for key, value in pending.headers.items()},
                "headers_template": headers_template,
                "content_type": content_type,
                "body_kind": body_kind,
                "raw_post_data": truncate_text(pending.post_data or "", 20000) if pending.post_data is not None else None,
                "body": parsed_body,
                "body_normalized": body_normalized,
                "page_context": page_context,
            },
            "response": {
                "status": pending.response_status,
                "mime_type": pending.response_mime_type,
                "headers": response_headers,
                "encoded_data_length": pending.encoded_data_length,
                "body_kind": pending.response_body_kind,
                "body": pending.response_body_raw,
                "body_redacted": pending.response_body,
                "body_capture_error": pending.response_body_capture_error,
                "error": pending.response_error,
            },
        }
        raw_log_path, raw_log_replaced = self.raw_log_catalog.observe(raw_record)
        self.catalog.write_index()
        if self.verbose:
            status = pending.response_status if pending.response_status is not None else "n/a"
            raw_state = "updated" if raw_log_replaced else "kept"
            print(
                f"[captured] {pending.method} {relative_path} status={status} -> {output_path} | raw={raw_state}:{raw_log_path}",
                flush=True,
            )


def fetch_json(url: str) -> Any:
    with urlopen(url) as response:
        payload = response.read().decode("utf-8")
    return json.loads(payload)


def list_targets(browser_url: str) -> List[Dict[str, Any]]:
    endpoint = browser_url.rstrip("/") + "/json/list"
    return fetch_json(endpoint)


def print_targets(targets: List[Dict[str, Any]]) -> None:
    for target in targets:
        title = target.get("title", "")
        url = target.get("url", "")
        target_type = target.get("type", "")
        target_id = target.get("id", "")
        print(f"{target_id}\t{target_type}\t{title}\t{url}")


def select_targets(
    targets: List[Dict[str, Any]],
    target_id: Optional[str],
    target_url_contains: Optional[str],
    api_prefix: str,
) -> List[Dict[str, Any]]:
    pages = [target for target in targets if target.get("type") == "page"]
    if not pages:
        raise RuntimeError("No page targets found. Open the browser page first.")

    if target_id:
        for target in pages:
            if target.get("id") == target_id:
                return [target]
        raise RuntimeError(f"Target id not found: {target_id}")

    if target_url_contains:
        matches = [target for target in pages if target_url_contains in target.get("url", "")]
        if matches:
            return matches
        raise RuntimeError(f"No page target matched --target-url-contains={target_url_contains}")

    api_netloc = urlsplit(api_prefix).netloc
    if api_netloc:
        matches = [target for target in pages if api_netloc in target.get("url", "")]
        if matches:
            return matches

    return pages


def install_signal_handlers(stop_event: asyncio.Event) -> None:
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop_event.set)
        except NotImplementedError:
            pass


def parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--browser-url",
        default="http://127.0.0.1:9222",
        help="Chrome remote debugging URL, default: %(default)s",
    )
    parser.add_argument(
        "--api-prefix",
        default="http://169.169.173.25:8080/server-api/",
        help="Only capture requests whose URL starts with this prefix",
    )
    parser.add_argument(
        "--output-dir",
        default="./captured_api",
        help="Directory used to write endpoint JSON files",
    )
    parser.add_argument(
        "--raw-log-dir",
        default=DEFAULT_RAW_LOG_DIR,
        help="Directory used to write one best raw request/response JSON per request signature",
    )
    parser.add_argument(
        "--target-id",
        help="Exact target id from /json/list",
    )
    parser.add_argument(
        "--target-url-contains",
        help="Attach to every page target whose URL contains this text",
    )
    parser.add_argument(
        "--discover-targets-interval",
        type=float,
        default=2.0,
        help="How often to poll Chrome for new matching page targets; set 0 to disable polling",
    )
    parser.add_argument(
        "--list-targets",
        action="store_true",
        help="Print available page targets and exit",
    )
    parser.add_argument(
        "--include-response-body",
        action="store_true",
        help="Try to capture small JSON/text responses as samples",
    )
    parser.add_argument(
        "--max-response-bytes",
        type=int,
        default=DEFAULT_RESPONSE_BYTES,
        help="Only attempt to capture response bodies smaller than this many bytes",
    )
    parser.add_argument(
        "--network-total-buffer-bytes",
        type=int,
        default=DEFAULT_NETWORK_TOTAL_BUFFER_BYTES,
        help="Total CDP network inspector buffer size in bytes; raise this if bodies are evicted from cache",
    )
    parser.add_argument(
        "--network-resource-buffer-bytes",
        type=int,
        default=DEFAULT_NETWORK_RESOURCE_BUFFER_BYTES,
        help="Per-resource CDP network inspector buffer size in bytes",
    )
    parser.add_argument(
        "--max-examples-per-method",
        type=int,
        default=DEFAULT_EXAMPLE_COUNT,
        help="How many unique request/response examples to keep per method",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print a line each time a matching endpoint is captured",
    )
    return parser.parse_args(argv)


async def async_main(args: argparse.Namespace) -> int:
    os.makedirs(args.output_dir, exist_ok=True)
    os.makedirs(args.raw_log_dir, exist_ok=True)
    targets = list_targets(args.browser_url)
    if args.list_targets:
        print_targets(targets)
        return 0

    selected_targets = select_targets(targets, args.target_id, args.target_url_contains, args.api_prefix)
    selected_targets = [target for target in selected_targets if target.get("webSocketDebuggerUrl")]
    if not selected_targets:
        raise RuntimeError("No selected targets expose webSocketDebuggerUrl")

    catalog = EndpointCatalog(args.output_dir, args.max_examples_per_method)
    catalog.load_existing()
    catalog.write_index()
    raw_log_catalog = RawLogCatalog(args.raw_log_dir)
    stop_event = asyncio.Event()
    install_signal_handlers(stop_event)

    print(f"Initial matching targets: {len(selected_targets)}")
    for target in selected_targets:
        print(f"- {target.get('title', '')} [{target.get('id', '')}]")
        print(f"  URL: {target.get('url', '')}")
    print(f"API prefix: {args.api_prefix}")
    print(f"Output dir: {os.path.abspath(args.output_dir)}")
    print(f"Raw log dir: {os.path.abspath(args.raw_log_dir)}")
    print(f"Network total buffer: {args.network_total_buffer_bytes}")
    print(f"Network resource buffer: {args.network_resource_buffer_bytes}")
    print(f"Discover targets interval: {args.discover_targets_interval}")
    print("Press Ctrl+C to stop.", flush=True)

    clients: Dict[str, CDPClient] = {}
    tasks: Dict[str, asyncio.Task] = {}

    async def attach_target(target: Dict[str, Any]) -> None:
        target_id = target.get("id", "")
        if not target_id or target_id in tasks:
            return
        websocket_url = target.get("webSocketDebuggerUrl")
        if not websocket_url:
            return
        client = CDPClient(websocket_url)
        await client.connect()
        clients[target_id] = client
        session = CaptureSession(
            cdp_client=client,
            catalog=catalog,
            raw_log_catalog=raw_log_catalog,
            api_prefix=args.api_prefix,
            target_id=target_id,
            target_title=str(target.get("title", "")),
            target_url=str(target.get("url", "")),
            include_response_body=args.include_response_body,
            max_response_bytes=args.max_response_bytes,
            network_total_buffer_bytes=args.network_total_buffer_bytes,
            network_resource_buffer_bytes=args.network_resource_buffer_bytes,
            stop_requested=stop_event,
            verbose=args.verbose,
        )
        tasks[target_id] = asyncio.create_task(session.run_forever())
        print(f"[attach] {target.get('title', '')} [{target_id}] {target.get('url', '')}", flush=True)

    async def refresh_targets() -> None:
        current_targets = list_targets(args.browser_url)
        matched_targets = select_targets(current_targets, args.target_id, args.target_url_contains, args.api_prefix)
        for target in matched_targets:
            await attach_target(target)

    try:
        for target in selected_targets:
            await attach_target(target)
        while not stop_event.is_set():
            failed = []
            for target_id, task in list(tasks.items()):
                if task.done():
                    exc = task.exception()
                    if exc is not None:
                        failed.append((target_id, exc))
                    tasks.pop(target_id, None)
                    client = clients.pop(target_id, None)
                    if client is not None:
                        await client.close()
            if failed:
                target_id, exc = failed[0]
                raise RuntimeError(f"Target {target_id} capture failed: {exc}") from exc
            if args.discover_targets_interval > 0:
                await refresh_targets()
                await asyncio.sleep(args.discover_targets_interval)
            else:
                if tasks:
                    await asyncio.gather(*tasks.values())
                    break
                await asyncio.sleep(0.5)
    finally:
        stop_event.set()
        for task in tasks.values():
            if not task.done():
                task.cancel()
        if tasks:
            await asyncio.gather(*tasks.values(), return_exceptions=True)
        for client in clients.values():
            await client.close()
        catalog.write_index()
    return 0


def main(argv: List[str]) -> int:
    args = parse_args(argv)
    try:
        return asyncio.run(async_main(args))
    except KeyboardInterrupt:
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
