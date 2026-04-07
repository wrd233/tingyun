import unittest
from pathlib import Path

from tingyun_adapter.config.settings import AdapterSettings
from tingyun_adapter.domain.models.common import ActionRef, DatabaseComponentRef
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
        self.assertGreater(len(payload["page_links"]), 0)
        self.assertGreater(len(payload["screenshot_hints"]), 0)
        self.assertIn("page_experience", payload["coverage_boundary"])
        self.assertGreater(len(payload["metric_semantics"]), 0)

    def test_build_action_hotspot_pack_from_samples(self) -> None:
        context = self.adapter.build_context(biz_system_id=1059, end_time="2026-04-03 12:20", period_minutes=30)
        envelope = self.adapter.build_action_hotspot_pack(context, source_mode="sample")
        payload = envelope.to_dict()["payload"]
        self.assertEqual(envelope.pack_type, "action_hotspot_pack")
        self.assertGreater(len(payload["hotspots"]), 0)
        self.assertIn("action", payload["hotspots"][0])
        self.assertGreater(len(payload["page_links"]), 0)
        self.assertGreater(len(payload["screenshot_hints"]), 0)

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
        self.assertGreater(len(payload["page_links"]), 0)
        self.assertGreater(len(payload["screenshot_hints"]), 0)
        self.assertGreater(len(payload["metric_semantics"]), 0)
        self.assertGreater(len(payload["evidence_linkage"]["related_sqls"]), 0)

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

    def test_build_instance_analysis_pack_from_samples(self) -> None:
        context = self.adapter.build_context(biz_system_id=1059, end_time="2026-04-03 12:20", period_minutes=30)
        envelope = self.adapter.build_instance_analysis_pack(context, source_mode="sample", application_id=1648)
        payload = envelope.to_dict()["payload"]
        self.assertEqual(envelope.pack_type, "instance_analysis_pack")
        self.assertEqual(payload["application"]["application_id"], 1648)
        self.assertEqual(payload["summary"]["instance_count"], 3)
        self.assertGreater(payload["cpu_chart"]["point_count"], 0)

    def test_build_topology_dependency_pack_from_samples(self) -> None:
        context = self.adapter.build_context(biz_system_id=1059, end_time="2026-04-03 12:20", period_minutes=30)
        envelope = self.adapter.build_topology_dependency_pack(context, source_mode="sample")
        payload = envelope.to_dict()["payload"]
        self.assertEqual(envelope.pack_type, "topology_dependency_pack")
        self.assertGreater(payload["detail_graph"]["node_count"], 0)
        self.assertGreater(payload["detail_graph"]["node_type_counts"]["external"], 0)
        self.assertGreater(len(payload["dependencies"]), 0)

    def test_build_external_dependency_pack_from_samples(self) -> None:
        context = self.adapter.build_context(biz_system_id=1059, end_time="2026-04-03 12:20", period_minutes=30)
        envelope = self.adapter.build_external_dependency_pack(context, source_mode="sample")
        payload = envelope.to_dict()["payload"]
        self.assertEqual(envelope.pack_type, "external_dependency_pack")
        self.assertGreater(len(payload["external_dependencies"]), 0)
        self.assertIn("http", {item["protocol"] for item in payload["external_dependencies"]})

    def test_build_slow_sql_pack_from_samples(self) -> None:
        context = self.adapter.build_context(biz_system_id=1065, end_time="2026-04-03 12:20", period_minutes=30)
        envelope = self.adapter.build_slow_sql_pack(context, source_mode="sample", limit=5)
        payload = envelope.to_dict()["payload"]
        self.assertEqual(envelope.pack_type, "slow_sql_pack")
        self.assertGreater(len(payload["top_sqls"]), 0)
        self.assertEqual(payload["top_sqls"][0]["component_name"], "10.190.22.21:3306")
        self.assertIn("statement_type_counts", payload["operation_overview"])

    def test_build_sql_fact_sheet_from_samples(self) -> None:
        context = self.adapter.build_context(biz_system_id=1065, end_time="2026-04-03 12:20", period_minutes=30)
        envelope = self.adapter.build_sql_fact_sheet(
            context,
            source_mode="sample",
            component_ref=DatabaseComponentRef(biz_system_id=1065, component_name="10.190.22.21:3306", component_subtype="MySQL"),
        )
        payload = envelope.to_dict()["payload"]
        self.assertEqual(envelope.pack_type, "sql_fact_sheet")
        self.assertEqual(payload["component"]["componentName"], "10.190.22.21:3306")
        self.assertGreater(len(payload["related_actions"]), 0)
        self.assertIn("statement_type", payload["sql_features"])
        self.assertGreater(len(payload["page_links"]), 0)
        self.assertGreater(len(payload["screenshot_hints"]), 0)
        self.assertGreater(len(payload["evidence_linkage"]["related_traces"]), 0)

    def test_build_action_dependency_breakdown_pack_from_samples(self) -> None:
        context = self.adapter.build_context(biz_system_id=1059, end_time="2026-04-03 12:20", period_minutes=30)
        envelope = self.adapter.build_action_dependency_breakdown_pack(
            context,
            source_mode="sample",
            action_ref=ActionRef(biz_system_id=1059, application_id=1648, action_id=20441, action_type="TX"),
        )
        payload = envelope.to_dict()["payload"]
        self.assertEqual(envelope.pack_type, "action_dependency_breakdown_pack")
        self.assertGreater(len(payload["component_breakdown"]), 0)
        self.assertGreater(payload["topology_summary"]["node_count"], 0)
        self.assertIn("component_type_counts", payload["breakdown_summary"])

    def test_build_business_labels_pack_from_samples(self) -> None:
        context = self.adapter.build_context(biz_system_id=1065, end_time="2026-04-03 12:20", period_minutes=30)
        envelope = self.adapter.build_business_labels_pack(context, source_mode="sample", limit=5)
        payload = envelope.to_dict()["payload"]
        self.assertEqual(envelope.pack_type, "business_labels_pack")
        self.assertGreater(len(payload["objects"]), 0)
        self.assertIn("label_counts", payload["summaries"])

    def test_build_stability_signals_pack_from_samples(self) -> None:
        context = self.adapter.build_context(biz_system_id=1065, end_time="2026-04-03 12:20", period_minutes=30)
        envelope = self.adapter.build_stability_signals_pack(context, source_mode="sample", limit=5)
        payload = envelope.to_dict()["payload"]
        self.assertEqual(envelope.pack_type, "stability_signals_pack")
        self.assertGreater(len(payload["objects"]), 0)
        self.assertIn("stability_class_counts", payload["summaries"])

    def test_build_impact_signals_pack_from_samples(self) -> None:
        context = self.adapter.build_context(biz_system_id=1065, end_time="2026-04-03 12:20", period_minutes=30)
        envelope = self.adapter.build_impact_signals_pack(context, source_mode="sample", limit=5)
        payload = envelope.to_dict()["payload"]
        self.assertEqual(envelope.pack_type, "impact_signals_pack")
        self.assertGreater(len(payload["objects"]), 0)
        self.assertIn("impact_tier", payload["objects"][0])

    def test_build_comparison_signals_pack_from_samples(self) -> None:
        context = self.adapter.build_context(biz_system_id=1065, end_time="2026-04-03 12:20", period_minutes=30)
        envelope = self.adapter.build_comparison_signals_pack(context, source_mode="sample", limit=5)
        payload = envelope.to_dict()["payload"]
        self.assertEqual(envelope.pack_type, "comparison_signals_pack")
        self.assertEqual(payload["comparison_baseline"]["mode"], "previous_window")
        self.assertGreater(len(payload["objects"]), 0)

    def test_build_page_experience_pack_from_samples(self) -> None:
        context = self.adapter.build_context(biz_system_id=1065, end_time="2026-04-03 12:20", period_minutes=30)
        envelope = self.adapter.build_page_experience_pack(context, source_mode="sample", limit=5)
        data = envelope.to_dict()
        payload = data["payload"]
        self.assertEqual(envelope.pack_type, "page_experience_pack")
        self.assertGreater(len(payload["pages"]), 0)
        self.assertIn("browser_distribution", data["meta"]["missing_inputs"])
        self.assertEqual(payload["coverage_boundary"]["page_experience"]["status"], "partial")
        self.assertGreater(len(payload["page_links"]), 0)
        self.assertGreater(len(payload["screenshot_hints"]), 0)

    def test_build_screenshot_index_pack_from_samples(self) -> None:
        context = self.adapter.build_context(biz_system_id=1065, end_time="2026-04-03 12:20", period_minutes=30)
        envelope = self.adapter.build_screenshot_index_pack(context, source_mode="sample", limit=5)
        payload = envelope.to_dict()["payload"]
        self.assertEqual(envelope.pack_type, "screenshot_index_pack")
        self.assertGreater(len(payload["screenshot_cards"]), 0)
        self.assertGreater(len(payload["page_links"]), 0)
        self.assertEqual(payload["screenshot_cards"][0]["figure_id"], "FIG-01")


if __name__ == "__main__":
    unittest.main()
