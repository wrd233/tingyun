from __future__ import annotations

import json
import tempfile
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

    def _write_json(self, path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _knowledge_doc(self, biz_system_id: int, file_type: str, entries: list[dict], *, stale_entries=None) -> dict:
        return {
            "schema_version": "v1",
            "biz_system": {"id": biz_system_id, "key": f"biz_system_{biz_system_id}"},
            "file_type": file_type,
            "entries": entries,
            "stale_entries": stale_entries or [],
            "metadata": {"created_at": "2026-04-07T10:00:00+08:00", "updated_at": "2026-04-07T10:00:00+08:00", "entry_count": len(entries)},
        }

    def _make_adapter_with_knowledge(self) -> tuple[Adapter, object, dict, dict]:
        context = self.adapter.build_context(biz_system_id=1065, end_time="2026-04-03 12:20", period_minutes=30)
        hotspot_payload = self.adapter.build_action_hotspot_pack(context, source_mode="sample").to_dict()["payload"]
        page_payload = self.adapter.build_page_experience_pack(context, source_mode="sample", limit=5).to_dict()["payload"]
        action = hotspot_payload["hotspots"][0]["action"]
        action_ref = {
            "kind": "action",
            "biz_system_id": action["biz_system_id"],
            "application_id": action["application_id"],
            "action_id": action["id"],
            "action_type": action["type"],
        }
        page_ref = dict(page_payload["pages"][0]["page_ref"])

        tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(tempdir.cleanup)
        root = Path(tempdir.name)
        biz_dir = root / "biz_system_1065"

        self._write_json(
            biz_dir / "system_profile.json",
            self._knowledge_doc(
                1065,
                "system_profile",
                [
                    {
                        "entry_id": "system:profile:1",
                        "entry_type": "system_profile",
                        "object_ref": {"kind": "biz_system", "biz_system_id": 1065},
                        "title": "示例业务系统画像",
                        "summary": "该系统以堆场作业和接口同步为主。",
                        "attributes": {"business_goal": "堆场作业支撑"},
                        "status": "confirmed",
                        "staleness": "active",
                    }
                ],
            ),
        )
        self._write_json(
            biz_dir / "glossary.json",
            self._knowledge_doc(
                1065,
                "glossary",
                [
                    {
                        "entry_id": "glossary:1",
                        "entry_type": "glossary_term",
                        "object_ref": {"kind": "glossary_term", "name": "WebView"},
                        "title": "WebView",
                        "summary": "前台页面透传接口。",
                        "attributes": {"aliases": ["页面透传"]},
                        "status": "confirmed",
                        "staleness": "active",
                    }
                ],
            ),
        )
        self._write_json(
            biz_dir / "critical_paths.json",
            self._knowledge_doc(
                1065,
                "critical_paths",
                [
                    {
                        "entry_id": "critical:path:1",
                        "entry_type": "critical_path",
                        "object_ref": action_ref,
                        "title": "接口同步链路",
                        "summary": "该 action 处于核心接口同步路径。",
                        "attributes": {"path_name": "接口同步链路"},
                        "status": "confirmed",
                        "staleness": "active",
                    }
                ],
            ),
        )
        self._write_json(
            biz_dir / "action_labels.json",
            self._knowledge_doc(
                1065,
                "action_labels",
                [
                    {
                        "entry_id": "action:label:1",
                        "entry_type": "action_label",
                        "object_ref": action_ref,
                        "title": "已确认标签",
                        "summary": "人工确认该 action 偏支撑链路而非核心链路。",
                        "attributes": {"confirmed_labels": ["important_support_path", "real_user_visible"]},
                        "status": "confirmed",
                        "staleness": "active",
                    }
                ],
            ),
        )
        self._write_json(
            biz_dir / "dependency_annotations.json",
            self._knowledge_doc(1065, "dependency_annotations", []),
        )
        self._write_json(
            biz_dir / "known_patterns.json",
            self._knowledge_doc(
                1065,
                "known_patterns",
                [
                    {
                        "entry_id": "pattern:1",
                        "entry_type": "known_pattern",
                        "object_ref": action_ref,
                        "title": "夜间波动",
                        "summary": "该接口在批处理窗口常出现周期性抖动。",
                        "attributes": {"pattern_type": "nightly_batch_related"},
                        "status": "confirmed",
                        "staleness": "active",
                    }
                ],
            ),
        )
        self._write_json(
            biz_dir / "baseline_notes.json",
            self._knowledge_doc(
                1065,
                "baseline_notes",
                [
                    {
                        "entry_id": "baseline:1",
                        "entry_type": "baseline_note",
                        "object_ref": action_ref,
                        "title": "长期基线",
                        "summary": "该对象长期响应时间偏高，需要结合批量窗口解读。",
                        "attributes": {"needs_review": False},
                        "status": "confirmed",
                        "staleness": "active",
                    }
                ],
            ),
        )
        self._write_json(
            biz_dir / "page_route_map.json",
            self._knowledge_doc(
                1065,
                "page_route_map",
                [
                    {
                        "entry_id": "page:route:1",
                        "entry_type": "page_route_map",
                        "object_ref": page_ref,
                        "title": "页面映射",
                        "summary": "该用户入口页映射到代表性接口。",
                        "attributes": {"action_refs": [action_ref], "route_pattern": page_ref.get("route")},
                        "status": "confirmed",
                        "staleness": "active",
                    }
                ],
            ),
        )
        self._write_json(
            biz_dir / "review_queue.json",
            {
                "schema_version": "v1",
                "biz_system": {"id": 1065, "key": "biz_system_1065"},
                "file_type": "review_queue",
                "pending": [
                    {
                        "proposal_id": "proposal:action_labels:existing",
                        "proposal_type": "action_labels",
                        "target_file_hint": "action_labels",
                        "object_ref": action_ref,
                        "title": "待确认标签",
                        "summary": "模型建议该 action 也可能属于核心链路。",
                        "attributes": {"candidate_labels": ["core_business_path"]},
                        "status": "pending",
                        "staleness": "active",
                        "reasoning_summary": "名字和调用路径看起来更接近核心链路。",
                        "conflicts": [],
                        "duplicate_of": [],
                        "dedupe_key": "existing-key",
                        "provenance": {
                            "source_type": "adapter_pack",
                            "source_refs": [{"kind": "pack", "value": "business_labels_pack"}],
                            "created_at": "2026-04-07T10:00:00+08:00",
                            "updated_at": "2026-04-07T10:00:00+08:00",
                            "confidence": 0.7,
                            "author_kind": "model",
                            "creation_method": "model_suggestion",
                        },
                    }
                ],
                "rejected": [],
                "obsolete": [],
                "metadata": {"created_at": "2026-04-07T10:00:00+08:00", "updated_at": "2026-04-07T10:00:00+08:00", "entry_count": 1},
            },
        )
        self._write_json(
            biz_dir / "judgment_log.json",
            {
                "schema_version": "v1",
                "biz_system": {"id": 1065, "key": "biz_system_1065"},
                "file_type": "judgment_log",
                "entries": [
                    {
                        "log_id": "log:1",
                        "entry_type": "analysis_note",
                        "summary": "历史分析认为该对象应结合夜间批处理窗口解读。",
                        "related_refs": [action_ref],
                        "outcome": {"note": "nightly_batch_related"},
                    }
                ],
                "metadata": {"created_at": "2026-04-07T10:00:00+08:00", "updated_at": "2026-04-07T10:00:00+08:00", "entry_count": 1},
            },
        )

        adapter = Adapter(
            AdapterSettings(
                captured_api_dir=str(CAPTURED_API_DIR),
                knowledge_dir=str(root),
            )
        )
        return adapter, context, action_ref, page_ref

    def test_build_system_snapshot_from_samples(self) -> None:
        context = self.adapter.build_context(biz_system_id=1059, end_time="2026-04-03 12:20", period_minutes=30)
        envelope = self.adapter.build_system_snapshot(context, source_mode="sample")
        payload = envelope.to_dict()["payload"]
        self.assertEqual(envelope.pack_type, "system_snapshot")
        self.assertEqual(payload["biz_system"]["id"], 1059)
        self.assertEqual(payload["biz_system"]["name"], "铃与堆场")
        self.assertIn("response", payload["trends"])
        self.assertGreater(len(payload["page_links"]), 0)
        self.assertIn("url_status", payload["page_links"][0])
        self.assertIn("fallback_url", payload["page_links"][0])
        self.assertIn("url_source", payload["page_links"][0])
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
        self.assertIn("priority_hints", payload["objects"][0])
        self.assertIn("impact_features", payload["objects"][0])

    def test_build_comparison_signals_pack_from_samples(self) -> None:
        context = self.adapter.build_context(biz_system_id=1065, end_time="2026-04-03 12:20", period_minutes=30)
        envelope = self.adapter.build_comparison_signals_pack(context, source_mode="sample", limit=5)
        payload = envelope.to_dict()["payload"]
        self.assertEqual(envelope.pack_type, "comparison_signals_pack")
        self.assertEqual(payload["comparison_baseline"]["mode"], "previous_window")
        self.assertEqual(payload["comparison_baseline"]["history_source"], "previous_window_plus_knowledge")
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
        self.assertIn(payload["page_links"][0]["url_status"], {"direct", "navigation_only", "unavailable"})
        self.assertGreater(len(payload["screenshot_hints"]), 0)
        self.assertIn("knowledge_context", payload)
        self.assertIn("candidate_action_links", payload["pages"][0])

    def test_build_screenshot_index_pack_from_samples(self) -> None:
        context = self.adapter.build_context(biz_system_id=1065, end_time="2026-04-03 12:20", period_minutes=30)
        envelope = self.adapter.build_screenshot_index_pack(context, source_mode="sample", limit=5)
        payload = envelope.to_dict()["payload"]
        self.assertEqual(envelope.pack_type, "screenshot_index_pack")
        self.assertGreater(len(payload["screenshot_cards"]), 0)
        self.assertGreater(len(payload["page_links"]), 0)
        self.assertEqual(payload["screenshot_cards"][0]["figure_id"], "FIG-01")
        self.assertTrue(payload["screenshot_cards"][0]["url"])

    def test_build_knowledge_context_pack_from_files(self) -> None:
        adapter, context, action_ref, _ = self._make_adapter_with_knowledge()
        envelope = adapter.build_knowledge_context_pack(context, source_mode="sample", limit=5)
        payload = envelope.to_dict()["payload"]
        self.assertEqual(envelope.pack_type, "knowledge_context_pack")
        self.assertGreater(payload["confirmed_knowledge_summary"]["entry_count"], 0)
        self.assertGreater(payload["pending_proposals_summary"]["pending_count"], 0)
        self.assertGreater(len(payload["recent_judgment_logs"]), 0)
        self.assertGreater(len(payload["core_context"]["action_labels"]), 0)
        self.assertEqual(payload["core_context"]["action_labels"][0]["object_ref"]["action_id"], action_ref["action_id"])

    def test_build_business_labels_pack_reads_confirmed_labels_and_conflicts(self) -> None:
        adapter, context, action_ref, _ = self._make_adapter_with_knowledge()
        payload = adapter.build_business_labels_pack(context, source_mode="sample", limit=5).to_dict()["payload"]
        matched = next(item for item in payload["objects"] if item["target_ref"] == action_ref)
        self.assertGreater(len(matched["confirmed_labels"]), 0)
        self.assertGreater(len(matched["pending_label_proposals"]), 0)
        self.assertGreater(len(matched["label_conflicts"]), 0)

    def test_build_knowledge_update_proposal_pack_merges_existing_pending_item(self) -> None:
        adapter, context, action_ref, _ = self._make_adapter_with_knowledge()
        envelope = adapter.build_knowledge_update_proposal_pack(
            context,
            source_mode="sample",
            proposals=[
                {
                    "proposal_type": "action_labels",
                    "target_file_hint": "action_labels",
                    "target_ref": action_ref,
                    "summary": "再次建议该 action 更接近核心链路。",
                    "attributes": {"candidate_labels": ["core_business_path", "real_user_visible"]},
                    "reasoning_summary": "新一次分析仍然给出相同方向。",
                }
            ],
            persist=True,
        )
        payload = envelope.to_dict()["payload"]
        self.assertEqual(envelope.pack_type, "knowledge_update_proposal_pack")
        self.assertEqual(payload["merge_summary"]["merged_count"], 1)
        self.assertGreaterEqual(payload["merge_summary"]["conflict_count"], 1)
        self.assertEqual(payload["review_queue_snapshot"]["pending_count"], 1)


if __name__ == "__main__":
    unittest.main()
