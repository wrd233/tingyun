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
        "followup_status",
        "followup_note",
        "writing_note",
    ],
    "request_master.csv": [
        "object_id",
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
        "followup_status",
        "followup_note",
        "evidence_status",
        "related_sql_count",
        "related_object_ids",
        "report_group_hint",
        "writing_note",
    ],
    "interface_cluster_master.csv": [
        "object_id",
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
        "followup_status",
        "followup_note",
        "report_group_hint",
        "writing_note",
    ],
    "sql_master.csv": [
        "object_id",
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
        "followup_status",
        "followup_note",
        "evidence_status",
        "related_request_ids",
        "report_group_hint",
        "writing_note",
    ],
    "nosql_master.csv": [
        "object_id",
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
        "followup_status",
        "followup_note",
        "writing_note",
    ],
}

EVIDENCE_INDEX_COLUMNS = {
    "request_evidence_index.csv": [
        "object_id",
        "object_type",
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
        "followup_status",
        "evidence_status",
        "page_link_count",
        "trace_link_count",
        "screenshot_hint_status",
        "related_request_ids",
        "writing_note",
    ],
}

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
    master_root.mkdir(parents=True, exist_ok=True)
    evidence_root.mkdir(parents=True, exist_ok=True)

    outputs: list[str] = []
    row_counts: dict[str, int] = {}

    application_master = _materialize_master(prepared_root / "application_prepared.csv", MASTER_COLUMNS["application_master.csv"])
    _write_csv(master_root / "application_master.csv", MASTER_COLUMNS["application_master.csv"], application_master)
    outputs.append("application_master.csv")
    row_counts["application_master"] = len(application_master)

    request_master = _materialize_master(prepared_root / "request_prepared.csv", MASTER_COLUMNS["request_master.csv"])
    _write_csv(master_root / "request_master.csv", MASTER_COLUMNS["request_master.csv"], request_master)
    outputs.append("request_master.csv")
    row_counts["request_master"] = len(request_master)

    interface_master = _materialize_master(prepared_root / "interface_cluster_prepared.csv", MASTER_COLUMNS["interface_cluster_master.csv"])
    _write_csv(master_root / "interface_cluster_master.csv", MASTER_COLUMNS["interface_cluster_master.csv"], interface_master)
    outputs.append("interface_cluster_master.csv")
    row_counts["interface_cluster_master"] = len(interface_master)

    sql_master = _materialize_master(prepared_root / "sql_prepared_full.csv", MASTER_COLUMNS["sql_master.csv"])
    _write_csv(master_root / "sql_master.csv", MASTER_COLUMNS["sql_master.csv"], sql_master)
    outputs.append("sql_master.csv")
    row_counts["sql_master"] = len(sql_master)

    nosql_master = _materialize_master(prepared_root / "nosql_prepared.csv", MASTER_COLUMNS["nosql_master.csv"])
    _write_csv(master_root / "nosql_master.csv", MASTER_COLUMNS["nosql_master.csv"], nosql_master)
    outputs.append("nosql_master.csv")
    row_counts["nosql_master"] = len(nosql_master)

    request_evidence_rows = [
        {
            "object_id": row["object_id"],
            "object_type": "request",
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

    summary = {
        "system_key": system_key,
        "batch_key": batch_key,
        "diagnostics_dir": str(diagnostics_root),
        "outputs": outputs,
        "row_counts": row_counts,
    }
    _write_json(master_root / "materialization_summary.json", summary)
    return summary


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


def _materialize_master(prepared_path: Path, columns: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not prepared_path.exists():
        return rows
    for raw in _read_csv_rows(prepared_path):
        if not _is_true(raw.get("selected_for_master")):
            continue
        row = {column: str(raw.get(column, "") or "") for column in columns}
        if "followup_status" in row and not row["followup_status"]:
            row["followup_status"] = "待确认"
        if "evidence_status" in row and not row["evidence_status"]:
            row["evidence_status"] = "待补证据"
        if "related_sql_count" in row and not row["related_sql_count"]:
            row["related_sql_count"] = "0"
        rows.append(row)
    return rows


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


def _stringify_number(value: Any) -> str:
    number = _to_float(value)
    if number is None:
        return ""
    if number.is_integer():
        return str(int(number))
    return f"{number:.6f}".rstrip("0").rstrip(".")


def _is_true(value: Any) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y"}


def _hash_id(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:20]


def _normalize_sql_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip()).lower()


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
