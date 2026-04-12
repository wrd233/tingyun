from __future__ import annotations

import argparse
import json

from .master_tables_pipeline import materialize_deep_dive_from_source


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Materialize deep-dive bundles and sync master/evidence indexes from source JSON.")
    parser.add_argument("--diagnostics-dir", required=True)
    parser.add_argument("--system-key", required=True)
    parser.add_argument("--batch-key", required=True)
    parser.add_argument("--source-json", required=True)
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    payload = materialize_deep_dive_from_source(
        args.diagnostics_dir,
        system_key=args.system_key,
        batch_key=args.batch_key,
        source_json=args.source_json,
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
