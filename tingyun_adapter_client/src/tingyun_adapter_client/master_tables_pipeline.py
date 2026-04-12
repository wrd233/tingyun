from __future__ import annotations

import csv
import hashlib
import json
import re
import subprocess
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .xls_parsing import parse_component_operation_xls

try:
    from tingyun_adapter.usecases.deep_dive_protocol import build_deep_dive_seed as _adapter_build_deep_dive_seed
except Exception:  # pragma: no cover - optional cross-project import
    _adapter_build_deep_dive_seed = None


CSV_EXPORT_PATTERNS = {
    "application": "graph_overview_export_application__*.csv",
    "request_overview": "graph_overview_export_request__*.csv",
    "action_list": "action_list_export__*.csv",
    "interface_cluster": "interface_list_export__*.csv",
}

SUMMARY_PATTERNS = {
    "application": "graph_overview_export_application__summary.json",
    "request_overview": "graph_overview_export_request__summary.json",
    "action_list": "action_list_export__summary.json",
    "interface_cluster": "interface_list_export__summary.json",
    "sql_database": "component_analysis_export_database__summary.json",
    "nosql": "component_analysis_export_nosql__summary.json",
}

APPLICATION_PREPARED_COLUMNS = [
    "object_id",
    "object_type",
    "system_key",
    "batch_key",
    "application_name",
    "health_status",
    "apdex",
    "score",
    "response_p50_ms",
    "tps",
    "request_count",
    "error_rate_pct",
    "error_count",
    "slow_count",
    "bucket_hits",
    "screening_score",
    "screening_reason",
    "selected_for_master",
    "source_case_key",
    "source_export_key",
    "source_file",
    "source_summary_file",
]

REQUEST_PREPARED_COLUMNS = [
    "object_id",
    "object_type",
    "system_key",
    "batch_key",
    "canonical_name",
    "display_name",
    "alias_name",
    "application_name",
    "request_type",
    "interface_cluster_key",
    "avg_rt_ms",
    "p50_ms",
    "p75_ms",
    "p95_ms",
    "p99_ms",
    "apdex",
    "total_time_ms",
    "time_share_pct",
    "request_count",
    "tps",
    "error_rate_pct",
    "error_count",
    "slow_count",
    "exception_count",
    "bucket_hits",
    "screening_score",
    "screening_reason",
    "selected_for_master",
    "source_case_key",
    "source_export_key",
    "source_file",
    "source_summary_file",
]

INTERFACE_PREPARED_COLUMNS = [
    "object_id",
    "object_type",
    "system_key",
    "batch_key",
    "cluster_name",
    "application_name",
    "total_time_ms",
    "avg_rt_ms",
    "request_count",
    "tps",
    "error_rate_pct",
    "error_count",
    "bucket_hits",
    "screening_score",
    "screening_reason",
    "selected_for_master",
    "source_case_key",
    "source_export_key",
    "source_file",
    "source_summary_file",
]

SQL_PREPARED_COLUMNS = [
    "object_id",
    "object_type",
    "system_key",
    "batch_key",
    "source_db_key",
    "source_db_name",
    "source_file",
    "source_summary_file",
    "source_case_key",
    "source_export_key",
    "source_component_key",
    "source_component_name",
    "source_component_subtype",
    "source_row_rank_in_db",
    "source_total_rows_in_db",
    "sql_group_key",
    "representative_sql",
    "query_object_hint",
    "avg_rt_ms",
    "total_time_ms",
    "qps",
    "exec_count",
    "error_count",
    "slow_count",
    "bucket_hits",
    "screening_score",
    "screening_reason",
    "selected_by_global_rank",
    "selected_by_db_rank",
    "selected_for_master",
    "parse_mode",
]

NOSQL_PREPARED_COLUMNS = [
    "object_id",
    "object_type",
    "system_key",
    "batch_key",
    "source_component_key",
    "source_component_name",
    "source_component_subtype",
    "source_file",
    "source_summary_file",
    "source_case_key",
    "source_export_key",
    "command_name",
    "representative_command",
    "avg_rt_ms",
    "total_time_ms",
    "qps",
    "exec_count",
    "error_count",
    "slow_count",
    "bucket_hits",
    "screening_score",
    "screening_reason",
    "selected_for_master",
    "parse_mode",
]

MASTER_COLUMNS = {
    "application_master.csv": [
        "object_id",
        "object_type",
        "system_key",
        "batch_key",
        "application_name",
        "health_status",
        "apdex",
        "score",
        "response_p50_ms",
        "tps",
        "request_count",
        "error_rate_pct",
        "error_count",
        "slow_count",
        "bucket_hits",
        "screening_score",
        "screening_reason",
        "selected_for_master",
        "selected_for_deep_dive",
        "followup_status",
        "followup_note",
        "deep_dive_count",
        "deep_dive_status",
        "latest_deep_dive_id",
        "latest_deep_dive_at",
        "evidence_status",
        "related_object_ids",
        "report_group_hint",
        "writing_note",
    ],
    "request_master.csv": [
        "object_id",
        "object_type",
        "system_key",
        "batch_key",
        "canonical_name",
        "display_name",
        "alias_name",
        "application_name",
        "request_type",
        "interface_cluster_key",
        "avg_rt_ms",
        "p50_ms",
        "p75_ms",
        "p95_ms",
        "p99_ms",
        "apdex",
        "total_time_ms",
        "time_share_pct",
        "request_count",
        "tps",
        "error_rate_pct",
        "error_count",
        "slow_count",
        "exception_count",
        "bucket_hits",
        "screening_score",
        "screening_reason",
        "selected_for_master",
        "selected_for_deep_dive",
        "followup_status",
        "followup_note",
        "deep_dive_count",
        "deep_dive_status",
        "latest_deep_dive_id",
        "latest_deep_dive_at",
        "evidence_status",
        "related_sql_count",
        "related_object_ids",
        "report_group_hint",
        "writing_note",
    ],
    "interface_cluster_master.csv": [
        "object_id",
        "object_type",
        "system_key",
        "batch_key",
        "cluster_name",
        "application_name",
        "total_time_ms",
        "avg_rt_ms",
        "request_count",
        "tps",
        "error_rate_pct",
        "error_count",
        "related_request_count",
        "related_request_ids",
        "bucket_hits",
        "screening_score",
        "screening_reason",
        "selected_for_master",
        "selected_for_deep_dive",
        "followup_status",
        "followup_note",
        "deep_dive_count",
        "deep_dive_status",
        "latest_deep_dive_id",
        "latest_deep_dive_at",
        "evidence_status",
        "related_object_ids",
        "report_group_hint",
        "writing_note",
    ],
    "sql_master.csv": [
        "object_id",
        "object_type",
        "system_key",
        "batch_key",
        "source_db_key",
        "source_db_name",
        "sql_group_key",
        "representative_sql",
        "query_object_hint",
        "avg_rt_ms",
        "total_time_ms",
        "qps",
        "exec_count",
        "error_count",
        "slow_count",
        "bucket_hits",
        "screening_score",
        "screening_reason",
        "selected_by_global_rank",
        "selected_by_db_rank",
        "selected_for_master",
        "selected_for_deep_dive",
        "followup_status",
        "followup_note",
        "deep_dive_count",
        "deep_dive_status",
        "latest_deep_dive_id",
        "latest_deep_dive_at",
        "evidence_status",
        "related_request_ids",
        "related_object_ids",
        "report_group_hint",
        "writing_note",
    ],
    "nosql_master.csv": [
        "object_id",
        "object_type",
        "system_key",
        "batch_key",
        "source_component_key",
        "source_component_name",
        "source_component_subtype",
        "command_name",
        "representative_command",
        "avg_rt_ms",
        "total_time_ms",
        "qps",
        "exec_count",
        "error_count",
        "slow_count",
        "bucket_hits",
        "screening_score",
        "screening_reason",
        "selected_for_master",
        "selected_for_deep_dive",
        "followup_status",
        "followup_note",
        "deep_dive_count",
        "deep_dive_status",
        "latest_deep_dive_id",
        "latest_deep_dive_at",
        "evidence_status",
        "related_object_ids",
        "report_group_hint",
        "writing_note",
    ],
}

EVIDENCE_INDEX_COLUMNS = {
    "request_evidence_index.csv": [
        "object_id",
        "object_type",
        "latest_deep_dive_id",
        "deep_dive_status",
        "followup_status",
        "evidence_status",
        "page_link_count",
        "trace_link_count",
        "screenshot_hint_status",
        "related_object_ids",
        "writing_note",
    ],
    "sql_evidence_index.csv": [
        "object_id",
        "object_type",
        "latest_deep_dive_id",
        "deep_dive_status",
        "followup_status",
        "evidence_status",
        "page_link_count",
        "trace_link_count",
        "screenshot_hint_status",
        "related_request_ids",
        "writing_note",
    ],
}

DEEP_DIVE_REGISTRY_COLUMNS = [
    "deep_dive_id",
    "object_id",
    "object_type",
    "system_key",
    "batch_key",
    "source_master_table",
    "deep_dive_kind",
    "deep_dive_scope",
    "pack_source",
    "status",
    "summary",
    "evidence_count",
    "page_link_count",
    "screenshot_hint_count",
    "generated_at",
    "bundle_path",
    "related_object_ids",
    "suspected_cluster_key",
    "report_group_hint",
]

DEEP_DIVE_BUNDLE_TYPES = [
    "request",
    "sql",
    "interface_cluster",
    "application",
    "dependency",
    "shared",
]

DEEP_DIVE_BUNDLE_FILE_COLUMNS = {
    "evidence_index.csv": ["evidence_id", "evidence_type", "source_pack", "source_ref", "summary", "status"],
    "screenshot_hints.csv": ["screenshot_purpose", "page_url", "suggested_area", "subject", "usage_note"],
}

MASTER_FILE_BY_OBJECT_TYPE = {
    "application": "application_master.csv",
    "request": "request_master.csv",
    "interface_cluster": "interface_cluster_master.csv",
    "sql": "sql_master.csv",
    "nosql": "nosql_master.csv",
}

SUPPORTED_DEEP_DIVE_OBJECT_TYPES = {"request", "sql", "interface_cluster"}

DEFAULT_RULES = {
    "application": {
        "min_apdex": 0.95,
        "min_score": 95.0,
        "min_error_rate_pct": 1.0,
        "min_slow_count": 50,
        "top_n": 10,
    },
    "request": {
        "high_avg_rt_ms": 1000.0,
        "high_total_time_ms": 100000.0,
        "high_error_rate_pct": 1.0,
        "high_slow_count": 10,
        "high_error_count": 3,
        "low_freq_outlier_rt_ms": 3000.0,
        "low_freq_request_count": 3,
        "top_n": 25,
    },
    "interface_cluster": {
        "high_avg_rt_ms": 1000.0,
        "high_total_time_ms": 100000.0,
        "high_error_rate_pct": 1.0,
        "top_n": 15,
    },
    "sql": {
        "high_avg_rt_ms": 800.0,
        "high_total_time_ms": 100000.0,
        "high_exec_count": 100.0,
        "global_top_n": 20,
        "per_db_top_n": 3,
    },
    "nosql": {
        "high_avg_rt_ms": 800.0,
        "high_total_time_ms": 10000.0,
        "high_exec_count": 1000.0,
        "top_n": 10,
    },
}


@dataclass
class ExportEntry:
    object_family: str
    source_case_key: str
    source_export_key: str
    source_component_key: str
    source_component_name: str
    source_component_subtype: str
    source_db_key: str
    source_db_name: str
    source_file: str
    source_summary_file: str
    sha1: str
    byte_size: int
    collected_at: str
    mime_type: str

    def to_dict(self, *, system_key: str, batch_key: str) -> dict[str, Any]:
        return {
            "system_key": system_key,
            "batch_key": batch_key,
            "object_family": self.object_family,
            "source_case_key": self.source_case_key,
            "source_export_key": self.source_export_key,
            "source_component_key": self.source_component_key,
            "source_component_name": self.source_component_name,
            "source_component_subtype": self.source_component_subtype,
            "source_db_key": self.source_db_key,
            "source_db_name": self.source_db_name,
            "source_file": self.source_file,
            "source_summary_file": self.source_summary_file,
            "sha1": self.sha1,
            "byte_size": self.byte_size,
            "collected_at": self.collected_at,
            "mime_type": self.mime_type,
        }


def prepare_master_table_inputs(
    diagnostics_dir: str | Path,
    *,
    system_key: str,
    batch_key: str,
    rules: dict[str, Any] | None = None,
) -> dict[str, Any]:
    diagnostics_root = Path(diagnostics_dir).expanduser().resolve()
    raw_root = diagnostics_root / "00_raw_exports"
    prepared_root = diagnostics_root / "01_prepared_tables"
    raw_root.mkdir(parents=True, exist_ok=True)
    prepared_root.mkdir(parents=True, exist_ok=True)

    effective_rules = _merge_rules(DEFAULT_RULES, rules or {})
    registry_entries = build_export_registry(diagnostics_root, system_key=system_key, batch_key=batch_key)
    _write_json(raw_root / "export_registry.json", {"exports": registry_entries})

    grouped = _group_registry(registry_entries)
    output_files: list[str] = []
    warnings: list[str] = []

    application_rows = _prepare_application_rows(grouped["application"], system_key, batch_key, effective_rules["application"])
    _write_csv(prepared_root / "application_prepared.csv", APPLICATION_PREPARED_COLUMNS, application_rows)
    output_files.append("application_prepared.csv")

    request_rows = _prepare_request_rows(
        grouped["action_list"],
        grouped["request_overview"],
        system_key,
        batch_key,
        effective_rules["request"],
    )
    _write_csv(prepared_root / "request_prepared.csv", REQUEST_PREPARED_COLUMNS, request_rows)
    output_files.append("request_prepared.csv")

    interface_rows = _prepare_interface_rows(grouped["interface_cluster"], system_key, batch_key, effective_rules["interface_cluster"])
    _write_csv(prepared_root / "interface_cluster_prepared.csv", INTERFACE_PREPARED_COLUMNS, interface_rows)
    output_files.append("interface_cluster_prepared.csv")

    sql_rows, sql_warnings = _prepare_sql_rows(grouped["sql_database"], system_key, batch_key, effective_rules["sql"])
    warnings.extend(sql_warnings)
    _write_csv(prepared_root / "sql_prepared_full.csv", SQL_PREPARED_COLUMNS, sql_rows)
    output_files.append("sql_prepared_full.csv")
    for db_key, db_rows in _group_rows_by(sql_rows, "source_db_key").items():
        _write_csv(prepared_root / f"sql_prepared__{db_key}.csv", SQL_PREPARED_COLUMNS, db_rows)
        output_files.append(f"sql_prepared__{db_key}.csv")

    nosql_rows, nosql_warnings = _prepare_nosql_rows(grouped["nosql"], system_key, batch_key, effective_rules["nosql"])
    warnings.extend(nosql_warnings)
    _write_csv(prepared_root / "nosql_prepared.csv", NOSQL_PREPARED_COLUMNS, nosql_rows)
    output_files.append("nosql_prepared.csv")

    summary = {
        "system_key": system_key,
        "batch_key": batch_key,
        "diagnostics_dir": str(diagnostics_root),
        "registry_count": len(registry_entries),
        "prepared_tables": output_files,
        "row_counts": {
            "application": len(application_rows),
            "request": len(request_rows),
            "interface_cluster": len(interface_rows),
            "sql": len(sql_rows),
            "nosql": len(nosql_rows),
        },
        "warnings": warnings,
    }
    _write_json(prepared_root / "preparation_summary.json", summary)
    return summary


def materialize_master_tables(
    diagnostics_dir: str | Path,
    *,
    system_key: str,
    batch_key: str,
) -> dict[str, Any]:
    diagnostics_root = Path(diagnostics_dir).expanduser().resolve()
    prepared_root = diagnostics_root / "01_prepared_tables"
    master_root = diagnostics_root / "02_master_tables"
    evidence_root = diagnostics_root / "03_evidence_indexes"
    deep_dive_root = diagnostics_root / "04_deep_dive"
    master_root.mkdir(parents=True, exist_ok=True)
    evidence_root.mkdir(parents=True, exist_ok=True)

    outputs: list[str] = []
    row_counts: dict[str, int] = {}

    application_master = _materialize_master(
        prepared_root / "application_prepared.csv",
        MASTER_COLUMNS["application_master.csv"],
        object_type="application",
    )
    _write_csv(master_root / "application_master.csv", MASTER_COLUMNS["application_master.csv"], application_master)
    outputs.append("application_master.csv")
    row_counts["application_master"] = len(application_master)

    request_master = _materialize_master(
        prepared_root / "request_prepared.csv",
        MASTER_COLUMNS["request_master.csv"],
        object_type="request",
    )
    _write_csv(master_root / "request_master.csv", MASTER_COLUMNS["request_master.csv"], request_master)
    outputs.append("request_master.csv")
    row_counts["request_master"] = len(request_master)

    interface_master = _materialize_master(
        prepared_root / "interface_cluster_prepared.csv",
        MASTER_COLUMNS["interface_cluster_master.csv"],
        object_type="interface_cluster",
    )
    _write_csv(master_root / "interface_cluster_master.csv", MASTER_COLUMNS["interface_cluster_master.csv"], interface_master)
    outputs.append("interface_cluster_master.csv")
    row_counts["interface_cluster_master"] = len(interface_master)

    sql_master = _materialize_master(
        prepared_root / "sql_prepared_full.csv",
        MASTER_COLUMNS["sql_master.csv"],
        object_type="sql",
    )
    _write_csv(master_root / "sql_master.csv", MASTER_COLUMNS["sql_master.csv"], sql_master)
    outputs.append("sql_master.csv")
    row_counts["sql_master"] = len(sql_master)

    nosql_master = _materialize_master(
        prepared_root / "nosql_prepared.csv",
        MASTER_COLUMNS["nosql_master.csv"],
        object_type="nosql",
    )
    _write_csv(master_root / "nosql_master.csv", MASTER_COLUMNS["nosql_master.csv"], nosql_master)
    outputs.append("nosql_master.csv")
    row_counts["nosql_master"] = len(nosql_master)

    request_evidence_rows = [
        {
            "object_id": row["object_id"],
            "object_type": "request",
            "latest_deep_dive_id": row.get("latest_deep_dive_id", ""),
            "deep_dive_status": row.get("deep_dive_status", ""),
            "followup_status": row["followup_status"],
            "evidence_status": row.get("evidence_status", "待补证据"),
            "page_link_count": "",
            "trace_link_count": "",
            "screenshot_hint_status": "待补充",
            "related_object_ids": row.get("related_object_ids", ""),
            "writing_note": row.get("writing_note", ""),
        }
        for row in request_master
    ]
    _write_csv(evidence_root / "request_evidence_index.csv", EVIDENCE_INDEX_COLUMNS["request_evidence_index.csv"], request_evidence_rows)
    outputs.append("request_evidence_index.csv")
    row_counts["request_evidence_index"] = len(request_evidence_rows)

    sql_evidence_rows = [
        {
            "object_id": row["object_id"],
            "object_type": "sql",
            "latest_deep_dive_id": row.get("latest_deep_dive_id", ""),
            "deep_dive_status": row.get("deep_dive_status", ""),
            "followup_status": row["followup_status"],
            "evidence_status": row.get("evidence_status", "待补证据"),
            "page_link_count": "",
            "trace_link_count": "",
            "screenshot_hint_status": "待补充",
            "related_request_ids": row.get("related_request_ids", ""),
            "writing_note": row.get("writing_note", ""),
        }
        for row in sql_master
    ]
    _write_csv(evidence_root / "sql_evidence_index.csv", EVIDENCE_INDEX_COLUMNS["sql_evidence_index.csv"], sql_evidence_rows)
    outputs.append("sql_evidence_index.csv")
    row_counts["sql_evidence_index"] = len(sql_evidence_rows)

    deep_dive_summary = initialize_deep_dive_workspace(
        diagnostics_root,
        system_key=system_key,
        batch_key=batch_key,
    )
    sync_summary = sync_master_tables_with_deep_dive_registry(
        diagnostics_root,
        system_key=system_key,
        batch_key=batch_key,
    )
    evidence_sync_summary = sync_evidence_indexes_with_deep_dive_registry(
        diagnostics_root,
        system_key=system_key,
        batch_key=batch_key,
    )
    outputs.append(str((deep_dive_root / "deep_dive_registry.csv").relative_to(diagnostics_root)))
    row_counts["deep_dive_registry"] = sync_summary["registry_count"]

    summary = {
        "system_key": system_key,
        "batch_key": batch_key,
        "diagnostics_dir": str(diagnostics_root),
        "outputs": outputs,
        "row_counts": row_counts,
        "deep_dive_workspace": deep_dive_summary,
        "deep_dive_sync": sync_summary,
        "deep_dive_evidence_sync": evidence_sync_summary,
    }
    _write_json(master_root / "materialization_summary.json", summary)
    return summary


def initialize_deep_dive_workspace(
    diagnostics_dir: str | Path,
    *,
    system_key: str,
    batch_key: str,
) -> dict[str, Any]:
    diagnostics_root = Path(diagnostics_dir).expanduser().resolve()
    deep_dive_root = diagnostics_root / "04_deep_dive"
    deep_dive_root.mkdir(parents=True, exist_ok=True)

    created_dirs: list[str] = []
    for object_type in DEEP_DIVE_BUNDLE_TYPES:
        target_dir = deep_dive_root / object_type
        target_dir.mkdir(parents=True, exist_ok=True)
        created_dirs.append(str(target_dir.relative_to(diagnostics_root)))

    registry_path = deep_dive_root / "deep_dive_registry.csv"
    if not registry_path.exists():
        _write_csv(registry_path, DEEP_DIVE_REGISTRY_COLUMNS, [])

    return {
        "system_key": system_key,
        "batch_key": batch_key,
        "root": str(deep_dive_root),
        "registry_path": str(registry_path),
        "bundle_directories": created_dirs,
    }


def initialize_deep_dive_bundle(
    diagnostics_dir: str | Path,
    *,
    system_key: str,
    batch_key: str,
    object_id: str,
    object_type: str,
    source_master_table: str,
    deep_dive_id: str,
    deep_dive_kind: str,
    deep_dive_scope: str,
    pack_source: str,
    summary: str = "",
    status: str = "initialized",
    generated_at: str | None = None,
    related_object_ids: str = "",
    suspected_cluster_key: str = "",
    report_group_hint: str = "",
) -> dict[str, Any]:
    diagnostics_root = Path(diagnostics_dir).expanduser().resolve()
    initialize_deep_dive_workspace(diagnostics_root, system_key=system_key, batch_key=batch_key)
    deep_dive_root = diagnostics_root / "04_deep_dive"
    object_dir = deep_dive_root / _bundle_object_dir(object_type) / _sanitize_path_segment(object_id)
    bundle_dir = object_dir / _sanitize_path_segment(deep_dive_id)
    bundle_dir.mkdir(parents=True, exist_ok=True)
    (bundle_dir / "pack_payloads").mkdir(parents=True, exist_ok=True)

    manifest = {
        "deep_dive_id": deep_dive_id,
        "object_id": object_id,
        "object_type": object_type,
        "system_key": system_key,
        "batch_key": batch_key,
        "source_master_table": source_master_table,
        "deep_dive_kind": deep_dive_kind,
        "deep_dive_scope": deep_dive_scope,
        "pack_source": pack_source,
        "status": status,
        "summary": summary,
        "generated_at": generated_at or datetime.now(timezone.utc).isoformat(),
        "bundle_path": str(bundle_dir),
        "related_object_ids": related_object_ids,
        "suspected_cluster_key": suspected_cluster_key,
        "report_group_hint": report_group_hint,
    }
    _write_json(bundle_dir / "summary.json", manifest)
    _write_json(bundle_dir / "page_links.json", {"page_links": []})
    _write_json(bundle_dir / "related_objects.json", {"related_object_ids": _split_semicolon_list(related_object_ids)})
    _write_csv(bundle_dir / "evidence_index.csv", DEEP_DIVE_BUNDLE_FILE_COLUMNS["evidence_index.csv"], [])
    _write_csv(bundle_dir / "screenshot_hints.csv", DEEP_DIVE_BUNDLE_FILE_COLUMNS["screenshot_hints.csv"], [])
    (bundle_dir / "notes.md").write_text("# Notes\n\n", encoding="utf-8")

    registry_path = deep_dive_root / "deep_dive_registry.csv"
    registry_rows = _read_csv_rows(registry_path) if registry_path.exists() else []
    if not any(str(item.get("deep_dive_id") or "") == deep_dive_id for item in registry_rows):
        registry_rows.append(
            {
                "deep_dive_id": deep_dive_id,
                "object_id": object_id,
                "object_type": object_type,
                "system_key": system_key,
                "batch_key": batch_key,
                "source_master_table": source_master_table,
                "deep_dive_kind": deep_dive_kind,
                "deep_dive_scope": deep_dive_scope,
                "pack_source": pack_source,
                "status": status,
                "summary": summary,
                "evidence_count": "0",
                "page_link_count": "0",
                "screenshot_hint_count": "0",
                "generated_at": manifest["generated_at"],
                "bundle_path": str(bundle_dir),
                "related_object_ids": related_object_ids,
                "suspected_cluster_key": suspected_cluster_key,
                "report_group_hint": report_group_hint,
            }
        )
        _write_csv(registry_path, DEEP_DIVE_REGISTRY_COLUMNS, registry_rows)

    return manifest


def sync_master_tables_with_deep_dive_registry(
    diagnostics_dir: str | Path,
    *,
    system_key: str,
    batch_key: str,
) -> dict[str, Any]:
    diagnostics_root = Path(diagnostics_dir).expanduser().resolve()
    initialize_deep_dive_workspace(diagnostics_root, system_key=system_key, batch_key=batch_key)
    deep_dive_root = diagnostics_root / "04_deep_dive"
    registry_path = deep_dive_root / "deep_dive_registry.csv"
    registry_rows = _read_csv_rows(registry_path) if registry_path.exists() else []
    registry_index = _index_deep_dive_registry(registry_rows)

    updated_files: list[str] = []
    object_types = {
        "application_master.csv": "application",
        "request_master.csv": "request",
        "interface_cluster_master.csv": "interface_cluster",
        "sql_master.csv": "sql",
        "nosql_master.csv": "nosql",
    }
    for filename, object_type in object_types.items():
        master_path = diagnostics_root / "02_master_tables" / filename
        if not master_path.exists():
            continue
        rows = _read_csv_rows(master_path)
        synced_rows = [
            _apply_deep_dive_registry_state(row, object_type, registry_index.get(str(row.get("object_id") or ""), []))
            for row in rows
        ]
        _write_csv(master_path, MASTER_COLUMNS[filename], synced_rows)
        updated_files.append(filename)

    return {
        "system_key": system_key,
        "batch_key": batch_key,
        "registry_count": len(registry_rows),
        "updated_master_tables": updated_files,
    }


def materialize_deep_dive_from_source(
    diagnostics_dir: str | Path,
    *,
    system_key: str,
    batch_key: str,
    source_json: str | Path,
) -> dict[str, Any]:
    diagnostics_root = Path(diagnostics_dir).expanduser().resolve()
    source_path = Path(source_json).expanduser().resolve()
    source_payload = _load_deep_dive_source_payload(source_path)
    targets = list(source_payload.get("deep_dive_targets") or [])
    expansions = list(source_payload.get("selected_target_expansions") or [])
    expansions_by_key = _group_expansions_by_candidate_key(expansions)

    initialize_deep_dive_workspace(diagnostics_root, system_key=system_key, batch_key=batch_key)
    registry_rows = _read_csv_rows(diagnostics_root / "04_deep_dive" / "deep_dive_registry.csv")
    materialized: list[dict[str, Any]] = []
    warnings: list[str] = []

    for target in targets:
        seed = _coerce_deep_dive_seed(target)
        object_type = str(seed.get("object_type") or "")
        if object_type not in SUPPORTED_DEEP_DIVE_OBJECT_TYPES:
            warnings.append(f"Skipped deep-dive target {target.get('candidate_key') or target.get('display_name')}: unsupported object_type={object_type}")
            continue
        matched = _match_seed_to_master_object(diagnostics_root, seed, expansions_by_key.get(str(target.get("candidate_key") or ""), []))
        if matched is None:
            warnings.append(f"Skipped deep-dive target {target.get('candidate_key') or target.get('display_name')}: no matching master-table object")
            continue
        object_id = matched["object_id"]
        source_master_table = matched["source_master_table"]
        bundle_input = _build_bundle_input(target, seed, expansions_by_key.get(str(target.get("candidate_key") or ""), []))
        existing = _find_existing_deep_dive_row(
            registry_rows,
            object_id=object_id,
            deep_dive_kind=str(seed.get("deep_dive_kind") or ""),
            pack_source=str(bundle_input["pack_source"]),
            summary=str(bundle_input["summary"]),
        )
        deep_dive_id = str(existing.get("deep_dive_id") or "") if existing else _new_deep_dive_id(target, object_id)
        generated_at = str(existing.get("generated_at") or "") if existing else datetime.now(timezone.utc).isoformat()
        manifest = initialize_deep_dive_bundle(
            diagnostics_root,
            system_key=system_key,
            batch_key=batch_key,
            object_id=object_id,
            object_type=object_type,
            source_master_table=source_master_table,
            deep_dive_id=deep_dive_id,
            deep_dive_kind=str(seed.get("deep_dive_kind") or ""),
            deep_dive_scope=str(seed.get("deep_dive_scope") or "local"),
            pack_source=str(bundle_input["pack_source"]),
            summary=str(bundle_input["summary"]),
            status=str(bundle_input["status"]),
            generated_at=generated_at,
            related_object_ids=";".join(seed.get("related_object_ids") or []),
            suspected_cluster_key=str(seed.get("suspected_cluster_key") or ""),
            report_group_hint=str(seed.get("report_group_hint") or ""),
        )
        _write_bundle_contents(
            Path(manifest["bundle_path"]),
            bundle_input=bundle_input,
        )
        materialized.append(
            {
                "deep_dive_id": deep_dive_id,
                "object_id": object_id,
                "object_type": object_type,
                "source_master_table": source_master_table,
                "bundle_path": manifest["bundle_path"],
            }
        )
        registry_rows = _read_csv_rows(diagnostics_root / "04_deep_dive" / "deep_dive_registry.csv")

    sync_summary = sync_master_tables_with_deep_dive_registry(
        diagnostics_root,
        system_key=system_key,
        batch_key=batch_key,
    )
    evidence_sync_summary = sync_evidence_indexes_with_deep_dive_registry(
        diagnostics_root,
        system_key=system_key,
        batch_key=batch_key,
    )
    summary = {
        "system_key": system_key,
        "batch_key": batch_key,
        "diagnostics_dir": str(diagnostics_root),
        "source_json": str(source_path),
        "source_target_count": len(targets),
        "source_expansion_count": len(expansions),
        "materialized_count": len(materialized),
        "materialized_bundles": materialized,
        "warnings": warnings,
        "deep_dive_sync": sync_summary,
        "deep_dive_evidence_sync": evidence_sync_summary,
    }
    _write_json(diagnostics_root / "04_deep_dive" / "deep_dive_materialization_summary.json", summary)
    return summary


def sync_evidence_indexes_with_deep_dive_registry(
    diagnostics_dir: str | Path,
    *,
    system_key: str,
    batch_key: str,
) -> dict[str, Any]:
    diagnostics_root = Path(diagnostics_dir).expanduser().resolve()
    registry_rows = _read_csv_rows(diagnostics_root / "04_deep_dive" / "deep_dive_registry.csv")
    registry_index = _index_deep_dive_registry(registry_rows)
    updated_files: list[str] = []

    for filename, object_type in {"request_evidence_index.csv": "request", "sql_evidence_index.csv": "sql"}.items():
        evidence_path = diagnostics_root / "03_evidence_indexes" / filename
        if not evidence_path.exists():
            continue
        rows = _read_csv_rows(evidence_path)
        updated_rows = [
            _apply_deep_dive_evidence_state(row, object_type, registry_index.get(str(row.get("object_id") or ""), []))
            for row in rows
        ]
        _write_csv(evidence_path, EVIDENCE_INDEX_COLUMNS[filename], updated_rows)
        updated_files.append(filename)

    return {
        "system_key": system_key,
        "batch_key": batch_key,
        "updated_evidence_indexes": updated_files,
    }


def build_export_registry(
    diagnostics_dir: str | Path,
    *,
    system_key: str,
    batch_key: str,
    collected_at: str | None = None,
) -> list[dict[str, Any]]:
    diagnostics_root = Path(diagnostics_dir).expanduser().resolve()
    source_root = diagnostics_root / "00_raw_exports"
    discovery_root = source_root if _has_discoverable_exports(source_root) else diagnostics_root
    collected = collected_at or datetime.now(timezone.utc).isoformat()

    entries: list[ExportEntry] = []
    for family, pattern in CSV_EXPORT_PATTERNS.items():
        for path in sorted(discovery_root.rglob(pattern)):
            if path.name.endswith("__summary.json"):
                continue
            summary_path = _find_summary_for_file(path, family)
            summary = _load_json(summary_path) if summary_path else {}
            entries.append(
                ExportEntry(
                    object_family=family,
                    source_case_key=str(summary.get("case_key") or family),
                    source_export_key=str(summary.get("selected_export", {}).get("export_key") or family),
                    source_component_key="",
                    source_component_name="",
                    source_component_subtype="",
                    source_db_key="",
                    source_db_name="",
                    source_file=str(path),
                    source_summary_file=str(summary_path) if summary_path else "",
                    sha1=_sha1_file(path),
                    byte_size=path.stat().st_size,
                    collected_at=collected,
                    mime_type=str(summary.get("execution", {}).get("mime_type") or "text/csv"),
                )
            )

    sql_entries = _discover_sql_entries(discovery_root, collected)
    nosql_entries = _discover_nosql_entries(discovery_root, collected)
    entries.extend(sql_entries)
    entries.extend(nosql_entries)
    return [entry.to_dict(system_key=system_key, batch_key=batch_key) for entry in entries]


def _discover_sql_entries(discovery_root: Path, collected_at: str) -> list[ExportEntry]:
    structured_root = discovery_root / "sql_database"
    entries: list[ExportEntry] = []
    if structured_root.exists():
        for db_dir in sorted(path for path in structured_root.iterdir() if path.is_dir()):
            files = sorted(db_dir.glob("*.xls")) + sorted(db_dir.glob("*.csv"))
            if not files:
                continue
            summary_path = db_dir / "summary.json"
            summary = _load_json(summary_path) if summary_path.exists() else {}
            source_db_key = db_dir.name
            source_db_name = str(summary.get("source_db_name") or db_dir.name)
            for path in files:
                entries.append(
                    ExportEntry(
                        object_family="sql_database",
                        source_case_key=str(summary.get("case_key") or "component_analysis_export_database"),
                        source_export_key=str(summary.get("selected_export", {}).get("export_key") or "component_analysis_export"),
                        source_component_key=str(summary.get("source_component_key") or source_db_key),
                        source_component_name=str(summary.get("source_component_name") or source_db_name),
                        source_component_subtype=str(summary.get("source_component_subtype") or ""),
                        source_db_key=source_db_key,
                        source_db_name=source_db_name,
                        source_file=str(path),
                        source_summary_file=str(summary_path) if summary_path.exists() else "",
                        sha1=_sha1_file(path),
                        byte_size=path.stat().st_size,
                        collected_at=collected_at,
                        mime_type=str(summary.get("execution", {}).get("mime_type") or _guess_mime_type(path)),
                    )
                )
        return entries

    legacy_files = sorted(discovery_root.glob("component_analysis_export_database__*.xls")) + sorted(discovery_root.glob("component_analysis_export_database__*.csv"))
    summary_path = discovery_root / SUMMARY_PATTERNS["sql_database"]
    summary = _load_json(summary_path) if summary_path.exists() else {}
    for index, path in enumerate(legacy_files, start=1):
        db_key = f"db_{index:03d}"
        entries.append(
            ExportEntry(
                object_family="sql_database",
                source_case_key=str(summary.get("case_key") or "component_analysis_export_database"),
                source_export_key=str(summary.get("selected_export", {}).get("export_key") or "component_analysis_export"),
                source_component_key=str(summary.get("source_component_key") or db_key),
                source_component_name=str(summary.get("source_component_name") or db_key),
                source_component_subtype=str(summary.get("source_component_subtype") or ""),
                source_db_key=db_key,
                source_db_name=str(summary.get("source_db_name") or db_key),
                source_file=str(path),
                source_summary_file=str(summary_path) if summary_path.exists() else "",
                sha1=_sha1_file(path),
                byte_size=path.stat().st_size,
                collected_at=collected_at,
                mime_type=str(summary.get("execution", {}).get("mime_type") or _guess_mime_type(path)),
            )
        )
    return entries


def _discover_nosql_entries(discovery_root: Path, collected_at: str) -> list[ExportEntry]:
    structured_root = discovery_root / "nosql"
    entries: list[ExportEntry] = []
    if structured_root.exists():
        for component_dir in sorted(path for path in structured_root.iterdir() if path.is_dir()):
            files = sorted(component_dir.glob("*.xls")) + sorted(component_dir.glob("*.csv"))
            if not files:
                continue
            summary_path = component_dir / "summary.json"
            summary = _load_json(summary_path) if summary_path.exists() else {}
            source_component_key = component_dir.name
            source_component_name = str(summary.get("source_component_name") or component_dir.name)
            source_component_subtype = str(summary.get("source_component_subtype") or "")
            for path in files:
                entries.append(
                    ExportEntry(
                        object_family="nosql",
                        source_case_key=str(summary.get("case_key") or "component_analysis_export_nosql"),
                        source_export_key=str(summary.get("selected_export", {}).get("export_key") or "component_analysis_export"),
                        source_component_key=source_component_key,
                        source_component_name=source_component_name,
                        source_component_subtype=source_component_subtype,
                        source_db_key="",
                        source_db_name="",
                        source_file=str(path),
                        source_summary_file=str(summary_path) if summary_path.exists() else "",
                        sha1=_sha1_file(path),
                        byte_size=path.stat().st_size,
                        collected_at=collected_at,
                        mime_type=str(summary.get("execution", {}).get("mime_type") or _guess_mime_type(path)),
                    )
                )
        return entries

    legacy_files = sorted(discovery_root.glob("component_analysis_export_nosql__*.xls")) + sorted(discovery_root.glob("component_analysis_export_nosql__*.csv"))
    summary_path = discovery_root / SUMMARY_PATTERNS["nosql"]
    summary = _load_json(summary_path) if summary_path.exists() else {}
    for path in legacy_files:
        entries.append(
            ExportEntry(
                object_family="nosql",
                source_case_key=str(summary.get("case_key") or "component_analysis_export_nosql"),
                source_export_key=str(summary.get("selected_export", {}).get("export_key") or "component_analysis_export"),
                source_component_key=str(summary.get("source_component_key") or "nosql_default"),
                source_component_name=str(summary.get("source_component_name") or ""),
                source_component_subtype=str(summary.get("source_component_subtype") or ""),
                source_db_key="",
                source_db_name="",
                source_file=str(path),
                source_summary_file=str(summary_path) if summary_path.exists() else "",
                sha1=_sha1_file(path),
                byte_size=path.stat().st_size,
                collected_at=collected_at,
                mime_type=str(summary.get("execution", {}).get("mime_type") or _guess_mime_type(path)),
            )
        )
    return entries


def _prepare_application_rows(
    entries: list[dict[str, Any]],
    system_key: str,
    batch_key: str,
    rules: dict[str, Any],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for entry in entries:
        for raw in _read_csv_rows(Path(entry["source_file"])):
            app_name = str(raw.get("应用名称") or "").strip()
            if not app_name:
                continue
            buckets: list[str] = []
            apdex = _to_float(raw.get("Apdex"))
            score = _to_float(raw.get("评分"))
            error_rate = _to_float(raw.get("错误率(%)"))
            slow_count = _to_float(raw.get("慢次数"))
            if apdex is not None and apdex < rules["min_apdex"]:
                buckets.append("low_apdex")
            if score is not None and score < rules["min_score"]:
                buckets.append("low_score")
            if error_rate is not None and error_rate >= rules["min_error_rate_pct"]:
                buckets.append("high_error_rate")
            if slow_count is not None and slow_count >= rules["min_slow_count"]:
                buckets.append("high_slow_count")
            screening_score = len(buckets)
            rows.append(
                {
                    "object_id": _hash_id(f"application:{app_name}"),
                    "object_type": "application",
                    "system_key": system_key,
                    "batch_key": batch_key,
                    "application_name": app_name,
                    "health_status": str(raw.get("健康度") or "").strip(),
                    "apdex": _stringify_number(apdex),
                    "score": _stringify_number(score),
                    "response_p50_ms": _stringify_number(_to_float(raw.get("responseP50"))),
                    "tps": _stringify_number(_to_float(raw.get("吞吐率 (/s)"))),
                    "request_count": _stringify_number(_to_float(raw.get("请求数"))),
                    "error_rate_pct": _stringify_number(error_rate),
                    "error_count": _stringify_number(_to_float(raw.get("错误次数"))),
                    "slow_count": _stringify_number(slow_count),
                    "bucket_hits": ";".join(buckets),
                    "screening_score": str(screening_score),
                    "screening_reason": "; ".join(_reason_text(buckets)),
                    "selected_for_master": "false",
                    "source_case_key": entry["source_case_key"],
                    "source_export_key": entry["source_export_key"],
                    "source_file": entry["source_file"],
                    "source_summary_file": entry["source_summary_file"],
                }
            )
    _mark_top_n(rows, rules["top_n"])
    return rows


def _prepare_request_rows(
    action_entries: list[dict[str, Any]],
    overview_entries: list[dict[str, Any]],
    system_key: str,
    batch_key: str,
    rules: dict[str, Any],
) -> list[dict[str, Any]]:
    overview_index: dict[tuple[str, str], dict[str, str]] = {}
    for entry in overview_entries:
        for raw in _read_csv_rows(Path(entry["source_file"])):
            key = (
                str(raw.get("事务名称") or "").strip(),
                str(raw.get("应用名称") or "").strip(),
            )
            if key[0]:
                overview_index[key] = raw

    rows: list[dict[str, Any]] = []
    for entry in action_entries:
        for raw in _read_csv_rows(Path(entry["source_file"])):
            canonical_name = str(raw.get("名称") or "").strip()
            alias_name = str(raw.get("事务别名") or "").strip()
            app_name = str(raw.get("应用") or "").strip()
            if not canonical_name:
                continue
            overview = overview_index.get((canonical_name, app_name), {})
            avg_rt = _to_float(raw.get("平均响应时间(ms)"))
            total_time = _to_float(raw.get("总耗时(ms)"))
            error_rate = _to_float(raw.get("错误率(%)"))
            request_count = _to_float(raw.get("请求数"))
            slow_count = _to_float(raw.get("慢次数"))
            error_count = _to_float(raw.get("错误数"))
            buckets: list[str] = []
            if avg_rt is not None and avg_rt >= rules["high_avg_rt_ms"]:
                buckets.append("high_avg_rt")
            if total_time is not None and total_time >= rules["high_total_time_ms"]:
                buckets.append("high_total_time")
            if error_rate is not None and error_rate >= rules["high_error_rate_pct"]:
                buckets.append("high_error_rate")
            if slow_count is not None and slow_count >= rules["high_slow_count"]:
                buckets.append("high_slow_count")
            if error_count is not None and error_count >= rules["high_error_count"]:
                buckets.append("high_error_count")
            if (
                request_count is not None
                and request_count <= rules["low_freq_request_count"]
                and avg_rt is not None
                and avg_rt >= rules["low_freq_outlier_rt_ms"]
            ):
                buckets.append("low_freq_outlier")
            screening_score = len(buckets)
            display_name = alias_name or canonical_name
            rows.append(
                {
                    "object_id": _hash_id(f"request:{app_name}:{canonical_name}"),
                    "object_type": "request",
                    "system_key": system_key,
                    "batch_key": batch_key,
                    "canonical_name": canonical_name,
                    "display_name": display_name,
                    "alias_name": alias_name,
                    "application_name": app_name,
                    "request_type": str(overview.get("请求类型") or "").strip(),
                    "interface_cluster_key": _hash_id(f"interface-cluster:{display_name}")[:16],
                    "avg_rt_ms": _stringify_number(avg_rt),
                    "p50_ms": _stringify_number(_to_float(overview.get("响应时间中位数(ms)"))),
                    "p75_ms": _stringify_number(_to_float(overview.get("响应时间 P75 (ms)"))),
                    "p95_ms": _stringify_number(_to_float(overview.get("响应时间 P95 (ms)"))),
                    "p99_ms": _stringify_number(_to_float(overview.get("响应时间 P99 (ms)"))),
                    "apdex": _stringify_number(_to_float(overview.get("Apdex"))),
                    "total_time_ms": _stringify_number(total_time),
                    "time_share_pct": _stringify_number(_to_float(raw.get("耗时百分比(%)"))),
                    "request_count": _stringify_number(request_count),
                    "tps": _stringify_number(_to_float(raw.get("吞吐率(tps)"))),
                    "error_rate_pct": _stringify_number(error_rate),
                    "error_count": _stringify_number(error_count),
                    "slow_count": _stringify_number(slow_count),
                    "exception_count": _stringify_number(_to_float(overview.get("异常次数"))),
                    "bucket_hits": ";".join(buckets),
                    "screening_score": str(screening_score),
                    "screening_reason": "; ".join(_reason_text(buckets)),
                    "selected_for_master": "false",
                    "source_case_key": entry["source_case_key"],
                    "source_export_key": entry["source_export_key"],
                    "source_file": entry["source_file"],
                    "source_summary_file": entry["source_summary_file"],
                }
            )
    _mark_top_n(rows, rules["top_n"])
    return rows


def _prepare_interface_rows(
    entries: list[dict[str, Any]],
    system_key: str,
    batch_key: str,
    rules: dict[str, Any],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for entry in entries:
        for raw in _read_csv_rows(Path(entry["source_file"])):
            cluster_name = str(raw.get("名称") or "").strip()
            if not cluster_name:
                continue
            avg_rt = _to_float(raw.get("平均响应时间(ms)"))
            total_time = _to_float(raw.get("总耗时(ms)"))
            error_rate = _to_float(raw.get("错误率(%)"))
            buckets: list[str] = []
            if avg_rt is not None and avg_rt >= rules["high_avg_rt_ms"]:
                buckets.append("high_avg_rt")
            if total_time is not None and total_time >= rules["high_total_time_ms"]:
                buckets.append("high_total_time")
            if error_rate is not None and error_rate >= rules["high_error_rate_pct"]:
                buckets.append("high_error_rate")
            screening_score = len(buckets)
            rows.append(
                {
                    "object_id": _hash_id(f"interface-cluster:{cluster_name}"),
                    "object_type": "interface_cluster",
                    "system_key": system_key,
                    "batch_key": batch_key,
                    "cluster_name": cluster_name,
                    "application_name": str(raw.get("应用") or "").strip(),
                    "total_time_ms": _stringify_number(total_time),
                    "avg_rt_ms": _stringify_number(avg_rt),
                    "request_count": _stringify_number(_to_float(raw.get("请求数"))),
                    "tps": _stringify_number(_to_float(raw.get("吞吐率(tps)"))),
                    "error_rate_pct": _stringify_number(error_rate),
                    "error_count": _stringify_number(_to_float(raw.get("错误数"))),
                    "bucket_hits": ";".join(buckets),
                    "screening_score": str(screening_score),
                    "screening_reason": "; ".join(_reason_text(buckets)),
                    "selected_for_master": "false",
                    "source_case_key": entry["source_case_key"],
                    "source_export_key": entry["source_export_key"],
                    "source_file": entry["source_file"],
                    "source_summary_file": entry["source_summary_file"],
                }
            )
    _mark_top_n(rows, rules["top_n"])
    return rows


def _prepare_sql_rows(
    entries: list[dict[str, Any]],
    system_key: str,
    batch_key: str,
    rules: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[str]]:
    warnings: list[str] = []
    rows: list[dict[str, Any]] = []
    for entry in entries:
        source_file = Path(entry["source_file"])
        parsed_rows, parse_warning = _load_component_operation_rows(source_file, kind="sql")
        if parse_warning:
            warnings.append(parse_warning)
        dedup: dict[str, dict[str, Any]] = {}
        for raw in parsed_rows:
            sql_text = str(raw.get("representative_sql") or "").strip()
            if not sql_text:
                continue
            sql_group_key = _hash_id(_normalize_sql_text(sql_text))[:16]
            row = {
                "object_id": f"{entry['source_db_key']}:{sql_group_key}",
                "object_type": "sql",
                "system_key": system_key,
                "batch_key": batch_key,
                "source_db_key": entry["source_db_key"],
                "source_db_name": entry["source_db_name"],
                "source_file": entry["source_file"],
                "source_summary_file": entry["source_summary_file"],
                "source_case_key": entry["source_case_key"],
                "source_export_key": entry["source_export_key"],
                "source_component_key": entry["source_component_key"],
                "source_component_name": entry["source_component_name"],
                "source_component_subtype": entry["source_component_subtype"],
                "source_row_rank_in_db": "0",
                "source_total_rows_in_db": "0",
                "sql_group_key": sql_group_key,
                "representative_sql": sql_text,
                "query_object_hint": _query_object_hint(sql_text),
                "avg_rt_ms": _stringify_number(raw.get("avg_rt_ms")),
                "total_time_ms": _stringify_number(raw.get("total_time_ms")),
                "qps": _stringify_number(raw.get("qps")),
                "exec_count": _stringify_number(raw.get("exec_count")),
                "error_count": _stringify_number(raw.get("error_count")),
                "slow_count": _stringify_number(raw.get("slow_count")),
                "bucket_hits": "",
                "screening_score": "0",
                "screening_reason": "",
                "selected_by_global_rank": "false",
                "selected_by_db_rank": "false",
                "selected_for_master": "false",
                "parse_mode": str(raw.get("parse_mode") or "csv"),
            }
            current = dedup.get(row["object_id"])
            if current is None or _sql_row_rank_key(row) > _sql_row_rank_key(current):
                dedup[row["object_id"]] = row
        db_rows = list(dedup.values())
        db_rows.sort(key=_sql_row_rank_key, reverse=True)
        total = len(db_rows)
        for index, row in enumerate(db_rows, start=1):
            row["source_row_rank_in_db"] = str(index)
            row["source_total_rows_in_db"] = str(total)
        rows.extend(db_rows)

    rows.sort(key=_sql_row_rank_key, reverse=True)
    for index, row in enumerate(rows, start=1):
        buckets: list[str] = []
        avg_rt = _to_float(row.get("avg_rt_ms"))
        total_time = _to_float(row.get("total_time_ms"))
        exec_count = _to_float(row.get("exec_count"))
        if avg_rt is not None and avg_rt >= rules["high_avg_rt_ms"]:
            buckets.append("high_avg_rt")
        if total_time is not None and total_time >= rules["high_total_time_ms"]:
            buckets.append("high_total_time")
        if exec_count is not None and exec_count >= rules["high_exec_count"]:
            buckets.append("high_exec_count")
        row["selected_by_global_rank"] = "true" if index <= rules["global_top_n"] else "false"
        if row["selected_by_global_rank"] == "true":
            buckets.append("selected_by_global_rank")
        row["bucket_hits"] = ";".join(buckets)
        row["screening_score"] = str(len(buckets))
        row["screening_reason"] = "; ".join(_reason_text(buckets))

    grouped_by_db = _group_rows_by(rows, "source_db_key")
    for db_rows in grouped_by_db.values():
        db_rows.sort(key=_sql_row_rank_key, reverse=True)
        for index, row in enumerate(db_rows, start=1):
            if index <= rules["per_db_top_n"]:
                row["selected_by_db_rank"] = "true"
                bucket_set = [part for part in row["bucket_hits"].split(";") if part]
                if "selected_by_db_rank" not in bucket_set:
                    bucket_set.append("selected_by_db_rank")
                row["bucket_hits"] = ";".join(bucket_set)
                row["screening_score"] = str(len(bucket_set))
                row["screening_reason"] = "; ".join(_reason_text(bucket_set))
            row["selected_for_master"] = "true" if row["selected_by_global_rank"] == "true" or row["selected_by_db_rank"] == "true" else "false"
    return rows, warnings


def _prepare_nosql_rows(
    entries: list[dict[str, Any]],
    system_key: str,
    batch_key: str,
    rules: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[str]]:
    warnings: list[str] = []
    rows: list[dict[str, Any]] = []
    for entry in entries:
        source_file = Path(entry["source_file"])
        parsed_rows, parse_warning = _load_component_operation_rows(source_file, kind="nosql")
        if parse_warning:
            warnings.append(parse_warning)
        for raw in parsed_rows:
            command = str(raw.get("representative_sql") or raw.get("representative_command") or "").strip()
            if not command:
                continue
            avg_rt = _to_float(raw.get("avg_rt_ms"))
            total_time = _to_float(raw.get("total_time_ms"))
            exec_count = _to_float(raw.get("exec_count"))
            buckets: list[str] = []
            if avg_rt is not None and avg_rt >= rules["high_avg_rt_ms"]:
                buckets.append("high_avg_rt")
            if total_time is not None and total_time >= rules["high_total_time_ms"]:
                buckets.append("high_total_time")
            if exec_count is not None and exec_count >= rules["high_exec_count"]:
                buckets.append("high_exec_count")
            rows.append(
                {
                    "object_id": _hash_id(f"nosql:{entry['source_component_key']}:{command}"),
                    "object_type": "nosql",
                    "system_key": system_key,
                    "batch_key": batch_key,
                    "source_component_key": entry["source_component_key"],
                    "source_component_name": entry["source_component_name"],
                    "source_component_subtype": entry["source_component_subtype"],
                    "source_file": entry["source_file"],
                    "source_summary_file": entry["source_summary_file"],
                    "source_case_key": entry["source_case_key"],
                    "source_export_key": entry["source_export_key"],
                    "command_name": command[:80],
                    "representative_command": command,
                    "avg_rt_ms": _stringify_number(avg_rt),
                    "total_time_ms": _stringify_number(total_time),
                    "qps": _stringify_number(raw.get("qps")),
                    "exec_count": _stringify_number(exec_count),
                    "error_count": _stringify_number(raw.get("error_count")),
                    "slow_count": _stringify_number(raw.get("slow_count")),
                    "bucket_hits": ";".join(buckets),
                    "screening_score": str(len(buckets)),
                    "screening_reason": "; ".join(_reason_text(buckets)),
                    "selected_for_master": "false",
                    "parse_mode": str(raw.get("parse_mode") or "csv"),
                }
            )
    _mark_top_n(rows, rules["top_n"])
    return rows, warnings


def _load_component_operation_rows(path: Path, *, kind: str) -> tuple[list[dict[str, Any]], str | None]:
    if path.suffix.lower() == ".csv":
        return _load_component_operation_csv(path, kind=kind), None
    if path.suffix.lower() == ".xls":
        xlrd_warning: str | None = None
        try:
            parsed = parse_component_operation_xls(path, kind=kind)
        except Exception as exc:
            parsed = None
            xlrd_warning = f"{path.name} xlrd parsing failed: {exc}"
        else:
            if parsed.warnings:
                xlrd_warning = "; ".join(parsed.warnings)
        if parsed and parsed.rows:
            return parsed.rows, xlrd_warning
        fallback_rows, fallback_warning = _load_component_operation_xls_strings(path, kind=kind)
        combined = "; ".join(part for part in [xlrd_warning, fallback_warning] if part)
        return fallback_rows, combined
    return [], f"Unsupported component operation file format: {path}"


def _load_component_operation_csv(path: Path, *, kind: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for raw in _read_csv_rows(path):
        sql_text = str(raw.get("SQL文本") or raw.get("SQL") or raw.get("sql") or raw.get("命令") or "").strip()
        if not sql_text:
            continue
        rows.append(
            {
                "representative_sql": sql_text,
                "avg_rt_ms": _to_float(raw.get("平均响应时间(ms)") or raw.get("平均响应时间")),
                "total_time_ms": _to_float(raw.get("总耗时(ms)") or raw.get("响应总时间")),
                "qps": _to_float(raw.get("吞吐率(tps)") or raw.get("吞吐率")),
                "exec_count": _to_float(raw.get("执行次数") or raw.get("请求数")),
                "error_count": _to_float(raw.get("错误次数") or raw.get("错误数")),
                "slow_count": _to_float(raw.get("慢次数")),
                "parse_mode": "csv",
            }
        )
    return rows


def _load_component_operation_xls_strings(path: Path, *, kind: str) -> tuple[list[dict[str, Any]], str | None]:
    try:
        proc = subprocess.run(
            ["strings", "-n", "6", str(path)],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        return [], f"Unable to inspect {path.name}: {exc}"

    if proc.returncode != 0:
        return [], f"strings fallback failed for {path.name}"

    rows: list[dict[str, Any]] = []
    pending_metric: float | None = None
    seen: set[str] = set()
    for line in proc.stdout.splitlines():
        text = line.strip()
        if not text:
            continue
        if _looks_like_number(text):
            pending_metric = _to_float(text)
            continue
        if not _looks_like_sql(text, kind=kind):
            continue
        normalized = _normalize_sql_text(text)
        if normalized in seen:
            continue
        seen.add(normalized)
        rows.append(
            {
                "representative_sql": text,
                "avg_rt_ms": pending_metric,
                "total_time_ms": None,
                "qps": None,
                "exec_count": None,
                "error_count": None,
                "slow_count": None,
                "parse_mode": "strings_fallback",
            }
        )
        pending_metric = None
    warning = (
        f"{path.name} was parsed with strings fallback; avg_rt_ms may be partial and total_time/exec_count fields are not yet materialized."
        if rows
        else f"{path.name} could not be parsed into prepared rows with the current strings fallback."
    )
    return rows, warning


def _materialize_master(prepared_path: Path, columns: list[str], *, object_type: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not prepared_path.exists():
        return rows
    for raw in _read_csv_rows(prepared_path):
        if not _is_true(raw.get("selected_for_master")):
            continue
        row = {column: str(raw.get(column, "") or "") for column in columns}
        if "object_type" in row and not row["object_type"]:
            row["object_type"] = object_type
        if "selected_for_deep_dive" in row and not row["selected_for_deep_dive"]:
            row["selected_for_deep_dive"] = "true" if _default_selected_for_deep_dive(row) else "false"
        if "followup_status" in row and not row["followup_status"]:
            row["followup_status"] = "待确认"
        if "deep_dive_count" in row and not row["deep_dive_count"]:
            row["deep_dive_count"] = "0"
        if "deep_dive_status" in row and not row["deep_dive_status"]:
            row["deep_dive_status"] = "not_started" if _is_true(row.get("selected_for_deep_dive")) else "not_selected"
        if "latest_deep_dive_id" in row and not row["latest_deep_dive_id"]:
            row["latest_deep_dive_id"] = ""
        if "latest_deep_dive_at" in row and not row["latest_deep_dive_at"]:
            row["latest_deep_dive_at"] = ""
        if "evidence_status" in row and not row["evidence_status"]:
            row["evidence_status"] = "待补证据"
        if "related_sql_count" in row and not row["related_sql_count"]:
            row["related_sql_count"] = "0"
        if "related_object_ids" in row and not row["related_object_ids"] and row.get("related_request_ids"):
            row["related_object_ids"] = row["related_request_ids"]
        rows.append(row)
    return rows


def _load_deep_dive_source_payload(path: Path) -> dict[str, Any]:
    loaded = _load_json(path)
    if isinstance(loaded.get("payload"), dict) and (
        "deep_dive_targets" in loaded.get("payload", {}) or "selected_target_expansions" in loaded.get("payload", {})
    ):
        return dict(loaded["payload"])
    if "deep_dive_targets" in loaded or "selected_target_expansions" in loaded:
        return dict(loaded)
    raise RuntimeError(f"{path} does not contain deep_dive_targets / selected_target_expansions")


def _group_expansions_by_candidate_key(expansions: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in expansions:
        grouped[str(item.get("candidate_key") or "")].append(item)
    return grouped


def _coerce_deep_dive_seed(target: dict[str, Any]) -> dict[str, Any]:
    if all(key in target for key in ("object_type", "source_master_table", "deep_dive_kind")):
        seed = {
            "object_type": target.get("object_type"),
            "source_master_table": target.get("source_master_table"),
            "deep_dive_kind": target.get("deep_dive_kind"),
            "deep_dive_scope": target.get("deep_dive_scope") or target.get("impact_scope") or "local",
            "pack_source": target.get("pack_source") or ";".join(target.get("source_packs") or []),
            "master_match_hints": target.get("master_match_hints") or {},
            "suspected_cluster_key": target.get("suspected_cluster_key") or "",
            "related_object_ids": target.get("related_object_ids") or [],
            "report_group_hint": target.get("report_group_hint") or "",
        }
        if isinstance(seed["related_object_ids"], str):
            seed["related_object_ids"] = _split_semicolon_list(str(seed["related_object_ids"]))
        return seed
    if _adapter_build_deep_dive_seed is not None:
        return dict(_adapter_build_deep_dive_seed(target))
    return _fallback_deep_dive_seed(target)


def _fallback_deep_dive_seed(target: dict[str, Any]) -> dict[str, Any]:
    candidate_type = str(target.get("candidate_type") or "")
    target_ref = target.get("target_ref") or {}
    object_type = "request"
    source_master_table = "request_master.csv"
    deep_dive_kind = "request_context"
    if candidate_type == "sql" or str(target_ref.get("kind") or "") == "sql":
        object_type = "sql"
        source_master_table = "sql_master.csv"
        deep_dive_kind = "sql_bottleneck"
    elif candidate_type == "interface_cluster":
        object_type = "interface_cluster"
        source_master_table = "interface_cluster_master.csv"
        deep_dive_kind = "interface_cluster_context"
    elif candidate_type == "trace":
        deep_dive_kind = "trace_primary"
    match_hints: dict[str, Any] = {
        "candidate_key": target.get("candidate_key"),
        "display_name": target.get("display_name"),
        "target_ref": target_ref,
    }
    if object_type == "sql":
        match_hints["sql_text"] = target_ref.get("op_name") or target.get("display_name")
        match_hints["component_name"] = target_ref.get("component_name")
    else:
        match_hints["action_name"] = target_ref.get("action_name") or target.get("display_name")
    return {
        "object_type": object_type,
        "source_master_table": source_master_table,
        "deep_dive_kind": deep_dive_kind,
        "deep_dive_scope": target.get("deep_dive_scope") or target.get("impact_scope") or "local",
        "pack_source": target.get("pack_source") or ";".join(target.get("source_packs") or target.get("recommended_next_packs") or []),
        "master_match_hints": match_hints,
        "suspected_cluster_key": f"{object_type}:{_hash_id(str(target.get('candidate_key') or target.get('display_name') or 'unknown'))[:10]}",
        "related_object_ids": [],
        "report_group_hint": f"{object_type}:{target.get('impact_scope') or 'local'}:{target.get('evidence_strength') or 'weak'}",
    }


def _match_seed_to_master_object(
    diagnostics_root: Path,
    seed: dict[str, Any],
    expansions: list[dict[str, Any]],
) -> dict[str, str] | None:
    object_type = str(seed.get("object_type") or "")
    filename = MASTER_FILE_BY_OBJECT_TYPE.get(object_type, "")
    if not filename:
        return None
    master_path = diagnostics_root / "02_master_tables" / filename
    if not master_path.exists():
        return None
    rows = _read_csv_rows(master_path)
    if object_type == "request":
        return _match_request_master_row(rows, seed, expansions, filename)
    if object_type == "sql":
        return _match_sql_master_row(rows, seed, expansions, filename)
    if object_type == "interface_cluster":
        return _match_interface_master_row(rows, seed, expansions, filename)
    return None


def _match_request_master_row(
    rows: list[dict[str, str]],
    seed: dict[str, Any],
    expansions: list[dict[str, Any]],
    source_master_table: str,
) -> dict[str, str] | None:
    names: list[str] = []
    hints = seed.get("master_match_hints") or {}
    names.extend(
        [
            str(hints.get("action_name") or ""),
            str(hints.get("display_name") or ""),
            str(((hints.get("target_ref") or {}).get("action_name")) or ""),
        ]
    )
    for expansion in expansions:
        payload = expansion.get("payload") or {}
        detail = payload.get("detail_summary") or {}
        trace = payload.get("trace") or {}
        names.extend(
            [
                str(detail.get("actionName") or ""),
                str(trace.get("actionName") or ""),
                str((payload.get("action") or {}).get("name") or ""),
            ]
        )
    normalized_names = [item for item in (_normalize_request_name(name) for name in names) if item]
    if not normalized_names:
        return None
    for row in rows:
        row_candidates = {
            _normalize_request_name(str(row.get("canonical_name") or "")),
            _normalize_request_name(str(row.get("display_name") or "")),
            _normalize_request_name(str(row.get("alias_name") or "")),
        }
        row_candidates.discard("")
        if any(name in row_candidates for name in normalized_names):
            return {"object_id": str(row.get("object_id") or ""), "source_master_table": source_master_table}
        if any(any(name in candidate or candidate in name for candidate in row_candidates) for name in normalized_names):
            return {"object_id": str(row.get("object_id") or ""), "source_master_table": source_master_table}
    return None


def _match_sql_master_row(
    rows: list[dict[str, str]],
    seed: dict[str, Any],
    expansions: list[dict[str, Any]],
    source_master_table: str,
) -> dict[str, str] | None:
    sql_texts: list[str] = []
    hints = seed.get("master_match_hints") or {}
    target_ref = hints.get("target_ref") or {}
    sql_texts.extend(
        [
            str(hints.get("sql_text") or ""),
            str(hints.get("display_name") or ""),
            str(target_ref.get("op_name") or ""),
        ]
    )
    for expansion in expansions:
        payload = expansion.get("payload") or {}
        selector = payload.get("selector") or {}
        sql_payload = payload.get("sql") or {}
        sql_texts.extend(
            [
                str(selector.get("opName") or ""),
                str(sql_payload.get("op_name_decoded") or ""),
                str(sql_payload.get("opName") or ""),
            ]
        )
    normalized_texts = [item for item in (_normalize_sql_text(text) for text in sql_texts) if item and not item.startswith("sql:")]
    if not normalized_texts:
        return None
    for row in rows:
        row_text = _normalize_sql_text(str(row.get("representative_sql") or ""))
        if not row_text:
            continue
        if any(text == row_text or text in row_text or row_text in text for text in normalized_texts):
            return {"object_id": str(row.get("object_id") or ""), "source_master_table": source_master_table}
    return None


def _match_interface_master_row(
    rows: list[dict[str, str]],
    seed: dict[str, Any],
    expansions: list[dict[str, Any]],
    source_master_table: str,
) -> dict[str, str] | None:
    hints = seed.get("master_match_hints") or {}
    names = [str(hints.get("display_name") or ""), str(hints.get("cluster_name") or "")]
    for expansion in expansions:
        payload = expansion.get("payload") or {}
        names.append(str((payload.get("selector") or {}).get("clusterName") or ""))
    normalized_names = [item for item in (_normalize_request_name(name) for name in names) if item]
    for row in rows:
        row_candidates = {
            _normalize_request_name(str(row.get("cluster_name") or "")),
            _normalize_request_name(str(row.get("application_name") or "")),
        }
        row_candidates.discard("")
        if any(name in row_candidates for name in normalized_names):
            return {"object_id": str(row.get("object_id") or ""), "source_master_table": source_master_table}
    return None


def _build_bundle_input(
    target: dict[str, Any],
    seed: dict[str, Any],
    expansions: list[dict[str, Any]],
) -> dict[str, Any]:
    page_links: list[dict[str, Any]] = []
    screenshot_hints: list[dict[str, Any]] = []
    evidence_rows: list[dict[str, Any]] = []
    related_object_ids = list(seed.get("related_object_ids") or [])
    pack_sources: list[str] = [part for part in str(seed.get("pack_source") or "").split(";") if part]

    for expansion in expansions:
        pack_type = str(expansion.get("pack_type") or "")
        if pack_type:
            pack_sources.append(pack_type)
        payload = expansion.get("payload") or {}
        page_links.extend(payload.get("page_links") or [])
        screenshot_hints.extend(payload.get("screenshot_hints") or [])
        evidence_rows.extend(_bundle_evidence_rows_for_expansion(expansion))
        related_object_ids.extend(_related_object_hints_from_payload(payload))

    page_links = _dedupe_json_items(page_links)
    screenshot_hints = _dedupe_json_items(screenshot_hints)
    evidence_rows = _dedupe_evidence_rows(evidence_rows)
    related_object_ids = _unique_strings(related_object_ids)
    return {
        "status": "materialized" if expansions else "seeded",
        "summary": str(target.get("selection_reason") or target.get("display_name") or ""),
        "pack_source": ";".join(_unique_strings(pack_sources)),
        "page_links": page_links,
        "screenshot_hints": screenshot_hints,
        "evidence_rows": evidence_rows,
        "related_object_ids": related_object_ids,
        "screenshot_hint_count": len(screenshot_hints),
        "page_link_count": len(page_links),
        "evidence_count": len(evidence_rows),
        "trace_link_count": len([row for row in evidence_rows if row.get("evidence_type") in {"trace", "trace_link"}]),
    }


def _write_bundle_contents(bundle_dir: Path, *, bundle_input: dict[str, Any]) -> None:
    _write_json(bundle_dir / "page_links.json", {"page_links": bundle_input["page_links"]})
    _write_json(bundle_dir / "related_objects.json", {"related_object_ids": bundle_input["related_object_ids"]})
    _write_csv(bundle_dir / "evidence_index.csv", DEEP_DIVE_BUNDLE_FILE_COLUMNS["evidence_index.csv"], bundle_input["evidence_rows"])
    _write_csv(
        bundle_dir / "screenshot_hints.csv",
        DEEP_DIVE_BUNDLE_FILE_COLUMNS["screenshot_hints.csv"],
        [_normalize_screenshot_hint_row(item) for item in bundle_input["screenshot_hints"]],
    )
    summary_payload = _load_json(bundle_dir / "summary.json")
    summary_payload.update(
        {
            "status": bundle_input["status"],
            "summary": bundle_input["summary"],
            "evidence_count": bundle_input["evidence_count"],
            "page_link_count": bundle_input["page_link_count"],
            "screenshot_hint_count": bundle_input["screenshot_hint_count"],
            "trace_link_count": bundle_input["trace_link_count"],
            "related_object_ids": bundle_input["related_object_ids"],
            "pack_source": bundle_input["pack_source"],
        }
    )
    _write_json(bundle_dir / "summary.json", summary_payload)
    (bundle_dir / "notes.md").write_text(
        "# Notes\n\n"
        f"- status: `{bundle_input['status']}`\n"
        f"- page_link_count: `{bundle_input['page_link_count']}`\n"
        f"- trace_link_count: `{bundle_input['trace_link_count']}`\n"
        f"- screenshot_hint_count: `{bundle_input['screenshot_hint_count']}`\n",
        encoding="utf-8",
    )
    _update_registry_row_from_bundle(bundle_dir, summary_payload)


def _bundle_evidence_rows_for_expansion(expansion: dict[str, Any]) -> list[dict[str, Any]]:
    pack_type = str(expansion.get("pack_type") or "")
    payload = expansion.get("payload") or {}
    evidence = list(expansion.get("evidence") or []) + list(payload.get("evidence") or [])
    rows: list[dict[str, Any]] = []
    for index, item in enumerate(evidence, start=1):
        source_ref = str(item.get("source_path") or item.get("source_api") or item.get("id") or "")
        summary = str(item.get("summary") or item.get("source_api") or item.get("id") or f"evidence-{index}")
        rows.append(
            {
                "evidence_id": str(item.get("id") or f"{pack_type or 'pack'}-{index}"),
                "evidence_type": str(item.get("type") or item.get("source_api") or "evidence"),
                "source_pack": pack_type,
                "source_ref": source_ref,
                "summary": summary,
                "status": "available",
            }
        )
    for trace in ((payload.get("evidence_linkage") or {}).get("related_traces") or []):
        trace_ref = str(trace.get("trace_id_numeric") or trace.get("traceGuid") or trace.get("requestId") or "")
        rows.append(
            {
                "evidence_id": f"trace-link-{trace_ref or _hash_id(json.dumps(trace, ensure_ascii=False, sort_keys=True))[:8]}",
                "evidence_type": "trace_link",
                "source_pack": pack_type,
                "source_ref": trace_ref,
                "summary": str(trace.get("actionName") or trace_ref or "related trace"),
                "status": "available",
            }
        )
    return rows


def _related_object_hints_from_payload(payload: dict[str, Any]) -> list[str]:
    hints: list[str] = []
    evidence_linkage = payload.get("evidence_linkage") or {}
    for action in evidence_linkage.get("related_actions") or []:
        action_id = action.get("actionId") or action.get("action_id")
        action_name = action.get("actionName") or action.get("action_name")
        if action_id or action_name:
            hints.append(f"request_hint:{action_id or action_name}")
    for sql in evidence_linkage.get("related_sqls") or []:
        op_name = sql.get("opName") or sql.get("op_name_decoded") or sql.get("sql_text")
        if op_name:
            hints.append(f"sql_hint:{_hash_id(_normalize_sql_text(str(op_name)))[:12]}")
    for dep in evidence_linkage.get("related_dependencies") or []:
        if dep:
            hints.append(f"dependency_hint:{dep}")
    return hints


def _normalize_screenshot_hint_row(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "screenshot_purpose": str(item.get("purpose") or item.get("screenshot_purpose") or item.get("summary") or ""),
        "page_url": str(item.get("url") or item.get("page_url") or item.get("direct_url") or ""),
        "suggested_area": str(item.get("suggested_area") or item.get("capture_area") or item.get("suggested_capture") or ""),
        "subject": str(item.get("subject") or item.get("object_name") or item.get("display_name") or ""),
        "usage_note": str(item.get("usage_note") or item.get("why_relevant") or item.get("note") or ""),
    }


def _find_existing_deep_dive_row(
    registry_rows: list[dict[str, str]],
    *,
    object_id: str,
    deep_dive_kind: str,
    pack_source: str,
    summary: str,
) -> dict[str, str] | None:
    for row in registry_rows:
        if (
            str(row.get("object_id") or "") == object_id
            and str(row.get("deep_dive_kind") or "") == deep_dive_kind
            and str(row.get("pack_source") or "") == pack_source
            and str(row.get("summary") or "") == summary
        ):
            return row
    return None


def _new_deep_dive_id(target: dict[str, Any], object_id: str) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    seed = f"{target.get('candidate_key') or target.get('display_name') or object_id}:{timestamp}"
    return f"dd_{timestamp}_{_hash_id(seed)[:8]}"


def _update_registry_row_from_bundle(bundle_dir: Path, summary_payload: dict[str, Any]) -> None:
    diagnostics_root = bundle_dir.parents[3]
    registry_path = diagnostics_root / "04_deep_dive" / "deep_dive_registry.csv"
    registry_rows = _read_csv_rows(registry_path)
    updated_rows: list[dict[str, str]] = []
    for row in registry_rows:
        if str(row.get("deep_dive_id") or "") != str(summary_payload.get("deep_dive_id") or ""):
            updated_rows.append(row)
            continue
        merged = dict(row)
        merged["status"] = str(summary_payload.get("status") or row.get("status") or "")
        merged["summary"] = str(summary_payload.get("summary") or row.get("summary") or "")
        merged["evidence_count"] = str(summary_payload.get("evidence_count") or "0")
        merged["page_link_count"] = str(summary_payload.get("page_link_count") or "0")
        merged["screenshot_hint_count"] = str(summary_payload.get("screenshot_hint_count") or "0")
        merged["bundle_path"] = str(bundle_dir)
        merged["related_object_ids"] = ";".join(summary_payload.get("related_object_ids") or [])
        merged["report_group_hint"] = str(summary_payload.get("report_group_hint") or row.get("report_group_hint") or "")
        updated_rows.append(merged)
    _write_csv(registry_path, DEEP_DIVE_REGISTRY_COLUMNS, updated_rows)


def _apply_deep_dive_evidence_state(
    row: dict[str, str],
    object_type: str,
    registry_rows: list[dict[str, str]],
) -> dict[str, str]:
    updated = dict(row)
    latest_entry = registry_rows[0] if registry_rows else {}
    page_link_count = 0
    trace_link_count = 0
    screenshot_hint_count = 0
    for entry in registry_rows:
        page_link_count += _safe_int(entry.get("page_link_count"))
        screenshot_hint_count += _safe_int(entry.get("screenshot_hint_count"))
        bundle_path = Path(str(entry.get("bundle_path") or ""))
        if bundle_path.exists():
            evidence_index_path = bundle_path / "evidence_index.csv"
            if evidence_index_path.exists():
                trace_link_count += len(
                    [
                        item
                        for item in _read_csv_rows(evidence_index_path)
                        if str(item.get("evidence_type") or "") in {"trace", "trace_link"}
                    ]
                )
    updated["latest_deep_dive_id"] = str(latest_entry.get("deep_dive_id") or "")
    updated["deep_dive_status"] = _rollup_deep_dive_status(
        [str(item.get("status") or "") for item in registry_rows],
        selected=bool(registry_rows),
    )
    updated["page_link_count"] = str(page_link_count) if page_link_count else ""
    updated["trace_link_count"] = str(trace_link_count) if trace_link_count else ""
    updated["screenshot_hint_status"] = "已生成" if screenshot_hint_count > 0 else "待补充"
    if registry_rows:
        updated["evidence_status"] = "已挂接deep-dive"
    if object_type == "sql" and not updated.get("related_request_ids") and latest_entry.get("related_object_ids"):
        related_ids = [item.replace("request_hint:", "") for item in _split_semicolon_list(str(latest_entry.get("related_object_ids") or "")) if item.startswith("request_hint:")]
        updated["related_request_ids"] = ";".join(related_ids)
    return updated


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, columns: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in columns})


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _merge_rules(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = json.loads(json.dumps(base))
    for section, values in override.items():
        if isinstance(values, dict) and isinstance(merged.get(section), dict):
            merged[section].update(values)
        else:
            merged[section] = values
    return merged


def _find_summary_for_file(path: Path, family: str) -> Path | None:
    direct = path.with_name(SUMMARY_PATTERNS.get(family, ""))
    if direct.exists():
        return direct
    for candidate in path.parent.glob("*__summary.json"):
        return candidate
    return None


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _group_registry(entries: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for entry in entries:
        grouped[str(entry.get("object_family") or "")].append(entry)
    return grouped


def _group_rows_by(rows: list[dict[str, Any]], key: str) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row.get(key) or "")].append(row)
    return grouped


def _has_discoverable_exports(path: Path) -> bool:
    if not path.exists():
        return False
    for child in path.rglob("*"):
        if child.is_file() and child.name != "export_registry.json":
            return True
    return False


def _mark_top_n(rows: list[dict[str, Any]], top_n: int) -> None:
    ranked = sorted(rows, key=lambda item: (_to_float(item.get("screening_score")) or 0, _to_float(item.get("avg_rt_ms")) or 0, _to_float(item.get("total_time_ms")) or 0), reverse=True)
    selected_ids = {row["object_id"] for row in ranked[:top_n] if (_to_float(row.get("screening_score")) or 0) > 0}
    for row in rows:
        if row["object_id"] in selected_ids:
            row["selected_for_master"] = "true"


def _reason_text(buckets: list[str]) -> list[str]:
    mapping = {
        "low_apdex": "Apdex 低于阈值",
        "low_score": "评分低于阈值",
        "high_error_rate": "错误率命中筛选阈值",
        "high_slow_count": "慢次数命中筛选阈值",
        "high_avg_rt": "平均响应时间命中筛选阈值",
        "high_total_time": "总耗时命中筛选阈值",
        "high_exec_count": "执行次数命中筛选阈值",
        "high_error_count": "错误数命中筛选阈值",
        "low_freq_outlier": "低频但明显离群",
        "selected_by_global_rank": "进入全局 SQL 候选排名",
        "selected_by_db_rank": "进入分库保底候选排名",
    }
    return [mapping.get(bucket, bucket) for bucket in buckets]


def _to_float(value: Any) -> float | None:
    if value in {None, ""}:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(",", "")
    if not text:
        return None
    if text.startswith("<"):
        text = text.replace("<", "").strip()
    try:
        return float(text)
    except ValueError:
        return None


def _safe_int(value: Any) -> int:
    number = _to_float(value)
    if number is None:
        return 0
    return int(number)


def _stringify_number(value: Any) -> str:
    number = _to_float(value)
    if number is None:
        return ""
    if number.is_integer():
        return str(int(number))
    return f"{number:.6f}".rstrip("0").rstrip(".")


def _is_true(value: Any) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y"}


def _default_selected_for_deep_dive(row: dict[str, Any]) -> bool:
    if not _is_true(row.get("selected_for_master")):
        return False
    followup_status = str(row.get("followup_status") or "").strip()
    evidence_status = str(row.get("evidence_status") or "").strip()
    if followup_status in {"继续深挖", "待确认", "保留观察"}:
        return True
    if evidence_status in {"待补证据", "待补充"}:
        return True
    screening_score = _to_float(row.get("screening_score")) or 0
    return screening_score > 0


def _hash_id(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:20]


def _normalize_sql_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip()).lower()


def _normalize_request_name(text: str) -> str:
    value = str(text or "").strip().lower()
    value = re.sub(r"^uri/", "", value)
    return re.sub(r"\s+", " ", value)


def _query_object_hint(sql_text: str) -> str:
    match = re.search(r"\bfrom\s+([a-zA-Z0-9_.$`]+)", sql_text, re.IGNORECASE)
    if match:
        return match.group(1).strip("`")
    match = re.search(r"\bupdate\s+([a-zA-Z0-9_.$`]+)", sql_text, re.IGNORECASE)
    if match:
        return match.group(1).strip("`")
    return ""


def _sql_row_rank_key(row: dict[str, Any]) -> tuple[float, float, float, float]:
    return (
        _to_float(row.get("total_time_ms")) or 0,
        _to_float(row.get("avg_rt_ms")) or 0,
        _to_float(row.get("slow_count")) or 0,
        _to_float(row.get("exec_count")) or 0,
    )


def _looks_like_sql(text: str, *, kind: str) -> bool:
    upper = text.upper()
    starters = ("SELECT ", "UPDATE ", "INSERT ", "DELETE ", "WITH ")
    if upper.startswith(starters):
        return True
    if kind == "nosql":
        return "(" not in text and len(text.split()) <= 6 and len(text) <= 120
    return False


def _looks_like_number(text: str) -> bool:
    return bool(re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", text.strip()))


def _sha1_file(path: Path) -> str:
    digest = hashlib.sha1()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _guess_mime_type(path: Path) -> str:
    if path.suffix.lower() == ".csv":
        return "text/csv"
    if path.suffix.lower() == ".xls":
        return "application/vnd.ms-excel"
    return "application/octet-stream"


def _bundle_object_dir(object_type: str) -> str:
    return object_type if object_type in DEEP_DIVE_BUNDLE_TYPES else "shared"


def _sanitize_path_segment(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return "unknown"
    return re.sub(r"[^a-zA-Z0-9._-]+", "_", text)


def _split_semicolon_list(value: str) -> list[str]:
    return [item for item in (part.strip() for part in str(value or "").split(";")) if item]


def _index_deep_dive_registry(rows: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    indexed: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        indexed[str(row.get("object_id") or "")].append(row)
    for items in indexed.values():
        items.sort(key=lambda row: str(row.get("generated_at") or ""), reverse=True)
    return indexed


def _apply_deep_dive_registry_state(row: dict[str, str], object_type: str, registry_rows: list[dict[str, str]]) -> dict[str, str]:
    updated = dict(row)
    updated["object_type"] = updated.get("object_type") or object_type
    related_from_row = _split_semicolon_list(updated.get("related_object_ids", ""))
    if not related_from_row and updated.get("related_request_ids"):
        related_from_row = _split_semicolon_list(updated.get("related_request_ids", ""))

    related_from_registry: list[str] = []
    statuses: list[str] = []
    latest_id = ""
    latest_at = ""
    report_group_hint = updated.get("report_group_hint", "")
    for entry in registry_rows:
        statuses.append(str(entry.get("status") or ""))
        generated_at = str(entry.get("generated_at") or "")
        if not latest_at or generated_at > latest_at:
            latest_at = generated_at
            latest_id = str(entry.get("deep_dive_id") or "")
        related_from_registry.extend(_split_semicolon_list(str(entry.get("related_object_ids") or "")))
        if not report_group_hint:
            report_group_hint = str(entry.get("report_group_hint") or "")

    updated["selected_for_deep_dive"] = "true" if registry_rows or _default_selected_for_deep_dive(updated) else "false"
    updated["deep_dive_count"] = str(len(registry_rows))
    updated["latest_deep_dive_id"] = latest_id
    updated["latest_deep_dive_at"] = latest_at
    updated["deep_dive_status"] = _rollup_deep_dive_status(statuses, selected=_is_true(updated.get("selected_for_deep_dive")))
    updated["evidence_status"] = "已挂接deep-dive" if registry_rows else (updated.get("evidence_status") or "待补证据")
    updated["related_object_ids"] = ";".join(_unique_strings(related_from_row + related_from_registry))
    updated["report_group_hint"] = report_group_hint
    return updated


def _rollup_deep_dive_status(statuses: list[str], *, selected: bool) -> str:
    normalized = {str(item or "").strip() for item in statuses if str(item or "").strip()}
    if "in_progress" in normalized:
        return "in_progress"
    if "materialized" in normalized or "completed" in normalized:
        return "completed"
    if "deferred" in normalized:
        return "deferred"
    if "queued" in normalized or "initialized" in normalized or "planned" in normalized or "seeded" in normalized:
        return "queued"
    return "not_started" if selected else "not_selected"


def _unique_strings(items: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for item in items:
        text = str(item or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def _dedupe_json_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in items:
        key = json.dumps(item, ensure_ascii=False, sort_keys=True)
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def _dedupe_evidence_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for row in rows:
        key = (
            str(row.get("evidence_type") or ""),
            str(row.get("source_pack") or ""),
            str(row.get("source_ref") or ""),
        )
        if key in seen:
            continue
        seen.add(key)
        result.append(row)
    return result
