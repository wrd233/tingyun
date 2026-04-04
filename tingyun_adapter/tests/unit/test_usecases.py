import unittest
from pathlib import Path

from tingyun_adapter.config.settings import AdapterSettings
from tingyun_adapter.invocation.sdk import Adapter


ROOT = Path(__file__).resolve().parents[2]
CAPTURED_API_DIR = ROOT.parent / "tingyun_cdp_capture" / "captured_api"


class UsecaseBuilderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.adapter = Adapter(
            AdapterSettings(
                captured_api_dir=str(CAPTURED_API_DIR),
            )
        )

    def test_build_system_snapshot_from_samples(self) -> None:
        context = self.adapter.build_context(biz_system_id=1059, end_time="2026-04-03 12:20", period_minutes=30)
        envelope = self.adapter.build_system_snapshot(context, source_mode="sample")
        payload = envelope.to_dict()["payload"]
        self.assertEqual(envelope.pack_type, "system_snapshot")
        self.assertEqual(payload["biz_system"]["id"], 1059)
        self.assertEqual(payload["biz_system"]["name"], "铃与堆场")
        self.assertIn("response", payload["trends"])

    def test_build_action_hotspot_pack_from_samples(self) -> None:
        context = self.adapter.build_context(biz_system_id=1059, end_time="2026-04-03 12:20", period_minutes=30)
        envelope = self.adapter.build_action_hotspot_pack(context, source_mode="sample")
        payload = envelope.to_dict()["payload"]
        self.assertEqual(envelope.pack_type, "action_hotspot_pack")
        self.assertGreater(len(payload["hotspots"]), 0)
        self.assertIn("action", payload["hotspots"][0])

    def test_build_trace_case_pack_from_samples(self) -> None:
        context = self.adapter.build_context(biz_system_id=1062, end_time="2026-04-03 12:20", period_minutes=30)
        envelope = self.adapter.build_trace_case_pack(context, source_mode="sample")
        payload = envelope.to_dict()["payload"]
        self.assertEqual(envelope.pack_type, "trace_case_pack")
        self.assertEqual(payload["trace_case"]["trace"]["biz_system_id"], 1062)
        self.assertEqual(payload["trace_case"]["trace"]["action_id"], 10860)

    def test_build_report_fact_pack_from_samples(self) -> None:
        context = self.adapter.build_context(biz_system_id=1059, end_time="2026-04-03 12:20", period_minutes=30)
        envelope = self.adapter.build_report_fact_pack(context, source_mode="sample")
        payload = envelope.to_dict()["payload"]
        self.assertEqual(envelope.pack_type, "report_fact_pack")
        self.assertEqual(payload["report_scope"]["bizSystemId"], 1059)
        self.assertIn("summary", payload)
        self.assertIn("issues", payload)

    def test_build_database_component_pack_from_samples(self) -> None:
        context = self.adapter.build_context(biz_system_id=1065, end_time="2026-04-03 12:20", period_minutes=30)
        envelope = self.adapter.build_database_component_pack(context, source_mode="sample")
        payload = envelope.to_dict()["payload"]
        self.assertEqual(envelope.pack_type, "database_component_pack")
        self.assertEqual(payload["component"]["component_name"], "10.190.22.21:3306")
        self.assertGreater(len(payload["top_operations"]), 0)
        self.assertGreater(len(payload["top_impacted_actions"]), 0)
        self.assertGreaterEqual(payload["topology_summary"]["node_count"], 1)

    def test_build_nosql_component_pack_from_samples(self) -> None:
        context = self.adapter.build_context(biz_system_id=1065, end_time="2026-04-03 12:20", period_minutes=30)
        envelope = self.adapter.build_nosql_component_pack(context, source_mode="sample")
        payload = envelope.to_dict()["payload"]
        self.assertEqual(envelope.pack_type, "nosql_component_pack")
        self.assertEqual(payload["component"]["component_name"], "10.190.22.20:6379/5")
        self.assertGreater(len(payload["top_operations"]), 0)
        self.assertEqual(payload["top_operations"][0]["op_name_decoded"], "EVAL")
        self.assertIn("error_summary", payload)

    def test_build_connection_pool_pack_from_samples(self) -> None:
        context = self.adapter.build_context(biz_system_id=1059, end_time="2026-04-03 12:20", period_minutes=30)
        envelope = self.adapter.build_connection_pool_pack(context, source_mode="sample")
        payload = envelope.to_dict()["payload"]
        self.assertEqual(envelope.pack_type, "connection_pool_pack")
        self.assertEqual(payload["pool"]["framework"], "Druid")
        self.assertGreater(payload["time_series"]["used_connections"]["point_count"], 0)
        self.assertIn("risk_level", payload["waiter_risk"])


if __name__ == "__main__":
    unittest.main()
