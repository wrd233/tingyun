from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .component_analysis_exports import export_component_analysis_raw
from .config import RemoteClientSettings
from .http_client import AdapterRemoteClient
from .master_tables_pipeline import materialize_master_tables, prepare_master_table_inputs
from .report_pack_builder import build_report_pack


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Remote client for a Tingyun adapter service.")
    parser.add_argument("--config")
    parser.add_argument("--service-base-url")
    parser.add_argument("--service-api-key")

    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("healthz", help="Call /healthz on the remote service.")
    subparsers.add_parser("meta", help="Call /v1/meta on the remote service.")

    build_pack = subparsers.add_parser("build-pack", help="Build a pack through the remote service.")
    build_pack.add_argument("--pack-type", required=True)
    build_pack.add_argument("--biz-system-id", type=int, required=True)
    build_pack.add_argument("--end-time", required=True)
    build_pack.add_argument("--period-minutes", type=int, default=30)
    build_pack.add_argument("--source-mode")
    build_pack.add_argument("--limit", type=int, default=5)
    build_pack.add_argument("--application-id", type=int)
    build_pack.add_argument("--instance-id", type=int)
    build_pack.add_argument("--action-id", type=int)
    build_pack.add_argument("--action-type", default="TX")
    build_pack.add_argument("--component-name")
    build_pack.add_argument("--component-subtype")
    build_pack.add_argument("--metric-category")
    build_pack.add_argument("--trace-id")
    build_pack.add_argument("--query-timestamp")
    build_pack.add_argument("--trace-guid")
    build_pack.add_argument("--action-guid")
    build_pack.add_argument("--request-id")
    build_pack.add_argument("--op-name")
    build_pack.add_argument("--proposal-file")
    build_pack.add_argument("--persist-proposals", action=argparse.BooleanOptionalAction, default=True)

    build_report = subparsers.add_parser("build-report-pack", help="Build a local report_pack directory from remote packs.")
    build_report.add_argument("--biz-system-id", type=int, required=True)
    build_report.add_argument("--start-time", required=True)
    build_report.add_argument("--end-time", required=True)
    build_report.add_argument("--source-mode")
    build_report.add_argument("--limit", type=int, default=5)
    build_report.add_argument("--output-dir", default="./report_pack")

    export_component_analysis = subparsers.add_parser(
        "export-component-analysis-raw",
        help="Export SQL/NoSQL component analysis files into diagnostics/00_raw_exports.",
    )
    export_component_analysis.add_argument("--diagnostics-dir", required=True)
    export_component_analysis.add_argument("--biz-system-id", type=int, required=True)
    export_component_analysis.add_argument("--end-time", required=True)
    export_component_analysis.add_argument("--period-minutes", type=int, default=2880)
    export_component_analysis.add_argument("--source-mode")
    export_component_analysis.add_argument("--include-sql", action=argparse.BooleanOptionalAction, default=True)
    export_component_analysis.add_argument("--include-nosql", action=argparse.BooleanOptionalAction, default=True)
    export_component_analysis.add_argument("--database-components-file")
    export_component_analysis.add_argument("--nosql-components-file")

    prepare_tables = subparsers.add_parser(
        "prepare-master-table-inputs",
        help="Build 01_prepared_tables from diagnostics raw exports.",
    )
    prepare_tables.add_argument("--diagnostics-dir", required=True)
    prepare_tables.add_argument("--system-key", required=True)
    prepare_tables.add_argument("--batch-key", required=True)
    prepare_tables.add_argument("--rules-file")

    materialize_tables = subparsers.add_parser(
        "materialize-master-tables",
        help="Build 02_master_tables and 03_evidence_indexes from prepared tables.",
    )
    materialize_tables.add_argument("--diagnostics-dir", required=True)
    materialize_tables.add_argument("--system-key", required=True)
    materialize_tables.add_argument("--batch-key", required=True)
    return parser


def _settings_from_args(args: argparse.Namespace) -> RemoteClientSettings:
    settings = RemoteClientSettings.from_env(config_path=args.config)
    return RemoteClientSettings(
        service_base_url=(args.service_base_url or settings.service_base_url).rstrip("/"),
        service_api_key=args.service_api_key if args.service_api_key is not None else settings.service_api_key,
        timeout_seconds=settings.timeout_seconds,
        default_source_mode=settings.default_source_mode,
        config_path=settings.config_path,
    )


def _pack_payload(args: argparse.Namespace, default_source_mode: str) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "bizSystemId": args.biz_system_id,
        "endTime": args.end_time,
        "periodMinutes": args.period_minutes,
        "sourceMode": args.source_mode or default_source_mode,
        "limit": args.limit,
    }
    optional_fields = {
        "applicationId": args.application_id,
        "instanceId": args.instance_id,
        "actionId": args.action_id,
        "actionType": args.action_type,
        "componentName": args.component_name,
        "componentSubtype": args.component_subtype,
        "metricCategory": args.metric_category,
        "traceId": args.trace_id,
        "queryTimestamp": args.query_timestamp,
        "traceGuid": args.trace_guid,
        "actionGuid": args.action_guid,
        "requestId": args.request_id,
        "opName": args.op_name,
    }
    for key, value in optional_fields.items():
        if value is not None:
            if key == "queryTimestamp":
                payload[key] = str(value)
            else:
                payload[key] = value
    if args.proposal_file:
        proposal_items = _load_proposals(args.proposal_file)
        payload["proposalItems"] = proposal_items
        payload["persistProposals"] = args.persist_proposals
    return payload


def _load_proposals(path: str) -> list[dict[str, Any]]:
    with Path(path).expanduser().open("r", encoding="utf-8") as handle:
        loaded = json.load(handle)
    if isinstance(loaded, dict):
        proposals = loaded.get("proposals")
        if not isinstance(proposals, list):
            raise RuntimeError("proposal file dict must contain a 'proposals' list")
        return [item for item in proposals if isinstance(item, dict)]
    if isinstance(loaded, list):
        return [item for item in loaded if isinstance(item, dict)]
    raise RuntimeError("proposal file must be a JSON list or a JSON object with a 'proposals' list")


def _load_json_dict(path: str) -> dict[str, Any]:
    with Path(path).expanduser().open("r", encoding="utf-8") as handle:
        loaded = json.load(handle)
    if not isinstance(loaded, dict):
        raise RuntimeError("rules file must be a JSON object")
    return loaded


def _load_json_list(path: str) -> list[dict[str, Any]]:
    with Path(path).expanduser().open("r", encoding="utf-8") as handle:
        loaded = json.load(handle)
    if not isinstance(loaded, list):
        raise RuntimeError("component file must be a JSON array")
    return [item for item in loaded if isinstance(item, dict)]


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()
    settings = _settings_from_args(args)
    client = AdapterRemoteClient(settings)

    if args.command == "healthz":
        payload = client.healthz()
    elif args.command == "meta":
        payload = client.meta()
    elif args.command == "build-pack":
        payload = client.build_pack(args.pack_type, _pack_payload(args, settings.default_source_mode))
    elif args.command == "build-report-pack":
        payload = build_report_pack(
            client,
            biz_system_id=args.biz_system_id,
            start_time=args.start_time,
            end_time=args.end_time,
            source_mode=args.source_mode or settings.default_source_mode,
            limit=args.limit,
            output_dir=args.output_dir,
            command_display=" ".join(
                [
                    "build-report-pack",
                    f"--biz-system-id {args.biz_system_id}",
                    f"--start-time {args.start_time}",
                    f"--end-time {args.end_time}",
                    f"--source-mode {args.source_mode or settings.default_source_mode}",
                    f"--limit {args.limit}",
                    f"--output-dir {args.output_dir}",
                ]
            ),
        )
    elif args.command == "export-component-analysis-raw":
        payload = export_component_analysis_raw(
            client,
            diagnostics_dir=args.diagnostics_dir,
            biz_system_id=args.biz_system_id,
            end_time=args.end_time,
            period_minutes=args.period_minutes,
            source_mode=args.source_mode or settings.default_source_mode,
            include_sql=args.include_sql,
            include_nosql=args.include_nosql,
            database_components=_load_json_list(args.database_components_file) if args.database_components_file else None,
            nosql_components=_load_json_list(args.nosql_components_file) if args.nosql_components_file else None,
        )
    elif args.command == "prepare-master-table-inputs":
        payload = prepare_master_table_inputs(
            args.diagnostics_dir,
            system_key=args.system_key,
            batch_key=args.batch_key,
            rules=_load_json_dict(args.rules_file) if args.rules_file else None,
        )
    elif args.command == "materialize-master-tables":
        payload = materialize_master_tables(
            args.diagnostics_dir,
            system_key=args.system_key,
            batch_key=args.batch_key,
        )
    else:
        payload = {
            "service_base_url": settings.service_base_url,
            "config_path": settings.config_path,
            "has_service_api_key": bool(settings.service_api_key),
            "default_source_mode": settings.default_source_mode,
            "commands": [
                "healthz",
                "meta",
                "build-pack",
                "build-report-pack",
                "export-component-analysis-raw",
                "prepare-master-table-inputs",
                "materialize-master-tables",
            ],
        }

    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
