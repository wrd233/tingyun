from __future__ import annotations

import argparse
import json
from pathlib import Path

from .master_tables_pipeline import prepare_master_table_inputs


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prepare master table inputs from APM export tables.")
    parser.add_argument("--diagnostics-dir", required=True)
    parser.add_argument("--system-key", required=True)
    parser.add_argument("--batch-key", required=True)
    parser.add_argument("--rules-file")
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    rules = None
    if args.rules_file:
        rules = json.loads(Path(args.rules_file).expanduser().read_text(encoding="utf-8"))
        if not isinstance(rules, dict):
            raise RuntimeError("rules file must be a JSON object")
    payload = prepare_master_table_inputs(
        args.diagnostics_dir,
        system_key=args.system_key,
        batch_key=args.batch_key,
        rules=rules,
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
