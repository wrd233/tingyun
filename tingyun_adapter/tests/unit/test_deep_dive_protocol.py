from __future__ import annotations

import unittest

from tingyun_adapter.usecases.deep_dive_protocol import build_deep_dive_seed, summarize_bundle_counts


class DeepDiveProtocolTests(unittest.TestCase):
    def test_build_deep_dive_seed_maps_sql_candidate_to_sql_master(self) -> None:
        seed = build_deep_dive_seed(
            {
                "candidate_key": "sql:fingerprint-1",
                "candidate_type": "sql",
                "display_name": "SELECT * FROM orders",
                "impact_scope": "core_path",
                "evidence_strength": "medium",
                "source_packs": ["slow_sql_pack", "trace_case_pack"],
                "recommended_next_packs": ["sql_fact_sheet", "database_component_pack"],
                "sql_fingerprint": "fingerprint-1",
                "component_name": "10.190.22.21:3306",
                "component_subtype": "MySQL",
                "impact_objects": [{"action_id": 20441, "action_name": "核心提交接口"}],
                "target_ref": {"kind": "sql", "component_name": "10.190.22.21:3306", "component_subtype": "MySQL"},
            }
        )
        self.assertEqual(seed["object_type"], "sql")
        self.assertEqual(seed["source_master_table"], "sql_master.csv")
        self.assertEqual(seed["deep_dive_kind"], "sql_bottleneck")
        self.assertIn("sql_fact_sheet", seed["recommended_next_packs"])
        self.assertIn("request_hint:20441", seed["related_object_ids"])
        self.assertEqual(seed["master_match_hints"]["sql_fingerprint"], "fingerprint-1")

    def test_summarize_bundle_counts_uses_existing_adapter_payload_shapes(self) -> None:
        counts = summarize_bundle_counts(
            {
                "page_links": [{"url": "http://example/a"}, {"url": "http://example/b"}],
                "screenshot_hints": [{"purpose": "说明慢调用"}],
                "evidence": [{"type": "trace"}, {"type": "sql"}],
                "evidence_linkage": {"related_traces": [{"trace_id": "1"}]},
            }
        )
        self.assertEqual(counts["page_link_count"], 2)
        self.assertEqual(counts["screenshot_hint_count"], 1)
        self.assertEqual(counts["evidence_count"], 2)
        self.assertEqual(counts["trace_link_count"], 1)


if __name__ == "__main__":
    unittest.main()
