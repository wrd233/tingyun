from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tingyun_adapter.config.settings import AdapterSettings
from tingyun_adapter.domain.models.common import ActionRef, DatabaseComponentRef, TraceRef
from tingyun_adapter.invocation.sdk import Adapter
from tingyun_adapter.usecases.build_session import BuildSession


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
        data = envelope.to_dict()
        payload = data["payload"]
        self.assertEqual(envelope.pack_type, "report_fact_pack")
        self.assertEqual(payload["report_scope"]["bizSystemId"], 1059)
        self.assertIn("summary", payload)
        self.assertIn("issues", payload)
        self.assertIn("observations", payload)
        self.assertIn("sql_candidates", payload)
        self.assertIn("candidate_registry", payload)
        self.assertIn("codex_review_input", payload)
        self.assertIn("main_issue_selections", payload)
        self.assertIn("deep_dive_targets", payload)
        self.assertIn("selected_target_expansions", payload)
        self.assertIn("report_writer_input", payload)
        self.assertIn("report_pack_exports", payload)
        self.assertGreater(len(payload["candidate_registry"]), 0)
        self.assertIn("03_issues/issues.csv", payload["report_pack_exports"])
        self.assertIn("03_issues/observations.csv", payload["report_pack_exports"])
        self.assertIn("03_issues/sql_opportunities.csv", payload["report_pack_exports"])
        self.assertIn("03_issues/main_issue_selections.json", payload["report_pack_exports"])
        self.assertIn("03_issues/deep_dive_targets.json", payload["report_pack_exports"])
        self.assertIn("04_raw/candidate_registry.json", payload["report_pack_exports"])
        self.assertIn("04_raw/issue_candidates.json", payload["report_pack_exports"])
        self.assertIn("04_raw/sql_candidates.json", payload["report_pack_exports"])
        self.assertIn("00_internal/codex_review_input.md", payload["report_pack_exports"])
        self.assertIn("00_internal/codex_review_input.json", payload["report_pack_exports"])
        self.assertIn("diagnostics", payload)
        self.assertIn("phase_1", payload["diagnostics"])
        self.assertIn("upstream_call_count", data["meta"]["build_stats"])
        self.assertIn("00_internal/report_writer_input.md", payload["report_pack_exports"])
        self.assertIn("00_internal/report_writer_input.json", payload["report_pack_exports"])
        self.assertIn("00_internal/template_outline.md", payload["report_pack_exports"])
        self.assertIn("02_sections/sql.md", payload["report_pack_exports"])
        screenshot_export = payload["report_pack_exports"]["01_foundation/screenshot_index.csv"]
        self.assertIn("direct_url", screenshot_export["columns"])
        self.assertIn("fallback_url", screenshot_export["columns"])
        self.assertIn("navigation_path", screenshot_export["columns"])
        self.assertIn("why_relevant", screenshot_export["columns"])
        self.assertIn("page_capability_boundary", payload["report_writer_input"])
        self.assertIn("links_and_screenshots", payload["report_writer_input"])
        deep_dive_types = {item.get("candidate_type") for item in payload["deep_dive_targets"]}
        self.assertTrue({"trace", "sql", "dependency"} & deep_dive_types)
        expansion_types = {item.get("pack_type") for item in payload["selected_target_expansions"]}
        self.assertTrue({"trace_fact_sheet", "sql_fact_sheet", "external_dependency_pack", "topology_dependency_pack"} & expansion_types)

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

    def test_build_deployment_inventory_pack_merges_service_and_component_inventory(self) -> None:
        context = self.adapter.build_context(biz_system_id=1065, end_time="2026-04-03 12:20", period_minutes=30)
        orig_business_overview = self.adapter.application.business_overview
        orig_query_overview = self.adapter.graph.query_overview
        orig_list_instances = self.adapter.instance.list_instances
        orig_list_pools = self.adapter.connection.list_pools
        try:
            self.adapter.application.business_overview = lambda **_: {
                "data": {
                    "bizSystemId": 1065,
                    "bizSystemName": "集团法务",
                    "applicationIds": [1644, 1645],
                    "instanceIds": [2745, 2746, 2747],
                    "hostCount": 2,
                }
            }
            self.adapter.graph.query_overview = lambda **_: {
                "data": [
                    {
                        "systemId": 1065,
                        "applicationId": 1644,
                        "applicationName": "com.nbport.zgb.manage.ManageWebApplication",
                        "language": "Java",
                        "tech": "Undertow",
                        "totalCount": 1000,
                        "throughput": 2.4,
                        "responseP50": 12.3,
                    },
                    {
                        "systemId": 1065,
                        "applicationId": 1645,
                        "applicationName": "com.nbport.zgb.manage.ManageServiceApplication",
                        "language": "Java",
                        "tech": "Netty",
                        "totalCount": 800,
                        "throughput": 1.2,
                        "responseP50": 8.1,
                    },
                ]
            }

            def _instances(**kwargs):
                app_id = kwargs["application_id"]
                if app_id == 1644:
                    return {
                        "data": [
                            {
                                "id": 2745,
                                "name": "app1:8080(10.190.71.31)",
                                "hostIp": "10.190.71.31",
                                "hostName": "app1",
                                "instanceIp": "10.190.71.31",
                                "processName": "java: ManageWebApplication",
                                "os": "linux",
                            }
                        ]
                    }
                return {
                    "data": [
                        {
                            "id": 2746,
                            "name": "app2:8080(10.190.71.32)",
                            "hostIp": "10.190.71.32",
                            "hostName": "app2",
                            "instanceIp": "10.190.71.32",
                            "processName": "java: ManageServiceApplication",
                            "os": "linux",
                        },
                        {
                            "id": 2747,
                            "name": "app3:8080(10.190.71.33)",
                            "hostIp": "10.190.71.33",
                            "hostName": "app3",
                            "instanceIp": "10.190.71.33",
                            "processName": "java: ManageServiceApplication",
                            "os": "linux",
                        },
                    ]
                }

            self.adapter.instance.list_instances = _instances
            self.adapter.connection.list_pools = lambda **_: {
                "data": {
                    "content": [
                        {
                            "addressSplit": "10.190.71.39:54321",
                            "databaseName": "legal",
                            "databaseType": "Kingbase",
                            "framework": "HikariCP",
                            "metricCategory": "kingbase-pool",
                            "applicationId": 1644,
                            "instanceId": 2745,
                        },
                        {
                            "addressSplit": "10.190.71.38:6379",
                            "databaseName": "0",
                            "databaseType": "Redis",
                            "framework": "Redisson",
                            "metricCategory": "redis-pool",
                            "applicationId": 1644,
                            "instanceId": 2745,
                        },
                        {
                            "addressSplit": "10.190.71.38:6379",
                            "databaseName": "0",
                            "databaseType": "Redis",
                            "framework": "Redisson",
                            "metricCategory": "redis-pool",
                            "applicationId": 1645,
                            "instanceId": 2746,
                        },
                    ]
                }
            }

            envelope = self.adapter.build_deployment_inventory_pack(context, source_mode="live")
        finally:
            self.adapter.application.business_overview = orig_business_overview
            self.adapter.graph.query_overview = orig_query_overview
            self.adapter.instance.list_instances = orig_list_instances
            self.adapter.connection.list_pools = orig_list_pools

        data = envelope.to_dict()
        payload = data["payload"]
        self.assertEqual(envelope.pack_type, "deployment_inventory_pack")
        self.assertEqual(payload["biz_system"]["id"], 1065)
        self.assertEqual(payload["summary"]["application_count"], 2)
        self.assertEqual(payload["summary"]["host_count"], 3)
        self.assertTrue(payload["diagnostics"]["field_coverage"]["service_name_and_technology_and_host_ip"])
        self.assertTrue(payload["diagnostics"]["field_coverage"]["database_or_redis_and_address_and_used_by_applications"])
        self.assertGreater(len(payload["service_inventory"]), 0)
        self.assertGreater(len(payload["service_host_rows"]), 0)
        self.assertGreater(len(payload["host_inventory"]), 0)
        self.assertGreater(len(payload["component_inventory"]), 0)
        self.assertGreater(len(payload["component_usage_rows"]), 0)
        self.assertGreater(len(payload["page_links"]), 0)
        self.assertGreater(len(payload["metric_semantics"]), 0)
        self.assertIn("component_count", data["meta"]["build_stats"])
        subtypes = {item.get("component_subtype") for item in payload["component_inventory"]}
        self.assertIn("Kingbase", subtypes)
        self.assertIn("Redis", subtypes)
        redis_component = next(item for item in payload["component_inventory"] if item.get("component_subtype") == "Redis")
        self.assertEqual(sorted(redis_component["used_by_applications"]), sorted(["com.nbport.zgb.manage.ManageWebApplication", "com.nbport.zgb.manage.ManageServiceApplication"]))
        service = payload["service_inventory"][0]
        self.assertIn("tech_stack", service)
        self.assertGreater(len(service["host_ips"]), 0)

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
        self.assertEqual(payload["diagnostics"]["mode"], "full")

    def test_build_trace_sql_pack_from_samples(self) -> None:
        context = self.adapter.build_context(biz_system_id=1062, end_time="2026-04-03 12:20", period_minutes=30)
        envelope = self.adapter.build_trace_sql_pack(context, source_mode="sample")
        payload = envelope.to_dict()["payload"]
        self.assertEqual(envelope.pack_type, "trace_sql_pack")
        self.assertIn("sql_summary", payload)
        self.assertIn("sqls", payload)
        self.assertIn("database_spans", payload)

    def test_build_trace_execution_pack_from_samples(self) -> None:
        context = self.adapter.build_context(biz_system_id=1062, end_time="2026-04-03 12:20", period_minutes=30)
        envelope = self.adapter.build_trace_execution_pack(context, source_mode="sample")
        payload = envelope.to_dict()["payload"]
        self.assertEqual(envelope.pack_type, "trace_execution_pack")
        self.assertIn("call_tree_summary", payload)
        self.assertIn("snapshot_summary", payload)
        self.assertIn("exception_summary", payload)
        self.assertIn("pool_summary", payload)

    def test_build_trace_fact_sheet_loads_live_exceptions(self) -> None:
        context = self.adapter.build_context(biz_system_id=1065, end_time="2026-04-03 12:20", period_minutes=30)
        detail = {
            "bizSystemId": 1065,
            "applicationId": 1645,
            "actionId": 16000,
            "traceId": "1716361816",
            "traceGuid": "trace-guid-1",
            "actionGuid": "action-guid-1",
            "requestId": "request-guid-1",
            "timestamp": 1775523101840,
            "status": "404",
            "respTime": 7.716,
            "duration": 7.716,
            "suspectedProblemList": [{"seq": 0, "metricType": "CODE", "metricName": "CasRedirectFilter", "exclusiveTime": 1.0}],
        }
        call_tree = {"data": {"nodeMap": {"action-guid-1_-1": {"metricType": "Code", "metricName": "root", "totalTime": 7.716}}}}
        exceptions = {"data": [{"name": "HTTP ERROR CODE: 404", "msg": "status: 404", "type": "HTTP Error Code", "seq": 0, "highest": True}]}
        orig_detail = self.adapter.trace.trace_detail
        orig_call_tree = self.adapter.trace.call_tree
        orig_exceptions = self.adapter.trace.trace_exceptions
        try:
            self.adapter.trace.trace_detail = lambda **_: detail
            self.adapter.trace.call_tree = lambda **_: call_tree
            self.adapter.trace.trace_exceptions = lambda **_: exceptions
            envelope = self.adapter.build_trace_fact_sheet(
                context,
                source_mode="live",
                trace_ref=TraceRef(
                    biz_system_id=1065,
                    trace_id_numeric="1716361816",
                    query_timestamp="1775523101840",
                    action_guid="action-guid-1",
                ),
            )
        finally:
            self.adapter.trace.trace_detail = orig_detail
            self.adapter.trace.call_tree = orig_call_tree
            self.adapter.trace.trace_exceptions = orig_exceptions
        payload = envelope.to_dict()["payload"]
        self.assertEqual(payload["exception_summary"]["count"], 1)
        self.assertEqual(payload["exception_summary"]["top_exception"]["name"], "HTTP ERROR CODE: 404")

    def test_build_trace_sql_pack_extracts_sqls_from_trace_detail(self) -> None:
        context = self.adapter.build_context(biz_system_id=1065, end_time="2026-04-03 12:20", period_minutes=30)
        detail = {
            "bizSystemId": 1065,
            "bizSystemName": "示例系统",
            "applicationId": 1645,
            "applicationName": "示例应用",
            "actionId": 16000,
            "actionName": "SpringController/example (POST)",
            "instanceId": 2746,
            "instanceName": "demo:8888",
            "traceId": "1716361816",
            "traceGuid": "trace-guid-1",
            "actionGuid": "action-guid-1",
            "requestId": "request-guid-1",
            "timestamp": 1775523101840,
            "status": "200",
            "respTime": 2176.739,
            "duration": 2176.739,
            "timeLine": {
                "metricType": "CODE",
                "metricName": "root",
                "exclusiveTime": 1.106,
                "subTimeLines": [
                    {
                        "metricType": "DATABASE",
                        "metricName": "MySQL/10.190.22.21:3306/bpmapp_hg",
                        "instance": "10.190.22.21:3306/bpmapp_hg",
                        "type": "MySQL",
                        "clasz": "com.mysql.cj.jdbc.ClientPreparedStatement",
                        "method": "executeQuery",
                        "exclusiveTime": 0.4,
                        "totalTime": 0.4,
                        "repeatTimes": 1,
                        "sql": "select tbl.ID_VAL from HD_ID_GEN tbl where tbl.ID_NAME='SYNC_COLLECT_LOG' for update",
                        "request": {"name": "SpringController/example (POST)"},
                        "callerInstance": {"name": "demo:8888"},
                        "subTimeLines": [],
                    },
                    {
                        "metricType": "DATABASE",
                        "metricName": "MySQL/10.190.22.21:3306/bpmapp_hg",
                        "instance": "10.190.22.21:3306/bpmapp_hg",
                        "type": "MySQL",
                        "clasz": "com.mysql.cj.jdbc.ClientPreparedStatement",
                        "method": "executeQuery",
                        "exclusiveTime": 718.263,
                        "totalTime": 718.263,
                        "repeatTimes": 1,
                        "sql": "select contractin0_.ID as id1_138_ from LAS_CONTRACT_INFO contractin0_",
                        "request": {"name": "SpringController/example (POST)"},
                        "callerInstance": {"name": "demo:8888"},
                        "subTimeLines": [],
                    },
                ],
            },
            "databaseSqlGroups": [
                {
                    "averageTime": 0.4,
                    "count": 1,
                    "errorCount": 0,
                    "sql": "select tbl.ID_VAL from HD_ID_GEN tbl where tbl.ID_NAME='SYNC_COLLECT_LOG' for update",
                    "totalTime": 0.4,
                },
                {
                    "averageTime": 718.193,
                    "count": 3,
                    "errorCount": 0,
                    "sql": "select contractin0_.ID as id1_138_ from LAS_CONTRACT_INFO contractin0_",
                    "totalTime": 2154.58,
                },
            ],
        }
        original_trace_detail = self.adapter.trace.trace_detail
        original_call_tree = self.adapter.trace.call_tree
        try:
            self.adapter.trace.trace_detail = lambda **_: detail
            self.adapter.trace.call_tree = lambda **_: {"data": {"nodeMap": {}}}
            envelope = self.adapter.build_trace_sql_pack(
                context,
                source_mode="live",
                trace_ref=TraceRef(
                    biz_system_id=1065,
                    trace_id_numeric="1716361816",
                    query_timestamp="1775523101840",
                    action_guid="action-guid-1",
                ),
            )
        finally:
            self.adapter.trace.trace_detail = original_trace_detail
            self.adapter.trace.call_tree = original_call_tree

        payload = envelope.to_dict()["payload"]
        self.assertEqual(envelope.pack_type, "trace_sql_pack")
        self.assertEqual(payload["sql_summary"]["sql_count"], 2)
        self.assertEqual(payload["sql_summary"]["database_span_count"], 2)
        self.assertEqual(payload["sqls"][0]["database_span_summary"]["span_count"], 1)
        self.assertIn("sql_fingerprint", payload["sqls"][0])
        self.assertEqual(payload["database_spans"][0]["metric_name"], "MySQL/10.190.22.21:3306/bpmapp_hg")

    def test_build_trace_sql_pack_uses_call_tree_sql_fallback(self) -> None:
        context = self.adapter.build_context(biz_system_id=1065, end_time="2026-04-03 12:20", period_minutes=30)
        detail = {
            "bizSystemId": 1065,
            "applicationId": 1645,
            "actionId": 16000,
            "traceId": "1716361816",
            "traceGuid": "trace-guid-1",
            "actionGuid": "action-guid-1",
            "requestId": "request-guid-1",
            "timestamp": 1775523101840,
            "status": "200",
            "respTime": 2043.972,
            "duration": 2043.972,
            "timeLine": {"metricType": "CODE", "metricName": "root", "subTimeLines": []},
        }
        call_tree = {
            "data": {
                "nodeMap": {
                    "action-guid-1_1017": {
                        "metricType": "Database",
                        "metricName": "MySQL/10.190.22.21:3306/bpmapp_hg",
                        "clazz": "com.fr.third.org.apache.commons.dbcp.DelegatingStatement",
                        "method": "executeQuery",
                        "totalTime": 0.231,
                        "exclTime": 0.231,
                        "execCount": 1,
                        "seq": 1017,
                        "param": {"instance": "10.190.22.21:3306/bpmapp_hg", "vendor": "MySQL", "operation": "select 1"},
                        "sql": "select 1",
                    }
                }
            }
        }
        orig_detail = self.adapter.trace.trace_detail
        orig_call_tree = self.adapter.trace.call_tree
        try:
            self.adapter.trace.trace_detail = lambda **_: detail
            self.adapter.trace.call_tree = lambda **_: call_tree
            envelope = self.adapter.build_trace_sql_pack(
                context,
                source_mode="live",
                trace_ref=TraceRef(
                    biz_system_id=1065,
                    trace_id_numeric="1716361816",
                    query_timestamp="1775523101840",
                    action_guid="action-guid-1",
                ),
            )
        finally:
            self.adapter.trace.trace_detail = orig_detail
            self.adapter.trace.call_tree = orig_call_tree
        payload = envelope.to_dict()["payload"]
        self.assertEqual(payload["sql_summary"]["sql_count"], 1)
        self.assertEqual(payload["sqls"][0]["sql"], "select 1")
        self.assertEqual(payload["database_spans"][0]["source"], "call_tree")

    def test_build_trace_execution_pack_combines_trace_sources(self) -> None:
        context = self.adapter.build_context(biz_system_id=1065, end_time="2026-04-03 12:20", period_minutes=30)
        detail = {
            "bizSystemId": 1065,
            "applicationId": 1645,
            "actionId": 16000,
            "traceId": "1716361816",
            "traceGuid": "trace-guid-1",
            "actionGuid": "action-guid-1",
            "requestId": "request-guid-1",
            "timestamp": 1775523101840,
            "status": "500",
            "respTime": 2176.739,
            "duration": 2176.739,
            "suspectedProblemList": [{"seq": 1017, "metricType": "DATABASE", "metricName": "MySQL/10.190.22.21:3306/bpmapp_hg", "exclusiveTime": 718.263}],
            "timeLine": {
                "metricType": "CODE",
                "metricName": "root",
                "subTimeLines": [
                    {
                        "metricType": "POOL",
                        "metricName": "10.190.22.20:6379/1/Redis-71302",
                        "poolActiveCount": 0,
                        "poolWaitCount": 0,
                        "poolEndTime": 1775523101840,
                        "totalTime": 0.1,
                        "subTimeLines": [],
                    }
                ],
            },
        }
        call_tree = {
            "data": {
                "nodeMap": {
                    "action-guid-1_-1": {"metricType": "Code", "metricName": "root", "totalTime": 2176.739, "threadName": "http-nio-8888-exec-1"},
                    "action-guid-1_1017": {
                        "metricType": "Database",
                        "metricName": "MySQL/10.190.22.21:3306/bpmapp_hg",
                        "clazz": "com.fr.third.org.apache.commons.dbcp.DelegatingStatement",
                        "method": "executeQuery",
                        "totalTime": 718.263,
                        "exclTime": 718.263,
                        "execCount": 1,
                        "seq": 1017,
                        "param": {"instance": "10.190.22.21:3306/bpmapp_hg", "vendor": "MySQL", "operation": "select 1"},
                        "sql": "select 1",
                    },
                },
                "nodeTableList": [{"fullName": "com.fr.third.org.apache.commons.dbcp.DelegatingStatement.executeQuery", "count": 1, "exclTime": 718.263, "avgExclTime": 718.263, "maxExclTime": 718.263, "timeRatio": 0.33}],
            }
        }
        exceptions = {"data": [{"name": "HTTP ERROR CODE: 500", "msg": "status: 500", "type": "HTTP Error Code", "seq": 0, "highest": True}]}
        snapshot = {"data": [{"statusCode": 500, "threadName": "http-nio-8888-exec-1", "threadCount": 1, "clientIp": "10.85.100.48", "url": "http://example/tx", "duration": 2176.739, "exclusiveTime": 2174.644, "networkTotal": 0.0, "errorNames": ["HTTP ERROR CODE: 500"], "exceptions": [{"name": "HTTP ERROR CODE: 500"}], "requestHeader": {"User-Agent": "Java/1.8"}}]}
        pool_info = {"data": {"metricCategory": "10.190.22.20:6379/1/Redis-71302", "framework": "Redisson", "databaseType": "Redis", "currentUsed": 0, "currentIdle": 0, "pools": [{"waitCount": 0}]}}
        orig_detail = self.adapter.trace.trace_detail
        orig_call_tree = self.adapter.trace.call_tree
        orig_exceptions = self.adapter.trace.trace_exceptions
        orig_snapshot = self.adapter.trace.snapshot_time_info
        orig_pool = self.adapter.trace.pool_info
        try:
            self.adapter.trace.trace_detail = lambda **_: detail
            self.adapter.trace.call_tree = lambda **_: call_tree
            self.adapter.trace.trace_exceptions = lambda **_: exceptions
            self.adapter.trace.snapshot_time_info = lambda **_: snapshot
            self.adapter.trace.pool_info = lambda **_: pool_info
            envelope = self.adapter.build_trace_execution_pack(
                context,
                source_mode="live",
                trace_ref=TraceRef(
                    biz_system_id=1065,
                    trace_id_numeric="1716361816",
                    query_timestamp="1775523101840",
                    action_guid="action-guid-1",
                ),
            )
        finally:
            self.adapter.trace.trace_detail = orig_detail
            self.adapter.trace.call_tree = orig_call_tree
            self.adapter.trace.trace_exceptions = orig_exceptions
            self.adapter.trace.snapshot_time_info = orig_snapshot
            self.adapter.trace.pool_info = orig_pool
        payload = envelope.to_dict()["payload"]
        self.assertEqual(envelope.pack_type, "trace_execution_pack")
        self.assertEqual(payload["exception_summary"]["count"], 1)
        self.assertEqual(payload["snapshot_summary"]["status_code"], 500)
        self.assertEqual(payload["pool_summary"]["pool_count"], 1)
        self.assertGreater(len(payload["call_tree_hotspots"]["top_nodes"]), 0)
        self.assertGreater(len(payload["database_spans"]), 0)

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
        self.assertIn("deep_dive_action_ids", payload["diagnostics"])

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
        self.assertIn(payload["comparison_baseline"]["comparison_mode"], {"summary", "full"})
        self.assertEqual(payload["comparison_baseline"]["history_source"], "previous_window_plus_knowledge")
        self.assertGreater(len(payload["objects"]), 0)

    def test_build_session_uses_shards_for_long_window(self) -> None:
        context = self.adapter.build_context(biz_system_id=1065, end_time="2026-04-03 12:20", period_minutes=90 * 24 * 60)
        session = BuildSession(context=context, source_mode="sample")
        self.assertEqual(session.time_strategy.mode, "auto_sharded_summary")
        self.assertEqual(session.time_strategy.comparison_mode, "summary")
        self.assertEqual(session.time_strategy.short_window_minutes, 30 * 24 * 60)
        self.assertGreater(session.time_strategy.shard_count, 1)

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
        self.assertIn("url_status", payload["screenshot_cards"][0])
        self.assertIn("direct_url", payload["screenshot_cards"][0])
        self.assertIn("fallback_url", payload["screenshot_cards"][0])
        self.assertIn("navigation_path", payload["screenshot_cards"][0])
        self.assertIn("url_source", payload["screenshot_cards"][0])
        self.assertIn("writer_summary", payload["screenshot_cards"][0])

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
