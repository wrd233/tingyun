from __future__ import annotations

import argparse
import json

from tingyun_adapter.config.settings import AdapterSettings
from tingyun_adapter.domain.models.common import ActionRef, ConnectionPoolRef, DatabaseComponentRef, NoSQLComponentRef, TraceRef
from tingyun_adapter.invocation.sdk import Adapter


def build_parser(settings: AdapterSettings) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Tingyun adapter CLI bootstrap.")
    parser.add_argument("--config", default=settings.config_path)
    parser.add_argument("--base-url", default=settings.base_url)
    parser.add_argument("--token", default=settings.token)
    parser.add_argument("--lang", default=settings.lang)
    parser.add_argument("--timeout-seconds", type=int, default=settings.timeout_seconds)
    parser.add_argument("--captured-api-dir", default=settings.captured_api_dir)
    parser.add_argument(
        "--build-pack",
        choices=[
            "system_snapshot",
            "action_hotspot_pack",
            "diagnostic_candidate_pack",
            "action_fact_sheet",
            "trace_case_pack",
            "trace_fact_sheet",
            "report_fact_pack",
            "database_component_pack",
            "nosql_component_pack",
            "connection_pool_pack",
            "instance_analysis_pack",
            "topology_dependency_pack",
            "external_dependency_pack",
            "slow_sql_pack",
            "sql_fact_sheet",
            "action_dependency_breakdown_pack",
            "business_labels_pack",
            "stability_signals_pack",
            "impact_signals_pack",
            "comparison_signals_pack",
            "page_experience_pack",
        ],
    )
    parser.add_argument("--biz-system-id", type=int)
    parser.add_argument("--end-time")
    parser.add_argument("--period-minutes", type=int, default=30)
    parser.add_argument("--source-mode", choices=["auto", "sample", "live"], default="auto")
    parser.add_argument("--component-name")
    parser.add_argument("--component-subtype")
    parser.add_argument("--metric-category")
    parser.add_argument("--application-id", type=int)
    parser.add_argument("--instance-id", type=int)
    parser.add_argument("--action-id", type=int)
    parser.add_argument("--action-type", default="TX")
    parser.add_argument("--trace-id")
    parser.add_argument("--query-timestamp")
    parser.add_argument("--trace-guid")
    parser.add_argument("--action-guid")
    parser.add_argument("--request-id")
    parser.add_argument("--op-name")
    parser.add_argument("--limit", type=int, default=5)
    return parser


def main() -> int:
    bootstrap = argparse.ArgumentParser(add_help=False)
    bootstrap.add_argument("--config")
    bootstrap_args, _ = bootstrap.parse_known_args()
    settings = AdapterSettings.from_env(config_path=bootstrap_args.config)
    parser = build_parser(settings)
    args = parser.parse_args()
    adapter = Adapter.from_env(
        config_path=args.config,
        base_url=args.base_url,
        token=args.token,
        lang=args.lang,
        timeout_seconds=args.timeout_seconds,
        captured_api_dir=args.captured_api_dir,
    )
    if args.build_pack:
        if not args.biz_system_id or not args.end_time:
            raise SystemExit("--build-pack requires --biz-system-id and --end-time")
        context = adapter.build_context(
            biz_system_id=args.biz_system_id,
            end_time=args.end_time,
            period_minutes=args.period_minutes,
        )
        if args.build_pack == "system_snapshot":
            envelope = adapter.build_system_snapshot(context, source_mode=args.source_mode)
        elif args.build_pack == "action_hotspot_pack":
            envelope = adapter.build_action_hotspot_pack(context, source_mode=args.source_mode)
        elif args.build_pack == "diagnostic_candidate_pack":
            envelope = adapter.build_diagnostic_candidate_pack(context, source_mode=args.source_mode, limit=args.limit)
        elif args.build_pack == "action_fact_sheet":
            action_ref = None
            if args.action_id and args.application_id:
                action_ref = ActionRef(
                    biz_system_id=args.biz_system_id,
                    application_id=args.application_id,
                    action_id=args.action_id,
                    action_type=args.action_type,
                )
            envelope = adapter.build_action_fact_sheet(context, source_mode=args.source_mode, action_ref=action_ref, trace_limit=args.limit)
        elif args.build_pack == "trace_case_pack":
            envelope = adapter.build_trace_case_pack(context, source_mode=args.source_mode)
        elif args.build_pack == "trace_fact_sheet":
            action_ref = None
            if args.action_id and args.application_id:
                action_ref = ActionRef(
                    biz_system_id=args.biz_system_id,
                    application_id=args.application_id,
                    action_id=args.action_id,
                    action_type=args.action_type,
                )
            trace_ref = None
            if args.trace_id or args.query_timestamp or args.trace_guid or args.action_guid or args.request_id:
                trace_ref = TraceRef(
                    biz_system_id=args.biz_system_id,
                    trace_id_numeric=args.trace_id,
                    query_timestamp=args.query_timestamp,
                    trace_guid=args.trace_guid,
                    action_guid=args.action_guid,
                    request_id=args.request_id,
                )
            envelope = adapter.build_trace_fact_sheet(context, source_mode=args.source_mode, action_ref=action_ref, trace_ref=trace_ref)
        elif args.build_pack == "database_component_pack":
            component_ref = None
            if args.component_name:
                component_ref = DatabaseComponentRef(
                    biz_system_id=args.biz_system_id,
                    component_name=args.component_name,
                    component_subtype=args.component_subtype,
                )
            envelope = adapter.build_database_component_pack(context, source_mode=args.source_mode, component_ref=component_ref)
        elif args.build_pack == "nosql_component_pack":
            component_ref = None
            if args.component_name:
                component_ref = NoSQLComponentRef(
                    biz_system_id=args.biz_system_id,
                    component_name=args.component_name,
                    component_subtype=args.component_subtype,
                )
            envelope = adapter.build_nosql_component_pack(context, source_mode=args.source_mode, component_ref=component_ref)
        elif args.build_pack == "connection_pool_pack":
            pool_ref = None
            if args.metric_category or args.application_id or args.instance_id:
                pool_ref = ConnectionPoolRef(
                    biz_system_id=args.biz_system_id,
                    metric_category=args.metric_category,
                    application_id=args.application_id,
                    instance_id=args.instance_id,
                )
            envelope = adapter.build_connection_pool_pack(context, source_mode=args.source_mode, pool_ref=pool_ref)
        elif args.build_pack == "instance_analysis_pack":
            envelope = adapter.build_instance_analysis_pack(
                context,
                source_mode=args.source_mode,
                application_id=args.application_id,
                instance_id=args.instance_id,
            )
        elif args.build_pack == "topology_dependency_pack":
            envelope = adapter.build_topology_dependency_pack(context, source_mode=args.source_mode)
        elif args.build_pack == "external_dependency_pack":
            envelope = adapter.build_external_dependency_pack(context, source_mode=args.source_mode)
        elif args.build_pack == "slow_sql_pack":
            component_ref = None
            if args.component_name:
                component_ref = DatabaseComponentRef(
                    biz_system_id=args.biz_system_id,
                    component_name=args.component_name,
                    component_subtype=args.component_subtype,
                )
            envelope = adapter.build_slow_sql_pack(
                context,
                source_mode=args.source_mode,
                component_ref=component_ref,
                limit=args.limit,
            )
        elif args.build_pack == "sql_fact_sheet":
            component_ref = None
            if args.component_name:
                component_ref = DatabaseComponentRef(
                    biz_system_id=args.biz_system_id,
                    component_name=args.component_name,
                    component_subtype=args.component_subtype,
                )
            envelope = adapter.build_sql_fact_sheet(
                context,
                source_mode=args.source_mode,
                component_ref=component_ref,
                op_name=args.op_name,
                limit=args.limit,
            )
        elif args.build_pack == "action_dependency_breakdown_pack":
            action_ref = None
            if args.action_id and args.application_id:
                action_ref = ActionRef(
                    biz_system_id=args.biz_system_id,
                    application_id=args.application_id,
                    action_id=args.action_id,
                    action_type=args.action_type,
                )
            envelope = adapter.build_action_dependency_breakdown_pack(
                context,
                source_mode=args.source_mode,
                action_ref=action_ref,
            )
        elif args.build_pack == "business_labels_pack":
            envelope = adapter.build_business_labels_pack(context, source_mode=args.source_mode, limit=args.limit)
        elif args.build_pack == "stability_signals_pack":
            envelope = adapter.build_stability_signals_pack(context, source_mode=args.source_mode, limit=args.limit)
        elif args.build_pack == "impact_signals_pack":
            envelope = adapter.build_impact_signals_pack(context, source_mode=args.source_mode, limit=args.limit)
        elif args.build_pack == "comparison_signals_pack":
            envelope = adapter.build_comparison_signals_pack(context, source_mode=args.source_mode, limit=args.limit)
        elif args.build_pack == "page_experience_pack":
            envelope = adapter.build_page_experience_pack(context, source_mode=args.source_mode, limit=args.limit)
        else:
            envelope = adapter.build_report_fact_pack(context, source_mode=args.source_mode)
        print(json.dumps(envelope.to_dict(), ensure_ascii=False, indent=2))
        return 0
    print(
        json.dumps(
            {
                "message": "CLI scaffold ready. Use the SDK/usecases layer next.",
                "config": {
                    "config_path": adapter.settings.config_path,
                    "base_url": adapter.settings.base_url,
                    "lang": adapter.settings.lang,
                    "timeout_seconds": adapter.settings.timeout_seconds,
                    "captured_api_dir": adapter.settings.captured_api_dir,
                },
                "capabilities": {
                    "captured_api_attached": bool(adapter.captured_api and adapter.captured_api.exists()),
                    "has_token": bool(adapter.settings.token),
                    "token_env": adapter.settings.token_env,
                },
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
