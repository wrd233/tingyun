from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .config import RemoteClientSettings
from .http_client import AdapterRemoteClient


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
    else:
        payload = {
            "service_base_url": settings.service_base_url,
            "config_path": settings.config_path,
            "has_service_api_key": bool(settings.service_api_key),
            "default_source_mode": settings.default_source_mode,
            "commands": ["healthz", "meta", "build-pack"],
        }

    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
