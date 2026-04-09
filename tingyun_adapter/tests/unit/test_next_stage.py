import unittest
from pathlib import Path

from tingyun_adapter.config.settings import AdapterSettings
from tingyun_adapter.domain.models.common import ActionRef
from tingyun_adapter.invocation.sdk import Adapter


ROOT = Path(__file__).resolve().parents[2]
CAPTURED_API_DIR = ROOT.parent / "tingyun_cdp_capture" / "captured_api"


class NextStageBuilderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.adapter = Adapter(
            AdapterSettings(
                captured_api_dir=str(CAPTURED_API_DIR),
                token="secret-test-token-value",
            )
        )

    def test_pack_output_masks_token(self) -> None:
        context = self.adapter.build_context(biz_system_id=1059, end_time="2026-04-03 12:20", period_minutes=30)
        envelope = self.adapter.build_system_snapshot(context, source_mode="sample")
        auth = envelope.to_dict()["context"]["auth"]
        self.assertTrue(auth["token_present"])
        self.assertNotEqual(auth["token"], "secret-test-token-value")

    def test_build_diagnostic_candidate_pack_from_samples(self) -> None:
        context = self.adapter.build_context(biz_system_id=1065, end_time="2026-04-03 12:20", period_minutes=30)
        envelope = self.adapter.build_diagnostic_candidate_pack(context, source_mode="sample", limit=3)
        payload = envelope.to_dict()["payload"]
        self.assertEqual(envelope.pack_type, "diagnostic_candidate_pack")
        self.assertGreater(len(payload["action_candidates"]), 0)
        self.assertIn("recommended_next_packs", payload)

    def test_build_action_fact_sheet_from_samples(self) -> None:
        context = self.adapter.build_context(biz_system_id=1065, end_time="2026-04-03 12:20", period_minutes=30)
        envelope = self.adapter.build_action_fact_sheet(
            context,
            source_mode="sample",
            action_ref=ActionRef(biz_system_id=1065, application_id=1644, action_id=13220, action_type="TX"),
        )
        payload = envelope.to_dict()["payload"]
        self.assertEqual(envelope.pack_type, "action_fact_sheet")
        self.assertEqual(payload["action_ref"]["action_id"], 13220)
        self.assertIn("suspect_signals", payload)
        self.assertIn("trace_candidates", payload)

    def test_build_trace_fact_sheet_from_samples(self) -> None:
        context = self.adapter.build_context(biz_system_id=1062, end_time="2026-04-03 12:20", period_minutes=30)
        envelope = self.adapter.build_trace_fact_sheet(context, source_mode="sample")
        payload = envelope.to_dict()["payload"]
        self.assertEqual(envelope.pack_type, "trace_fact_sheet")
        self.assertIn("trace", payload)
        self.assertIn("suspect_signals", payload)
        self.assertIn("drilldown_keys", payload)

    def test_build_trace_sql_pack_from_samples(self) -> None:
        context = self.adapter.build_context(biz_system_id=1062, end_time="2026-04-03 12:20", period_minutes=30)
        envelope = self.adapter.build_trace_sql_pack(context, source_mode="sample")
        payload = envelope.to_dict()["payload"]
        self.assertEqual(envelope.pack_type, "trace_sql_pack")
        self.assertIn("sql_summary", payload)
        self.assertIn("sqls", payload)
        self.assertIn("database_spans", payload)
        self.assertIn("drilldown_keys", payload)

    def test_build_trace_execution_pack_from_samples(self) -> None:
        context = self.adapter.build_context(biz_system_id=1062, end_time="2026-04-03 12:20", period_minutes=30)
        envelope = self.adapter.build_trace_execution_pack(context, source_mode="sample")
        payload = envelope.to_dict()["payload"]
        self.assertEqual(envelope.pack_type, "trace_execution_pack")
        self.assertIn("call_tree_summary", payload)
        self.assertIn("snapshot_summary", payload)
        self.assertIn("exception_summary", payload)
        self.assertIn("pool_summary", payload)


if __name__ == "__main__":
    unittest.main()
