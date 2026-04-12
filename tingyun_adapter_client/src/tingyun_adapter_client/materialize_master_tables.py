from __future__ import annotations

import argparse
import json

from .master_tables_pipeline import materialize_master_tables


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Materialize master tables and evidence indexes from prepared tables.")
    parser.add_argument("--diagnostics-dir", required=True)
    parser.add_argument("--system-key", required=True)
    parser.add_argument("--batch-key", required=True)
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    payload = materialize_master_tables(
        args.diagnostics_dir,
        system_key=args.system_key,
        batch_key=args.batch_key,
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
