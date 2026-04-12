from __future__ import annotations

import argparse
import base64
import json
import re
from pathlib import Path
from typing import Any

from tingyun_adapter.config.settings import AdapterSettings
from tingyun_adapter.invocation.sdk import Adapter


def _load_json_file(path: str) -> object:
    with Path(path).expanduser().open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _safe_filename(name: str, *, fallback: str) -> str:
    cleaned = re.sub(r"[^\w.\-]+", "_", str(name or "").strip(), flags=re.ASCII).strip("._")
    return cleaned or fallback


def _default_manifest_name(export_key: str, suffix: str | None = None) -> str:
    export_key_safe = _safe_filename(export_key, fallback="export")
    if not suffix:
        return f"{export_key_safe}_manifest.json"
    suffix_safe = re.sub(r"[^0-9A-Za-z]+", "_", suffix).strip("_")
    if not suffix_safe or suffix_safe == export_key_safe:
        return f"{export_key_safe}_manifest.json"
    return f"{export_key_safe}_{suffix_safe}_manifest.json"


def _build_manifest(envelope: dict[str, Any]) -> dict[str, Any]:
    payload = dict(envelope.get("payload") or {})
    execution = dict(payload.get("execution") or {})
    if "content_base64" in execution:
        execution["content_base64"] = f"<omitted:{len(str(execution['content_base64']))} chars>"
    payload["execution"] = execution
    manifest = dict(envelope)
    manifest["payload"] = payload
    return manifest


def persist_export_artifacts(
    envelope: dict[str, Any],
    *,
    output_dir: str | Path,
    save_manifest: bool = True,
) -> dict[str, Any]:
    output_root = Path(output_dir).expanduser().resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    payload = envelope.get("payload") or {}
    selected_export = payload.get("selected_export") or {}
    execution = payload.get("execution") or {}
    export_key = str(selected_export.get("export_key") or "export")
    suggested_filename = _safe_filename(
        str(execution.get("suggested_filename") or selected_export.get("suggested_filename") or ""),
        fallback=f"{export_key}.bin",
    )

    written_files: list[str] = []
    saved_content = False

    if execution.get("content_base64"):
        file_path = output_root / suggested_filename
        file_path.write_bytes(base64.b64decode(str(execution["content_base64"])))
        written_files.append(str(file_path))
        saved_content = True
    elif "response_json" in execution:
        if not suggested_filename.lower().endswith(".json"):
            suggested_filename = f"{suggested_filename}.json"
        file_path = output_root / suggested_filename
        file_path.write_text(json.dumps(execution["response_json"], ensure_ascii=False, indent=2), encoding="utf-8")
        written_files.append(str(file_path))
        saved_content = True

    manifest_path: Path | None = None
    if save_manifest:
        manifest_name = _default_manifest_name(
            export_key,
            str(
                payload.get("scope", {}).get("endTime")
                or execution.get("suggested_filename")
                or selected_export.get("suggested_filename")
                or ""
            ),
        )
        manifest_path = output_root / manifest_name
        manifest_path.write_text(json.dumps(_build_manifest(envelope), ensure_ascii=False, indent=2), encoding="utf-8")
        written_files.append(str(manifest_path))

    return {
        "output_dir": str(output_root),
        "saved_content": saved_content,
        "manifest_saved": manifest_path is not None,
        "written_files": written_files,
        "execution_status": execution.get("status"),
        "byte_size": execution.get("byte_size"),
        "mime_type": execution.get("mime_type"),
    }


def build_parser(settings: AdapterSettings) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Tingyun export pack and persist exported artifacts locally.")
    parser.add_argument("--config", default=settings.config_path)
    parser.add_argument("--base-url", default=settings.base_url)
    parser.add_argument("--token", default=settings.token)
    parser.add_argument("--lang", default=settings.lang)
    parser.add_argument("--timeout-seconds", type=int, default=settings.timeout_seconds)
    parser.add_argument("--captured-api-dir", default=settings.captured_api_dir)
    parser.add_argument("--knowledge-dir", default=settings.knowledge_dir)
    parser.add_argument("--biz-system-id", type=int, required=True)
    parser.add_argument("--end-time", required=True)
    parser.add_argument("--period-minutes", type=int, default=30)
    parser.add_argument("--source-mode", choices=["auto", "sample", "live"], default="live")
    parser.add_argument("--export-kind", required=True)
    parser.add_argument("--export-params-file")
    parser.add_argument("--output-dir", default="./exports")
    parser.add_argument("--max-export-bytes", type=int, default=20_000_000)
    parser.add_argument("--save-manifest", action=argparse.BooleanOptionalAction, default=True)
    return parser


def main() -> int:
    bootstrap = argparse.ArgumentParser(add_help=False)
    bootstrap.add_argument("--config")
    bootstrap_args, _ = bootstrap.parse_known_args()
    settings = AdapterSettings.from_env(config_path=bootstrap_args.config)
    parser = build_parser(settings)
    args = parser.parse_args()

    export_params = {}
    if args.export_params_file:
        loaded = _load_json_file(args.export_params_file)
        if not isinstance(loaded, dict):
            raise SystemExit("--export-params-file must contain a JSON object")
        export_params = dict(loaded)

    adapter = Adapter.from_env(
        config_path=args.config,
        base_url=args.base_url,
        token=args.token,
        lang=args.lang,
        timeout_seconds=args.timeout_seconds,
        captured_api_dir=args.captured_api_dir,
        knowledge_dir=args.knowledge_dir,
    )
    context = adapter.build_context(
        biz_system_id=args.biz_system_id,
        end_time=args.end_time,
        period_minutes=args.period_minutes,
    )
    envelope = adapter.build_data_export_pack(
        context,
        source_mode=args.source_mode,
        export_kind=args.export_kind,
        export_params=export_params,
        execute_export=True,
        include_file_content=True,
        max_export_bytes=args.max_export_bytes,
    ).to_dict()

    persist_result = persist_export_artifacts(
        envelope,
        output_dir=args.output_dir,
        save_manifest=args.save_manifest,
    )
    payload = envelope.get("payload") or {}
    execution = payload.get("execution") or {}
    print(
        json.dumps(
            {
                "export_kind": args.export_kind,
                "scope": payload.get("scope") or {},
                "selected_export": {
                    "export_key": (payload.get("selected_export") or {}).get("export_key"),
                    "label": (payload.get("selected_export") or {}).get("label"),
                    "suggested_filename": execution.get("suggested_filename")
                    or (payload.get("selected_export") or {}).get("suggested_filename"),
                },
                "execution": {
                    "status": execution.get("status"),
                    "status_code": execution.get("status_code"),
                    "mime_type": execution.get("mime_type"),
                    "byte_size": execution.get("byte_size"),
                    "content_included": execution.get("content_included"),
                    "content_omitted_reason": execution.get("content_omitted_reason"),
                },
                "persist_result": persist_result,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
