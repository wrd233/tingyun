from __future__ import annotations

import argparse
import json
import tempfile
import unittest
from pathlib import Path

from tingyun_adapter_client.cli import _build_parser, _load_proposals, _pack_payload


class ClientCliTests(unittest.TestCase):
    def test_pack_payload_normalizes_query_timestamp_and_op_name(self) -> None:
        args = argparse.Namespace(
            biz_system_id=1065,
            end_time="2026-04-07 12:24",
            period_minutes=30,
            source_mode="live",
            limit=5,
            application_id=1644,
            instance_id=None,
            action_id=13513,
            action_type="TX",
            component_name="10.0.0.1:3306",
            component_subtype="MySQL",
            metric_category=None,
            trace_id="1782890998",
            query_timestamp=1775535633940,
            trace_guid="trace-guid",
            action_guid="action-guid",
            request_id="request-id",
            op_name="SELECT * FROM dual",
            proposal_file=None,
            persist_proposals=True,
        )
        payload = _pack_payload(args, "sample")
        self.assertEqual(payload["queryTimestamp"], "1775535633940")
        self.assertEqual(payload["opName"], "SELECT * FROM dual")

    def test_load_proposals_supports_wrapped_dict(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "proposal.json"
            path.write_text(
                json.dumps({"proposals": [{"proposal_type": "action_labels", "summary": "demo"}]}),
                encoding="utf-8",
            )
            proposals = _load_proposals(str(path))
        self.assertEqual(len(proposals), 1)
        self.assertEqual(proposals[0]["proposal_type"], "action_labels")

    def test_build_report_pack_parser_accepts_time_range(self) -> None:
        parser = _build_parser()
        args = parser.parse_args(
            [
                "build-report-pack",
                "--biz-system-id",
                "1065",
                "--start-time",
                "2025-12-20",
                "--end-time",
                "2026-03-31",
                "--source-mode",
                "live",
                "--limit",
                "6",
                "--output-dir",
                "./report_pack",
            ]
        )
        self.assertEqual(args.command, "build-report-pack")
        self.assertEqual(args.biz_system_id, 1065)
        self.assertEqual(args.start_time, "2025-12-20")
        self.assertEqual(args.end_time, "2026-03-31")
        self.assertEqual(args.limit, 6)

    def test_prepare_master_table_inputs_parser_accepts_diagnostics_context(self) -> None:
        parser = _build_parser()
        args = parser.parse_args(
            [
                "prepare-master-table-inputs",
                "--diagnostics-dir",
                "./diagnostics",
                "--system-key",
                "bizsystem_1065",
                "--batch-key",
                "2026-04-12-check",
                "--rules-file",
                "./screening_rules.json",
            ]
        )
        self.assertEqual(args.command, "prepare-master-table-inputs")
        self.assertEqual(args.system_key, "bizsystem_1065")
        self.assertEqual(args.batch_key, "2026-04-12-check")
        self.assertEqual(args.rules_file, "./screening_rules.json")

    def test_export_component_analysis_raw_parser_accepts_component_files(self) -> None:
        parser = _build_parser()
        args = parser.parse_args(
            [
                "export-component-analysis-raw",
                "--diagnostics-dir",
                "./diagnostics",
                "--biz-system-id",
                "1065",
                "--end-time",
                "2026-04-12 22:15",
                "--period-minutes",
                "2880",
                "--database-components-file",
                "./database_components.json",
                "--nosql-components-file",
                "./nosql_components.json",
            ]
        )
        self.assertEqual(args.command, "export-component-analysis-raw")
        self.assertEqual(args.biz_system_id, 1065)
        self.assertEqual(args.database_components_file, "./database_components.json")
        self.assertEqual(args.nosql_components_file, "./nosql_components.json")


if __name__ == "__main__":
    unittest.main()
