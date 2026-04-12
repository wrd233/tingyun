from __future__ import annotations

import argparse
import base64
import json
import re
from pathlib import Path
from typing import Any

from .config import RemoteClientSettings
from .http_client import AdapterRemoteClient

DEFAULT_EXPORT_PARAMS = {
    "dataType": "OP",
    "pageSize": 10000,
    "pageNumber": 1,
    "limit": True,
    "sortField": "respTime",
    "sortDirection": "DESC",
}


def export_component_analysis_raw(
    client: AdapterRemoteClient,
    *,
    diagnostics_dir: str | Path,
    biz_system_id: int,
    end_time: str,
    period_minutes: int,
    source_mode: str,
    include_sql: bool = True,
    include_nosql: bool = True,
    database_components: list[dict[str, Any]] | None = None,
    nosql_components: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    diagnostics_root = Path(diagnostics_dir).expanduser().resolve()
    raw_root = diagnostics_root / "00_raw_exports"
    raw_root.mkdir(parents=True, exist_ok=True)

    results = {
        "diagnostics_dir": str(diagnostics_root),
        "sql_exports": [],
        "nosql_exports": [],
        "warnings": [],
    }

    if include_sql:
        sql_specs = list(database_components or [])
        if not sql_specs:
            try:
                discovered = _discover_primary_component(
                    client,
                    pack_type="database_component_pack",
                    biz_system_id=biz_system_id,
                    end_time=end_time,
                    period_minutes=period_minutes,
                    source_mode=source_mode,
                    component_type="Database",
                )
            except Exception as exc:
                discovered = None
                results["warnings"].append(f"Database component discovery failed: {exc}")
            if discovered:
                sql_specs.append(discovered)
            else:
                results["warnings"].append("No database component was discovered for SQL export.")
        for spec in sql_specs:
            try:
                results["sql_exports"].append(
                    _materialize_component_export(
                        client,
                        raw_root=raw_root,
                        biz_system_id=biz_system_id,
                        end_time=end_time,
                        period_minutes=period_minutes,
                        source_mode=source_mode,
                        component_spec=spec,
                    )
                )
            except Exception as exc:
                results["warnings"].append(f"SQL export failed for {spec.get('component_name')}: {exc}")

    if include_nosql:
        nosql_specs = list(nosql_components or [])
        if not nosql_specs:
            try:
                discovered = _discover_primary_component(
                    client,
                    pack_type="nosql_component_pack",
                    biz_system_id=biz_system_id,
                    end_time=end_time,
                    period_minutes=period_minutes,
                    source_mode=source_mode,
                    component_type="NoSQL",
                )
            except Exception as exc:
                discovered = None
                results["warnings"].append(f"NoSQL component discovery failed: {exc}")
            if discovered:
                nosql_specs.append(discovered)
            else:
                results["warnings"].append("No NoSQL component was discovered for NoSQL export.")
        for spec in nosql_specs:
            try:
                results["nosql_exports"].append(
                    _materialize_component_export(
                        client,
                        raw_root=raw_root,
                        biz_system_id=biz_system_id,
                        end_time=end_time,
                        period_minutes=period_minutes,
                        source_mode=source_mode,
                        component_spec=spec,
                    )
                )
            except Exception as exc:
                results["warnings"].append(f"NoSQL export failed for {spec.get('component_name')}: {exc}")

    summary = {
        "biz_system_id": biz_system_id,
        "end_time": end_time,
        "period_minutes": period_minutes,
        "source_mode": source_mode,
        "sql_export_count": len(results["sql_exports"]),
        "nosql_export_count": len(results["nosql_exports"]),
        "warnings": results["warnings"],
    }
    (raw_root / "component_analysis_exports_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    results["summary_file"] = str(raw_root / "component_analysis_exports_summary.json")
    return results


def _discover_primary_component(
    client: AdapterRemoteClient,
    *,
    pack_type: str,
    biz_system_id: int,
    end_time: str,
    period_minutes: int,
    source_mode: str,
    component_type: str,
) -> dict[str, Any] | None:
    response = client.build_pack(
        pack_type,
        {
            "bizSystemId": biz_system_id,
            "endTime": end_time,
            "periodMinutes": period_minutes,
            "sourceMode": source_mode,
            "limit": 5,
        },
    )
    payload = response.get("payload") or {}
    summary = payload.get("summary") or {}
    component = payload.get("component") or {}
    evidence = payload.get("evidence") or []
    list_evidence = next(
        (
            item
            for item in evidence
            if str(item.get("source_api") or "") in {"Database/list", "NoSQL/list"}
        ),
        {},
    )
    component_row = list_evidence.get("response_excerpt") or {}
    component_name = str(summary.get("component_name") or component.get("component_name") or component_row.get("componentName") or "").strip()
    if not component_name:
        return None
    component_subtype = str(
        summary.get("component_subtype")
        or component.get("component_subtype")
        or component_row.get("componentSubtype")
        or ""
    ).strip()
    component_key = _component_key(component_type, component_name, component_subtype)
    return {
        "component_type": component_type,
        "component_name": component_name,
        "component_subtype": component_subtype,
        "source_component_key": component_key,
        "source_component_name": component_name,
        "source_component_subtype": component_subtype,
        "source_db_key": component_key if component_type == "Database" else "",
        "source_db_name": component_name if component_type == "Database" else "",
        "schemas": component_row.get("schemas") or [],
        "discovery_mode": f"auto:{pack_type}",
        "component_pack_summary": summary,
    }


def _materialize_component_export(
    client: AdapterRemoteClient,
    *,
    raw_root: Path,
    biz_system_id: int,
    end_time: str,
    period_minutes: int,
    source_mode: str,
    component_spec: dict[str, Any],
) -> dict[str, Any]:
    component_type = str(component_spec.get("component_type") or "Database")
    component_name = str(component_spec.get("component_name") or "").strip()
    component_subtype = str(component_spec.get("component_subtype") or "").strip()
    if not component_name:
        raise RuntimeError(f"component_name is required: {component_spec}")

    export_payload = {
        "bizSystemId": biz_system_id,
        "endTime": end_time,
        "periodMinutes": period_minutes,
        "sourceMode": source_mode,
        "limit": 5,
        "exportKind": "component_analysis_export",
        "exportParams": {
            **DEFAULT_EXPORT_PARAMS,
            "componentType": component_type,
            "componentName": component_name,
            "componentSubtype": component_subtype,
        },
        "executeExport": True,
        "includeFileContent": True,
        "maxExportBytes": 20_000_000,
    }
    response = client.build_pack("data_export_pack", export_payload)
    payload = response.get("payload") or {}
    execution = payload.get("execution") or {}
    selected_export = payload.get("selected_export") or {}

    bucket_name = "sql_database" if component_type == "Database" else "nosql"
    component_key = str(component_spec.get("source_component_key") or _component_key(component_type, component_name, component_subtype))
    target_dir = raw_root / bucket_name / component_key
    target_dir.mkdir(parents=True, exist_ok=True)

    canonical_stem = "component_analysis_export_database__SQL_" if component_type == "Database" else "component_analysis_export_nosql__SQL_"
    written_files: list[str] = []

    if execution.get("content_base64"):
        extension = _file_extension(execution.get("suggested_filename"), execution.get("mime_type"))
        export_path = target_dir / f"{canonical_stem}{extension}"
        export_path.write_bytes(base64.b64decode(str(execution["content_base64"])))
        written_files.append(str(export_path))
    elif "response_json" in execution:
        export_path = target_dir / f"{canonical_stem}.json"
        export_path.write_text(json.dumps(execution["response_json"], ensure_ascii=False, indent=2), encoding="utf-8")
        written_files.append(str(export_path))

    summary = {
        "case_key": "component_analysis_export_database" if component_type == "Database" else "component_analysis_export_nosql",
        "biz_system_id": biz_system_id,
        "component_type": component_type,
        "source_component_key": component_key,
        "source_component_name": component_name,
        "source_component_subtype": component_subtype,
        "source_db_key": str(component_spec.get("source_db_key") or ""),
        "source_db_name": str(component_spec.get("source_db_name") or ""),
        "schemas": component_spec.get("schemas") or [],
        "discovery_mode": component_spec.get("discovery_mode"),
        "component_pack_summary": component_spec.get("component_pack_summary") or {},
        "selected_export": selected_export,
        "execution": execution,
        "generated_at": response.get("generated_at"),
        "context": response.get("context") or {},
        "written_files": written_files,
    }
    summary_path = target_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "component_type": component_type,
        "component_name": component_name,
        "component_subtype": component_subtype,
        "target_dir": str(target_dir),
        "written_files": written_files,
        "summary_file": str(summary_path),
        "execution_status": execution.get("status"),
        "mime_type": execution.get("mime_type"),
    }


def _component_key(component_type: str, component_name: str, component_subtype: str) -> str:
    prefix = "db" if component_type == "Database" else "nosql"
    subtype = re.sub(r"[^0-9A-Za-z]+", "_", component_subtype.strip().lower()).strip("_")
    name = re.sub(r"[^0-9A-Za-z]+", "_", component_name.strip()).strip("_").lower()
    parts = [prefix]
    if subtype:
        parts.append(subtype)
    if name:
        parts.append(name)
    return "_".join(parts)


def _file_extension(suggested_filename: Any, mime_type: Any) -> str:
    name = str(suggested_filename or "").strip()
    suffix = Path(name).suffix.lower()
    if suffix in {".csv", ".xls", ".json"}:
        return suffix
    mime = str(mime_type or "").lower()
    if "json" in mime:
        return ".json"
    if "csv" in mime:
        return ".csv"
    if "excel" in mime or "spreadsheet" in mime or "octet-stream" in mime:
        return ".xls"
    return ".bin"


def _load_component_specs(path: str | None) -> list[dict[str, Any]] | None:
    if not path:
        return None
    loaded = json.loads(Path(path).expanduser().read_text(encoding="utf-8"))
    if not isinstance(loaded, list):
        raise RuntimeError("component spec file must be a JSON array")
    return [item for item in loaded if isinstance(item, dict)]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Export SQL/NoSQL component analysis files into diagnostics/00_raw_exports.")
    parser.add_argument("--config")
    parser.add_argument("--service-base-url")
    parser.add_argument("--service-api-key")
    parser.add_argument("--diagnostics-dir", required=True)
    parser.add_argument("--biz-system-id", type=int, required=True)
    parser.add_argument("--end-time", required=True)
    parser.add_argument("--period-minutes", type=int, default=2880)
    parser.add_argument("--source-mode", default="live")
    parser.add_argument("--include-sql", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--include-nosql", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--database-components-file")
    parser.add_argument("--nosql-components-file")
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    settings = RemoteClientSettings.from_env(config_path=args.config)
    effective = RemoteClientSettings(
        service_base_url=(args.service_base_url or settings.service_base_url).rstrip("/"),
        service_api_key=args.service_api_key if args.service_api_key is not None else settings.service_api_key,
        timeout_seconds=settings.timeout_seconds,
        default_source_mode=settings.default_source_mode,
        config_path=settings.config_path,
    )
    client = AdapterRemoteClient(effective)
    payload = export_component_analysis_raw(
        client,
        diagnostics_dir=args.diagnostics_dir,
        biz_system_id=args.biz_system_id,
        end_time=args.end_time,
        period_minutes=args.period_minutes,
        source_mode=args.source_mode or effective.default_source_mode,
        include_sql=args.include_sql,
        include_nosql=args.include_nosql,
        database_components=_load_component_specs(args.database_components_file),
        nosql_components=_load_component_specs(args.nosql_components_file),
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
