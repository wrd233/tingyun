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
    REPORT_FACT = "report_fact_pack"


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
