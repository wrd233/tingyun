from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import datetime
from typing import Any, Optional

from tingyun_adapter.config.constants import DEFAULT_LANG, DEFAULT_SCHEMA_VERSION, DEFAULT_TIMEZONE


def dataclass_to_dict(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, list):
        return [dataclass_to_dict(item) for item in value]
    if isinstance(value, dict):
        return {key: dataclass_to_dict(item) for key, item in value.items()}
    return value


@dataclass(frozen=True)
class TimeWindow:
    end_time: str
    period_minutes: int


@dataclass(frozen=True)
class AuthConfig:
    token: Optional[str] = None
    token_env: str = "TINGYUN_TOKEN"


@dataclass(frozen=True)
class AnalysisContext:
    base_url: str
    biz_system_id: int
    time_window: TimeWindow
    auth: AuthConfig = field(default_factory=AuthConfig)
    lang: str = DEFAULT_LANG
    timezone: str = DEFAULT_TIMEZONE


@dataclass(frozen=True)
class ActionRef:
    biz_system_id: int
    application_id: int
    action_id: int
    action_type: str


@dataclass(frozen=True)
class TraceRef:
    biz_system_id: int
    trace_id_numeric: Optional[str] = None
    query_timestamp: Optional[str] = None
    action_guid: Optional[str] = None
    trace_guid: Optional[str] = None
    request_id: Optional[str] = None


@dataclass(frozen=True)
class DatabaseComponentRef:
    biz_system_id: int
    component_name: str
    component_subtype: Optional[str] = None
    component_type: str = "Database"


@dataclass(frozen=True)
class NoSQLComponentRef:
    biz_system_id: int
    component_name: str
    component_subtype: Optional[str] = None
    component_type: str = "NoSQL"


@dataclass(frozen=True)
class ConnectionPoolRef:
    biz_system_id: int
    metric_category: Optional[str] = None
    application_id: Optional[int] = None
    instance_id: Optional[int] = None


@dataclass(frozen=True)
class HotspotPolicy:
    sort_by: str = "response_time_ms"
    secondary_sort_by: str = "slow_count"
    limit: int = 10
    include_zero_error: bool = True


@dataclass(frozen=True)
class TraceSelectionPolicy:
    strategy: str = "slowest"
    limit: int = 15


@dataclass(frozen=True)
class EvidencePolicy:
    include_raw_request: bool = True
    include_raw_response_excerpt: bool = True
    max_evidence_per_fact: int = 5


@dataclass
class WarningMessage:
    code: str
    message: str
    source_api: Optional[str] = None


@dataclass
class Evidence:
    id: str
    source_api: str
    source_path: str
    source_method: str
    request_signature: dict[str, Any]
    request_params: dict[str, Any]
    response_excerpt: Any
    extracted_fields: dict[str, Any] = field(default_factory=dict)
    captured_at: Optional[str] = None
    confidence: float = 1.0


@dataclass
class PackMeta:
    adapter_version: str = "0.1.0"
    source_count: int = 0
    evidence_count: int = 0
    warnings: list[WarningMessage] = field(default_factory=list)


@dataclass
class PackEnvelope:
    pack_type: str
    context: AnalysisContext
    payload: dict[str, Any]
    schema_version: str = DEFAULT_SCHEMA_VERSION
    generated_at: str = field(default_factory=lambda: datetime.now().astimezone().isoformat(timespec="seconds"))
    meta: PackMeta = field(default_factory=PackMeta)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "pack_type": self.pack_type,
            "generated_at": self.generated_at,
            "context": dataclass_to_dict(self.context),
            "payload": dataclass_to_dict(self.payload),
            "meta": dataclass_to_dict(self.meta),
        }
