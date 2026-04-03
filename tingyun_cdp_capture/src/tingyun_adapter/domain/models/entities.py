from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from .common import Evidence


@dataclass
class BizSystem:
    id: int
    name: Optional[str] = None
    overview: dict[str, Any] = field(default_factory=dict)
    health: dict[str, Any] = field(default_factory=dict)
    applications: list[int] = field(default_factory=list)
    instances: list[int] = field(default_factory=list)
    actions: list[int] = field(default_factory=list)
    components: list[str] = field(default_factory=list)
    evidence: list[Evidence] = field(default_factory=list)


@dataclass
class Application:
    id: int
    biz_system_id: int
    name: Optional[str] = None
    display_name: Optional[str] = None
    technology: Optional[str] = None
    language: Optional[str] = None
    instance_ids: list[int] = field(default_factory=list)
    overview: dict[str, Any] = field(default_factory=dict)
    trends: dict[str, Any] = field(default_factory=dict)
    evidence: list[Evidence] = field(default_factory=list)


@dataclass
class Instance:
    id: int
    application_id: int
    name: Optional[str] = None
    host_ip: Optional[str] = None
    host_name: Optional[str] = None
    agent_version: Optional[str] = None
    one_agent_version: Optional[str] = None
    os: Optional[str] = None
    evidence: list[Evidence] = field(default_factory=list)


@dataclass
class Action:
    id: int
    biz_system_id: int
    application_id: int
    type: str
    name: Optional[str] = None
    alias: Optional[str] = None
    metrics: dict[str, Any] = field(default_factory=dict)
    component_summary: dict[str, Any] = field(default_factory=dict)
    trace_summary: dict[str, Any] = field(default_factory=dict)
    evidence: list[Evidence] = field(default_factory=list)


@dataclass
class ActionHotspot:
    action_id: int
    application_id: int
    biz_system_id: int
    ranking_basis: list[str] = field(default_factory=list)
    severity_score: Optional[float] = None
    why_selected: list[str] = field(default_factory=list)
    evidence: list[Evidence] = field(default_factory=list)


@dataclass
class Trace:
    biz_system_id: int
    trace_id_numeric: Optional[str] = None
    trace_guid: Optional[str] = None
    action_guid: Optional[str] = None
    request_id: Optional[str] = None
    timestamp: Optional[int] = None
    application_id: Optional[int] = None
    instance_id: Optional[int] = None
    action_id: Optional[int] = None
    status: Optional[str] = None
    duration_ms: Optional[float] = None
    error_count: Optional[int] = None
    is_slow_trace: Optional[bool] = None
    suspected_problems: list[dict[str, Any]] = field(default_factory=list)
    topology_summary: dict[str, Any] = field(default_factory=dict)
    service_flow_summary: dict[str, Any] = field(default_factory=dict)
    timeline_summary: dict[str, Any] = field(default_factory=dict)
    exceptions: list[dict[str, Any]] = field(default_factory=list)
    logs: list[dict[str, Any]] = field(default_factory=list)
    evidence: list[Evidence] = field(default_factory=list)


@dataclass
class DatabaseComponent:
    biz_system_id: int
    component_name: str
    component_subtype: Optional[str] = None
    metrics: dict[str, Any] = field(default_factory=dict)
    top_actions: list[dict[str, Any]] = field(default_factory=list)
    top_operations: list[dict[str, Any]] = field(default_factory=list)
    top_traces: list[dict[str, Any]] = field(default_factory=list)
    topology: dict[str, Any] = field(default_factory=dict)
    connection_pool: dict[str, Any] = field(default_factory=dict)
    evidence: list[Evidence] = field(default_factory=list)


@dataclass
class DatabaseOperation:
    biz_system_id: int
    component_name: str
    op_name_raw: str
    op_name_decoded: str
    decoded: bool
    metrics: dict[str, Any] = field(default_factory=dict)
    top_actions: list[dict[str, Any]] = field(default_factory=list)
    top_traces: list[dict[str, Any]] = field(default_factory=list)
    evidence: list[Evidence] = field(default_factory=list)


@dataclass
class NoSQLComponent:
    biz_system_id: int
    component_name: str
    component_subtype: Optional[str] = None
    metrics: dict[str, Any] = field(default_factory=dict)
    top_operations: list[dict[str, Any]] = field(default_factory=list)
    top_traces: list[dict[str, Any]] = field(default_factory=list)
    topology: dict[str, Any] = field(default_factory=dict)
    evidence: list[Evidence] = field(default_factory=list)


@dataclass
class ConnectionPool:
    biz_system_id: int
    metric_category: Optional[str] = None
    database_type: Optional[str] = None
    framework: Optional[str] = None
    current_used: Optional[int] = None
    current_idle: Optional[int] = None
    max_active: Optional[int] = None
    min_idle: Optional[int] = None
    waiter_connections: Optional[int] = None
    connection_time_series: dict[str, Any] = field(default_factory=dict)
    pools: list[dict[str, Any]] = field(default_factory=list)
    evidence: list[Evidence] = field(default_factory=list)


@dataclass
class Relation:
    subject_type: str
    subject_id: str
    relation_type: str
    object_type: str
    object_id: str
    attributes: dict[str, Any] = field(default_factory=dict)
