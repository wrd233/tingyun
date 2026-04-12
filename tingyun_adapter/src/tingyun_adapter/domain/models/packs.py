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
    metric_semantics: list[dict[str, Any]] = field(default_factory=list)
    page_links: list[dict[str, Any]] = field(default_factory=list)
    primary_console_url: str | None = None
    related_console_urls: list[str] = field(default_factory=list)
    screenshot_hints: list[dict[str, Any]] = field(default_factory=list)
    coverage_boundary: dict[str, Any] = field(default_factory=dict)
    evidence_linkage: dict[str, Any] = field(default_factory=dict)
    evidence: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class ActionHotspotPackPayload:
    ranking_policy: dict[str, Any]
    hotspots: list[dict[str, Any]] = field(default_factory=list)
    suspect_signals: list[dict[str, Any]] = field(default_factory=list)
    metric_semantics: list[dict[str, Any]] = field(default_factory=list)
    page_links: list[dict[str, Any]] = field(default_factory=list)
    primary_console_url: str | None = None
    related_console_urls: list[str] = field(default_factory=list)
    screenshot_hints: list[dict[str, Any]] = field(default_factory=list)
    coverage_boundary: dict[str, Any] = field(default_factory=dict)
    evidence_linkage: dict[str, Any] = field(default_factory=dict)
    evidence: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class TraceCasePackPayload:
    selector: dict[str, Any]
    trace_case: dict[str, Any]
    suspect_signals: list[dict[str, Any]] = field(default_factory=list)
    drilldown_path: list[str] = field(default_factory=list)
    metric_semantics: list[dict[str, Any]] = field(default_factory=list)
    page_links: list[dict[str, Any]] = field(default_factory=list)
    primary_console_url: str | None = None
    related_console_urls: list[str] = field(default_factory=list)
    screenshot_hints: list[dict[str, Any]] = field(default_factory=list)
    coverage_boundary: dict[str, Any] = field(default_factory=dict)
    evidence_linkage: dict[str, Any] = field(default_factory=dict)
    evidence: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class DiagnosticCandidatePackPayload:
    candidate_policy: dict[str, Any]
    system_signals: list[dict[str, Any]] = field(default_factory=list)
    action_candidates: list[dict[str, Any]] = field(default_factory=list)
    trace_candidates: list[dict[str, Any]] = field(default_factory=list)
    component_candidates: list[dict[str, Any]] = field(default_factory=list)
    recommended_next_packs: list[dict[str, Any]] = field(default_factory=list)
    metric_semantics: list[dict[str, Any]] = field(default_factory=list)
    page_links: list[dict[str, Any]] = field(default_factory=list)
    primary_console_url: str | None = None
    related_console_urls: list[str] = field(default_factory=list)
    screenshot_hints: list[dict[str, Any]] = field(default_factory=list)
    coverage_boundary: dict[str, Any] = field(default_factory=dict)
    evidence_linkage: dict[str, Any] = field(default_factory=dict)
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
    metric_semantics: list[dict[str, Any]] = field(default_factory=list)
    page_links: list[dict[str, Any]] = field(default_factory=list)
    primary_console_url: str | None = None
    related_console_urls: list[str] = field(default_factory=list)
    screenshot_hints: list[dict[str, Any]] = field(default_factory=list)
    coverage_boundary: dict[str, Any] = field(default_factory=dict)
    evidence_linkage: dict[str, Any] = field(default_factory=dict)
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
    metric_semantics: list[dict[str, Any]] = field(default_factory=list)
    page_links: list[dict[str, Any]] = field(default_factory=list)
    primary_console_url: str | None = None
    related_console_urls: list[str] = field(default_factory=list)
    screenshot_hints: list[dict[str, Any]] = field(default_factory=list)
    coverage_boundary: dict[str, Any] = field(default_factory=dict)
    evidence_linkage: dict[str, Any] = field(default_factory=dict)
    evidence: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class TraceSQLPackPayload:
    selector: dict[str, Any]
    trace: dict[str, Any] = field(default_factory=dict)
    detail_summary: dict[str, Any] = field(default_factory=dict)
    sql_summary: dict[str, Any] = field(default_factory=dict)
    sqls: list[dict[str, Any]] = field(default_factory=list)
    database_spans: list[dict[str, Any]] = field(default_factory=list)
    suspect_signals: list[dict[str, Any]] = field(default_factory=list)
    drilldown_keys: dict[str, Any] = field(default_factory=dict)
    drilldown_path: list[str] = field(default_factory=list)
    metric_semantics: list[dict[str, Any]] = field(default_factory=list)
    page_links: list[dict[str, Any]] = field(default_factory=list)
    primary_console_url: str | None = None
    related_console_urls: list[str] = field(default_factory=list)
    screenshot_hints: list[dict[str, Any]] = field(default_factory=list)
    coverage_boundary: dict[str, Any] = field(default_factory=dict)
    evidence_linkage: dict[str, Any] = field(default_factory=dict)
    evidence: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class TraceExecutionPackPayload:
    selector: dict[str, Any]
    trace: dict[str, Any] = field(default_factory=dict)
    detail_summary: dict[str, Any] = field(default_factory=dict)
    call_tree_summary: dict[str, Any] = field(default_factory=dict)
    call_tree_hotspots: dict[str, Any] = field(default_factory=dict)
    snapshot_summary: dict[str, Any] = field(default_factory=dict)
    exception_summary: dict[str, Any] = field(default_factory=dict)
    exceptions: list[dict[str, Any]] = field(default_factory=list)
    pool_summary: dict[str, Any] = field(default_factory=dict)
    pool_infos: list[dict[str, Any]] = field(default_factory=list)
    database_spans: list[dict[str, Any]] = field(default_factory=list)
    suspect_signals: list[dict[str, Any]] = field(default_factory=list)
    drilldown_keys: dict[str, Any] = field(default_factory=dict)
    drilldown_path: list[str] = field(default_factory=list)
    metric_semantics: list[dict[str, Any]] = field(default_factory=list)
    page_links: list[dict[str, Any]] = field(default_factory=list)
    primary_console_url: str | None = None
    related_console_urls: list[str] = field(default_factory=list)
    screenshot_hints: list[dict[str, Any]] = field(default_factory=list)
    coverage_boundary: dict[str, Any] = field(default_factory=dict)
    evidence_linkage: dict[str, Any] = field(default_factory=dict)
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
    metric_semantics: list[dict[str, Any]] = field(default_factory=list)
    page_links: list[dict[str, Any]] = field(default_factory=list)
    primary_console_url: str | None = None
    related_console_urls: list[str] = field(default_factory=list)
    screenshot_hints: list[dict[str, Any]] = field(default_factory=list)
    coverage_boundary: dict[str, Any] = field(default_factory=dict)
    evidence_linkage: dict[str, Any] = field(default_factory=dict)
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
    metric_semantics: list[dict[str, Any]] = field(default_factory=list)
    page_links: list[dict[str, Any]] = field(default_factory=list)
    primary_console_url: str | None = None
    related_console_urls: list[str] = field(default_factory=list)
    screenshot_hints: list[dict[str, Any]] = field(default_factory=list)
    coverage_boundary: dict[str, Any] = field(default_factory=dict)
    evidence_linkage: dict[str, Any] = field(default_factory=dict)
    evidence: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class ConnectionPoolPackPayload:
    pool: dict[str, Any]
    summary: dict[str, Any] = field(default_factory=dict)
    time_series: dict[str, Any] = field(default_factory=dict)
    waiter_risk: dict[str, Any] = field(default_factory=dict)
    suspect_signals: list[dict[str, Any]] = field(default_factory=list)
    metric_semantics: list[dict[str, Any]] = field(default_factory=list)
    page_links: list[dict[str, Any]] = field(default_factory=list)
    primary_console_url: str | None = None
    related_console_urls: list[str] = field(default_factory=list)
    screenshot_hints: list[dict[str, Any]] = field(default_factory=list)
    coverage_boundary: dict[str, Any] = field(default_factory=dict)
    evidence_linkage: dict[str, Any] = field(default_factory=dict)
    evidence: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class InstanceAnalysisPackPayload:
    application: dict[str, Any]
    instances: list[dict[str, Any]] = field(default_factory=list)
    selected_instance: dict[str, Any] = field(default_factory=dict)
    summary: dict[str, Any] = field(default_factory=dict)
    cpu_chart: dict[str, Any] = field(default_factory=dict)
    jvm_chart: dict[str, Any] = field(default_factory=dict)
    suspect_signals: list[dict[str, Any]] = field(default_factory=list)
    metric_semantics: list[dict[str, Any]] = field(default_factory=list)
    page_links: list[dict[str, Any]] = field(default_factory=list)
    primary_console_url: str | None = None
    related_console_urls: list[str] = field(default_factory=list)
    screenshot_hints: list[dict[str, Any]] = field(default_factory=list)
    coverage_boundary: dict[str, Any] = field(default_factory=dict)
    evidence_linkage: dict[str, Any] = field(default_factory=dict)
    evidence: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class DeploymentInventoryPackPayload:
    biz_system: dict[str, Any]
    summary: dict[str, Any] = field(default_factory=dict)
    service_inventory: list[dict[str, Any]] = field(default_factory=list)
    service_host_rows: list[dict[str, Any]] = field(default_factory=list)
    host_inventory: list[dict[str, Any]] = field(default_factory=list)
    component_inventory: list[dict[str, Any]] = field(default_factory=list)
    component_usage_rows: list[dict[str, Any]] = field(default_factory=list)
    diagnostics: dict[str, Any] = field(default_factory=dict)
    suspect_signals: list[dict[str, Any]] = field(default_factory=list)
    metric_semantics: list[dict[str, Any]] = field(default_factory=list)
    page_links: list[dict[str, Any]] = field(default_factory=list)
    primary_console_url: str | None = None
    related_console_urls: list[str] = field(default_factory=list)
    screenshot_hints: list[dict[str, Any]] = field(default_factory=list)
    coverage_boundary: dict[str, Any] = field(default_factory=dict)
    evidence_linkage: dict[str, Any] = field(default_factory=dict)
    evidence: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class TopologyDependencyPackPayload:
    biz_system: dict[str, Any]
    business_graph: dict[str, Any] = field(default_factory=dict)
    detail_graph: dict[str, Any] = field(default_factory=dict)
    node_health: dict[str, Any] = field(default_factory=dict)
    dependencies: list[dict[str, Any]] = field(default_factory=list)
    suspect_signals: list[dict[str, Any]] = field(default_factory=list)
    metric_semantics: list[dict[str, Any]] = field(default_factory=list)
    page_links: list[dict[str, Any]] = field(default_factory=list)
    primary_console_url: str | None = None
    related_console_urls: list[str] = field(default_factory=list)
    screenshot_hints: list[dict[str, Any]] = field(default_factory=list)
    coverage_boundary: dict[str, Any] = field(default_factory=dict)
    evidence_linkage: dict[str, Any] = field(default_factory=dict)
    evidence: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class ExternalDependencyPackPayload:
    biz_system: dict[str, Any]
    topology_summary: dict[str, Any] = field(default_factory=dict)
    protocol_summary: dict[str, Any] = field(default_factory=dict)
    external_dependencies: list[dict[str, Any]] = field(default_factory=list)
    suspect_signals: list[dict[str, Any]] = field(default_factory=list)
    metric_semantics: list[dict[str, Any]] = field(default_factory=list)
    page_links: list[dict[str, Any]] = field(default_factory=list)
    primary_console_url: str | None = None
    related_console_urls: list[str] = field(default_factory=list)
    screenshot_hints: list[dict[str, Any]] = field(default_factory=list)
    coverage_boundary: dict[str, Any] = field(default_factory=dict)
    evidence_linkage: dict[str, Any] = field(default_factory=dict)
    evidence: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class SlowSQLPackPayload:
    scope: dict[str, Any]
    selected_components: list[dict[str, Any]] = field(default_factory=list)
    top_sqls: list[dict[str, Any]] = field(default_factory=list)
    operation_overview: dict[str, Any] = field(default_factory=dict)
    diagnostics: dict[str, Any] = field(default_factory=dict)
    suspect_signals: list[dict[str, Any]] = field(default_factory=list)
    metric_semantics: list[dict[str, Any]] = field(default_factory=list)
    page_links: list[dict[str, Any]] = field(default_factory=list)
    primary_console_url: str | None = None
    related_console_urls: list[str] = field(default_factory=list)
    screenshot_hints: list[dict[str, Any]] = field(default_factory=list)
    coverage_boundary: dict[str, Any] = field(default_factory=dict)
    evidence_linkage: dict[str, Any] = field(default_factory=dict)
    evidence: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class SQLFactSheetPayload:
    selector: dict[str, Any]
    component: dict[str, Any] = field(default_factory=dict)
    sql: dict[str, Any] = field(default_factory=dict)
    sql_features: dict[str, Any] = field(default_factory=dict)
    related_actions: list[dict[str, Any]] = field(default_factory=list)
    related_traces: list[dict[str, Any]] = field(default_factory=list)
    drilldown_keys: dict[str, Any] = field(default_factory=dict)
    diagnostics: dict[str, Any] = field(default_factory=dict)
    suspect_signals: list[dict[str, Any]] = field(default_factory=list)
    metric_semantics: list[dict[str, Any]] = field(default_factory=list)
    page_links: list[dict[str, Any]] = field(default_factory=list)
    primary_console_url: str | None = None
    related_console_urls: list[str] = field(default_factory=list)
    screenshot_hints: list[dict[str, Any]] = field(default_factory=list)
    coverage_boundary: dict[str, Any] = field(default_factory=dict)
    evidence_linkage: dict[str, Any] = field(default_factory=dict)
    evidence: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class ActionDependencyBreakdownPackPayload:
    action_ref: dict[str, Any]
    action: dict[str, Any] = field(default_factory=dict)
    breakdown_summary: dict[str, Any] = field(default_factory=dict)
    component_breakdown: list[dict[str, Any]] = field(default_factory=list)
    action_graph: dict[str, Any] = field(default_factory=dict)
    topology_summary: dict[str, Any] = field(default_factory=dict)
    suspect_signals: list[dict[str, Any]] = field(default_factory=list)
    metric_semantics: list[dict[str, Any]] = field(default_factory=list)
    page_links: list[dict[str, Any]] = field(default_factory=list)
    primary_console_url: str | None = None
    related_console_urls: list[str] = field(default_factory=list)
    screenshot_hints: list[dict[str, Any]] = field(default_factory=list)
    coverage_boundary: dict[str, Any] = field(default_factory=dict)
    evidence_linkage: dict[str, Any] = field(default_factory=dict)
    evidence: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class ReportFactPackPayload:
    report_scope: dict[str, Any]
    summary: dict[str, Any] = field(default_factory=dict)
    hotspots: dict[str, Any] = field(default_factory=dict)
    components: dict[str, Any] = field(default_factory=dict)
    trace_case: dict[str, Any] = field(default_factory=dict)
    diagnostics: dict[str, Any] = field(default_factory=dict)
    issues: list[dict[str, Any]] = field(default_factory=list)
    observations: list[dict[str, Any]] = field(default_factory=list)
    issue_candidates: list[dict[str, Any]] = field(default_factory=list)
    sql_main_candidates: list[dict[str, Any]] = field(default_factory=list)
    sql_opportunities: list[dict[str, Any]] = field(default_factory=list)
    sql_candidates: list[dict[str, Any]] = field(default_factory=list)
    candidate_registry: list[dict[str, Any]] = field(default_factory=list)
    codex_review_input: dict[str, Any] = field(default_factory=dict)
    main_issue_selections: list[dict[str, Any]] = field(default_factory=list)
    deep_dive_targets: list[dict[str, Any]] = field(default_factory=list)
    selected_target_expansions: list[dict[str, Any]] = field(default_factory=list)
    report_writer_input: dict[str, Any] = field(default_factory=dict)
    template_mapping: dict[str, Any] = field(default_factory=dict)
    report_pack_exports: dict[str, Any] = field(default_factory=dict)
    drilldown_paths: list[str] = field(default_factory=list)
    metric_semantics: list[dict[str, Any]] = field(default_factory=list)
    page_links: list[dict[str, Any]] = field(default_factory=list)
    primary_console_url: str | None = None
    related_console_urls: list[str] = field(default_factory=list)
    screenshot_hints: list[dict[str, Any]] = field(default_factory=list)
    coverage_boundary: dict[str, Any] = field(default_factory=dict)
    evidence_linkage: dict[str, Any] = field(default_factory=dict)
    evidence: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class BusinessLabelsPackPayload:
    scope: dict[str, Any]
    objects: list[dict[str, Any]] = field(default_factory=list)
    summaries: dict[str, Any] = field(default_factory=dict)
    knowledge_context: dict[str, Any] = field(default_factory=dict)
    diagnostics: dict[str, Any] = field(default_factory=dict)
    input_dependencies: list[str] = field(default_factory=list)
    evidence_refs: list[str] = field(default_factory=list)
    derivation_notes: list[str] = field(default_factory=list)
    evidence: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class StabilitySignalsPackPayload:
    scope: dict[str, Any]
    objects: list[dict[str, Any]] = field(default_factory=list)
    summaries: dict[str, Any] = field(default_factory=dict)
    knowledge_context: dict[str, Any] = field(default_factory=dict)
    diagnostics: dict[str, Any] = field(default_factory=dict)
    input_dependencies: list[str] = field(default_factory=list)
    evidence_refs: list[str] = field(default_factory=list)
    derivation_notes: list[str] = field(default_factory=list)
    evidence: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class ImpactSignalsPackPayload:
    scope: dict[str, Any]
    objects: list[dict[str, Any]] = field(default_factory=list)
    summaries: dict[str, Any] = field(default_factory=dict)
    knowledge_context: dict[str, Any] = field(default_factory=dict)
    diagnostics: dict[str, Any] = field(default_factory=dict)
    input_dependencies: list[str] = field(default_factory=list)
    evidence_refs: list[str] = field(default_factory=list)
    derivation_notes: list[str] = field(default_factory=list)
    evidence: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class ComparisonSignalsPackPayload:
    scope: dict[str, Any]
    comparison_baseline: dict[str, Any] = field(default_factory=dict)
    objects: list[dict[str, Any]] = field(default_factory=list)
    summaries: dict[str, Any] = field(default_factory=dict)
    knowledge_context: dict[str, Any] = field(default_factory=dict)
    diagnostics: dict[str, Any] = field(default_factory=dict)
    input_dependencies: list[str] = field(default_factory=list)
    evidence_refs: list[str] = field(default_factory=list)
    derivation_notes: list[str] = field(default_factory=list)
    evidence: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class PageExperiencePackPayload:
    scope: dict[str, Any]
    pages: list[dict[str, Any]] = field(default_factory=list)
    performance_summary: dict[str, Any] = field(default_factory=dict)
    js_error_summary: dict[str, Any] = field(default_factory=dict)
    browser_distribution: list[dict[str, Any]] = field(default_factory=list)
    geo_distribution: list[dict[str, Any]] = field(default_factory=list)
    platform_distribution: list[dict[str, Any]] = field(default_factory=list)
    related_actions: list[dict[str, Any]] = field(default_factory=list)
    related_dependencies: list[dict[str, Any]] = field(default_factory=list)
    page_links: list[dict[str, Any]] = field(default_factory=list)
    primary_console_url: str | None = None
    related_console_urls: list[str] = field(default_factory=list)
    screenshot_hints: list[dict[str, Any]] = field(default_factory=list)
    metric_semantics: list[dict[str, Any]] = field(default_factory=list)
    coverage_boundary: dict[str, Any] = field(default_factory=dict)
    evidence_linkage: dict[str, Any] = field(default_factory=dict)
    knowledge_context: dict[str, Any] = field(default_factory=dict)
    input_dependencies: list[str] = field(default_factory=list)
    evidence_refs: list[str] = field(default_factory=list)
    derivation_notes: list[str] = field(default_factory=list)
    evidence: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class DataExportPackPayload:
    scope: dict[str, Any]
    available_exports: list[dict[str, Any]] = field(default_factory=list)
    selected_export: dict[str, Any] = field(default_factory=dict)
    execution: dict[str, Any] = field(default_factory=dict)
    diagnostics: dict[str, Any] = field(default_factory=dict)
    page_links: list[dict[str, Any]] = field(default_factory=list)
    primary_console_url: str | None = None
    related_console_urls: list[str] = field(default_factory=list)
    screenshot_hints: list[dict[str, Any]] = field(default_factory=list)
    metric_semantics: list[dict[str, Any]] = field(default_factory=list)
    coverage_boundary: dict[str, Any] = field(default_factory=dict)
    evidence_linkage: dict[str, Any] = field(default_factory=dict)
    input_dependencies: list[str] = field(default_factory=list)
    derivation_notes: list[str] = field(default_factory=list)
    evidence: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class ScreenshotIndexPackPayload:
    scope: dict[str, Any]
    screenshot_cards: list[dict[str, Any]] = field(default_factory=list)
    page_links: list[dict[str, Any]] = field(default_factory=list)
    primary_console_url: str | None = None
    related_console_urls: list[str] = field(default_factory=list)
    coverage_boundary: dict[str, Any] = field(default_factory=dict)
    evidence_linkage: dict[str, Any] = field(default_factory=dict)
    input_dependencies: list[str] = field(default_factory=list)
    derivation_notes: list[str] = field(default_factory=list)
    evidence: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class KnowledgeContextPackPayload:
    scope: dict[str, Any]
    knowledge_scope: dict[str, Any] = field(default_factory=dict)
    confirmed_knowledge_summary: dict[str, Any] = field(default_factory=dict)
    pending_proposals_summary: dict[str, Any] = field(default_factory=dict)
    recent_judgment_logs: list[dict[str, Any]] = field(default_factory=list)
    core_context: dict[str, Any] = field(default_factory=dict)
    missing_items: list[str] = field(default_factory=list)
    source_summary: dict[str, Any] = field(default_factory=dict)
    input_dependencies: list[str] = field(default_factory=list)
    evidence_refs: list[str] = field(default_factory=list)
    derivation_notes: list[str] = field(default_factory=list)
    evidence: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class KnowledgeUpdateProposalPackPayload:
    scope: dict[str, Any]
    knowledge_scope: dict[str, Any] = field(default_factory=dict)
    received_proposals: list[dict[str, Any]] = field(default_factory=list)
    normalized_proposals: list[dict[str, Any]] = field(default_factory=list)
    merge_summary: dict[str, Any] = field(default_factory=dict)
    conflicts: list[dict[str, Any]] = field(default_factory=list)
    pending_proposals: list[dict[str, Any]] = field(default_factory=list)
    review_queue_snapshot: dict[str, Any] = field(default_factory=dict)
    input_dependencies: list[str] = field(default_factory=list)
    evidence_refs: list[str] = field(default_factory=list)
    derivation_notes: list[str] = field(default_factory=list)
    evidence: list[dict[str, Any]] = field(default_factory=list)
