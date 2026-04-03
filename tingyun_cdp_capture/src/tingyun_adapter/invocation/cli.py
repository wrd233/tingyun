from __future__ import annotations

import argparse
import json

from tingyun_adapter.config.settings import AdapterSettings
from tingyun_adapter.invocation.sdk import Adapter


def build_parser() -> argparse.ArgumentParser:
    settings = AdapterSettings.from_env()
    parser = argparse.ArgumentParser(description="Tingyun adapter CLI bootstrap.")
    parser.add_argument("--base-url", default=settings.base_url)
    parser.add_argument("--lang", default=settings.lang)
    parser.add_argument("--timeout-seconds", type=int, default=settings.timeout_seconds)
    parser.add_argument("--captured-api-dir", default=settings.captured_api_dir)
    parser.add_argument(
        "--build-pack",
        choices=["system_snapshot", "action_hotspot_pack", "trace_case_pack", "report_fact_pack"],
    )
    parser.add_argument("--biz-system-id", type=int)
    parser.add_argument("--end-time")
    parser.add_argument("--period-minutes", type=int, default=30)
    parser.add_argument("--source-mode", choices=["auto", "sample", "live"], default="auto")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    adapter = Adapter.from_env(
        base_url=args.base_url,
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
        elif args.build_pack == "trace_case_pack":
            envelope = adapter.build_trace_case_pack(context, source_mode=args.source_mode)
        else:
            envelope = adapter.build_report_fact_pack(context, source_mode=args.source_mode)
        print(json.dumps(envelope.to_dict(), ensure_ascii=False, indent=2))
        return 0
    print(
        json.dumps(
            {
                "message": "CLI scaffold ready. Use the SDK/usecases layer next.",
                "config": {
                    "base_url": adapter.settings.base_url,
                    "lang": adapter.settings.lang,
                    "timeout_seconds": adapter.settings.timeout_seconds,
                    "captured_api_dir": adapter.settings.captured_api_dir,
                },
                "capabilities": {
                    "captured_api_attached": bool(adapter.captured_api and adapter.captured_api.exists()),
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
