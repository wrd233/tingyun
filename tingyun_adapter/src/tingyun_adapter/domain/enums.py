from __future__ import annotations

from enum import Enum


class PackType(str, Enum):
    SYSTEM_SNAPSHOT = "system_snapshot"
    ACTION_HOTSPOT = "action_hotspot_pack"
    TRACE_CASE = "trace_case_pack"
    DIAGNOSTIC_CANDIDATE = "diagnostic_candidate_pack"
    ACTION_FACT_SHEET = "action_fact_sheet"
    TRACE_FACT_SHEET = "trace_fact_sheet"
    DATABASE_COMPONENT = "database_component_pack"
    NOSQL_COMPONENT = "nosql_component_pack"
    CONNECTION_POOL = "connection_pool_pack"
    INSTANCE_ANALYSIS = "instance_analysis_pack"
    TOPOLOGY_DEPENDENCY = "topology_dependency_pack"
    EXTERNAL_DEPENDENCY = "external_dependency_pack"
    SLOW_SQL = "slow_sql_pack"
    SQL_FACT_SHEET = "sql_fact_sheet"
    ACTION_DEPENDENCY_BREAKDOWN = "action_dependency_breakdown_pack"
    REPORT_FACT = "report_fact_pack"
    BUSINESS_LABELS = "business_labels_pack"
    STABILITY_SIGNALS = "stability_signals_pack"
    IMPACT_SIGNALS = "impact_signals_pack"
    COMPARISON_SIGNALS = "comparison_signals_pack"
    PAGE_EXPERIENCE = "page_experience_pack"
    SCREENSHOT_INDEX = "screenshot_index_pack"
    KNOWLEDGE_CONTEXT = "knowledge_context_pack"
    KNOWLEDGE_UPDATE_PROPOSAL = "knowledge_update_proposal_pack"


class RelationType(str, Enum):
    BELONGS_TO = "belongs_to"
    RUNS_ON = "runs_on"
    DEPENDS_ON = "depends_on"
    TRACED_BY = "traced_by"
    IMPACTED_BY = "impacted_by"
    DERIVED_FROM = "derived_from"


class TraceSelectionStrategy(str, Enum):
    SLOWEST = "slowest"
    NEWEST = "newest"
    HIGHEST_ERROR = "highest_error"
