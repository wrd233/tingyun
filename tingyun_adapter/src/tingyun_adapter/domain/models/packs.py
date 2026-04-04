from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SystemSnapshotPayload:
    biz_system: dict[str, Any]
    overview: dict[str, Any] = field(default_factory=dict)
    health: dict[str, Any] = field(default_factory=dict)
    trends: dict[str, Any] = field(default_factory=dict)
    suspect_signals: list[dict[str, Any]] = field(default_factory=list)
    evidence: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class ActionHotspotPackPayload:
    ranking_policy: dict[str, Any]
    hotspots: list[dict[str, Any]] = field(default_factory=list)
    suspect_signals: list[dict[str, Any]] = field(default_factory=list)
    evidence: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class TraceCasePackPayload:
    selector: dict[str, Any]
    trace_case: dict[str, Any]
    suspect_signals: list[dict[str, Any]] = field(default_factory=list)
    drilldown_path: list[str] = field(default_factory=list)
    evidence: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class DiagnosticCandidatePackPayload:
    candidate_policy: dict[str, Any]
    system_signals: list[dict[str, Any]] = field(default_factory=list)
    action_candidates: list[dict[str, Any]] = field(default_factory=list)
    trace_candidates: list[dict[str, Any]] = field(default_factory=list)
    component_candidates: list[dict[str, Any]] = field(default_factory=list)
    recommended_next_packs: list[dict[str, Any]] = field(default_factory=list)
    evidence: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class ActionFactSheetPayload:
    action_ref: dict[str, Any]
    action: dict[str, Any] = field(default_factory=dict)
    overview: dict[str, Any] = field(default_factory=dict)
    suspect_signals: list[dict[str, Any]] = field(default_factory=list)
    trace_candidates: list[dict[str, Any]] = field(default_factory=list)
    downstream_components: dict[str, Any] = field(default_factory=dict)
    drilldown_keys: dict[str, Any] = field(default_factory=dict)
    drilldown_path: list[str] = field(default_factory=list)
    evidence: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class TraceFactSheetPayload:
    selector: dict[str, Any]
    trace: dict[str, Any] = field(default_factory=dict)
    detail_summary: dict[str, Any] = field(default_factory=dict)
    call_tree_summary: dict[str, Any] = field(default_factory=dict)
    exception_summary: dict[str, Any] = field(default_factory=dict)
    suspect_signals: list[dict[str, Any]] = field(default_factory=list)
    drilldown_keys: dict[str, Any] = field(default_factory=dict)
    drilldown_path: list[str] = field(default_factory=list)
    evidence: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class DatabaseComponentPackPayload:
    component: dict[str, Any]
    summary: dict[str, Any] = field(default_factory=dict)
    top_operations: list[dict[str, Any]] = field(default_factory=list)
    top_impacted_actions: list[dict[str, Any]] = field(default_factory=list)
    top_related_traces: list[dict[str, Any]] = field(default_factory=list)
    topology_summary: dict[str, Any] = field(default_factory=dict)
    connection_pool_summary: dict[str, Any] = field(default_factory=dict)
    suspect_signals: list[dict[str, Any]] = field(default_factory=list)
    evidence: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class NoSQLComponentPackPayload:
    component: dict[str, Any]
    summary: dict[str, Any] = field(default_factory=dict)
    top_operations: list[dict[str, Any]] = field(default_factory=list)
    top_related_traces: list[dict[str, Any]] = field(default_factory=list)
    error_summary: dict[str, Any] = field(default_factory=dict)
    topology_summary: dict[str, Any] = field(default_factory=dict)
    suspect_signals: list[dict[str, Any]] = field(default_factory=list)
    evidence: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class ConnectionPoolPackPayload:
    pool: dict[str, Any]
    summary: dict[str, Any] = field(default_factory=dict)
    time_series: dict[str, Any] = field(default_factory=dict)
    waiter_risk: dict[str, Any] = field(default_factory=dict)
    suspect_signals: list[dict[str, Any]] = field(default_factory=list)
    evidence: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class ReportFactPackPayload:
    report_scope: dict[str, Any]
    summary: dict[str, Any] = field(default_factory=dict)
    hotspots: dict[str, Any] = field(default_factory=dict)
    components: dict[str, Any] = field(default_factory=dict)
    trace_case: dict[str, Any] = field(default_factory=dict)
    issues: list[dict[str, Any]] = field(default_factory=list)
    drilldown_paths: list[str] = field(default_factory=list)
    evidence: list[dict[str, Any]] = field(default_factory=list)
