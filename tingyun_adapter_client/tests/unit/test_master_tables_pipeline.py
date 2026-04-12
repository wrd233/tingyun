from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from tingyun_adapter_client.master_tables_pipeline import (
    build_export_registry,
    initialize_deep_dive_bundle,
    materialize_deep_dive_from_source,
    materialize_master_tables,
    prepare_master_table_inputs,
)


class MasterTablesPipelineTests(unittest.TestCase):
    def _write_csv(self, path: Path, header: list[str], rows: list[list[str]]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(header)
            writer.writerows(rows)

    def _write_json(self, path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def test_build_export_registry_supports_structured_sql_directories(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            diagnostics = Path(tmpdir) / "diagnostics"
            raw = diagnostics / "00_raw_exports"
            self._write_csv(
                raw / "application" / "graph_overview_export_application__application_overview-demo.csv",
                ["健康度", "应用名称", "Apdex", "评分", "responseP50", "吞吐率 (/s)", "请求数", "错误率(%)", "错误次数", "慢次数"],
                [["正常", "demo-app", "0.99", "100", "12", "1.2", "120", "0.5", "1", "3"]],
            )
            self._write_json(
                raw / "application" / "graph_overview_export_application__summary.json",
                {"case_key": "graph_overview_export_application", "selected_export": {"export_key": "graph_overview_export"}},
            )
            sql_dir = raw / "sql_database" / "db_main"
            sql_dir.mkdir(parents=True, exist_ok=True)
            (sql_dir / "component_analysis_export_database__SQL_.csv").write_text(
                "SQL文本,平均响应时间(ms),响应总时间,执行次数,错误次数,慢次数\nSELECT * FROM orders,1200,24000,20,0,5\n",
                encoding="utf-8",
            )
            self._write_json(sql_dir / "summary.json", {"case_key": "component_analysis_export_database", "source_db_name": "main-db"})

            registry = build_export_registry(diagnostics, system_key="bizsystem_1065", batch_key="2026-04-12-check")
            self.assertEqual(len(registry), 2)
            sql_entry = next(item for item in registry if item["object_family"] == "sql_database")
            self.assertEqual(sql_entry["source_db_key"], "db_main")
            self.assertEqual(sql_entry["source_db_name"], "main-db")

    def test_prepare_and_materialize_pipeline_outputs_expected_directories(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            diagnostics = Path(tmpdir) / "diagnostics"
            raw = diagnostics / "00_raw_exports"
            self._write_csv(
                raw / "application" / "graph_overview_export_application__application_overview-demo.csv",
                ["健康度", "应用名称", "Apdex", "评分", "responseP50", "吞吐率 (/s)", "请求数", "错误率(%)", "错误次数", "慢次数"],
                [["警告", "demo-app", "0.80", "88", "32", "1.2", "120", "2.5", "4", "30"]],
            )
            self._write_json(
                raw / "application" / "graph_overview_export_application__summary.json",
                {"case_key": "graph_overview_export_application", "selected_export": {"export_key": "graph_overview_export"}},
            )
            self._write_csv(
                raw / "action" / "action_list_export__actionList-demo.csv",
                ["事务别名", "名称", "平均响应时间(ms)", "总耗时(ms)", "耗时百分比(%)", "请求数", "吞吐率(tps)", "错误率(%)", "错误数", "慢次数", "应用"],
                [["alias/demo", "alias/demo", "2400", "240000", "15", "100", "1.2", "2.5", "6", "20", "demo-app"]],
            )
            self._write_json(
                raw / "action" / "action_list_export__summary.json",
                {"case_key": "action_list_export", "selected_export": {"export_key": "action_list_export"}},
            )
            self._write_csv(
                raw / "request" / "graph_overview_export_request__request_overview-demo.csv",
                ["事务名称", "应用名称", "Apdex", "响应时间中位数(ms)", "响应时间 P75 (ms)", "响应时间 P95 (ms)", "响应时间 P99 (ms)", "平均请求时间", "吞吐率 (/s)", "请求数", "错误率(%)", "错误次数", "慢次数", "异常次数", "请求类型"],
                [["alias/demo", "demo-app", "0.70", "100", "200", "500", "900", "2400", "1.2", "100", "2.5", "6", "20", "3", "Web请求"]],
            )
            self._write_json(
                raw / "request" / "graph_overview_export_request__summary.json",
                {"case_key": "graph_overview_export_request", "selected_export": {"export_key": "graph_overview_export"}},
            )
            self._write_csv(
                raw / "interface" / "interface_list_export__interfaceList-demo.csv",
                ["名称", "应用", "总耗时(ms)", "平均响应时间(ms)", "请求数", "吞吐率(tps)", "错误率(%)", "错误数"],
                [["demo/interface", "demo-app", "120000", "1500", "100", "1.2", "2.0", "5"]],
            )
            self._write_json(
                raw / "interface" / "interface_list_export__summary.json",
                {"case_key": "interface_list_export", "selected_export": {"export_key": "interface_list_export"}},
            )
            sql_dir = raw / "sql_database" / "db_main"
            self._write_csv(
                sql_dir / "component_analysis_export_database__SQL_.csv",
                ["SQL文本", "平均响应时间(ms)", "响应总时间", "执行次数", "错误次数", "慢次数"],
                [["SELECT * FROM orders", "1800", "36000", "20", "0", "5"]],
            )
            self._write_json(
                sql_dir / "summary.json",
                {"case_key": "component_analysis_export_database", "selected_export": {"export_key": "component_analysis_export"}, "source_db_name": "main-db"},
            )
            self._write_csv(
                raw / "nosql" / "redis_primary" / "component_analysis_export_nosql__SQL_.csv",
                ["SQL文本", "平均响应时间(ms)", "响应总时间", "执行次数", "错误次数", "慢次数"],
                [["GET cache:orders", "900", "18000", "20", "0", "3"]],
            )
            self._write_json(
                raw / "nosql" / "redis_primary" / "summary.json",
                {
                    "case_key": "component_analysis_export_nosql",
                    "selected_export": {"export_key": "component_analysis_export"},
                    "source_component_key": "redis_primary",
                    "source_component_name": "10.190.22.20:6379/1",
                    "source_component_subtype": "Redis",
                },
            )

            prepare_summary = prepare_master_table_inputs(
                diagnostics,
                system_key="bizsystem_1065",
                batch_key="2026-04-12-check",
            )
            self.assertIn("request_prepared.csv", prepare_summary["prepared_tables"])
            self.assertEqual(prepare_summary["row_counts"]["sql"], 1)

            materialize_summary = materialize_master_tables(
                diagnostics,
                system_key="bizsystem_1065",
                batch_key="2026-04-12-check",
            )
            self.assertIn("request_master.csv", materialize_summary["outputs"])
            request_master = diagnostics / "02_master_tables" / "request_master.csv"
            self.assertTrue(request_master.exists())
            content = request_master.read_text(encoding="utf-8")
            self.assertIn("followup_status", content)
            self.assertIn("待确认", content)
            self.assertIn("selected_for_deep_dive", content)
            self.assertIn("deep_dive_status", content)
            sql_evidence = diagnostics / "03_evidence_indexes" / "sql_evidence_index.csv"
            self.assertTrue(sql_evidence.exists())
            nosql_prepared = diagnostics / "01_prepared_tables" / "nosql_prepared.csv"
            self.assertIn("source_component_key", nosql_prepared.read_text(encoding="utf-8"))
            deep_dive_registry = diagnostics / "04_deep_dive" / "deep_dive_registry.csv"
            self.assertTrue(deep_dive_registry.exists())

    def test_prepare_and_materialize_pipeline_synthesizes_interface_cluster_from_request_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            diagnostics = Path(tmpdir) / "diagnostics"
            raw = diagnostics / "00_raw_exports"
            self._write_csv(
                raw / "action" / "action_list_export__actionList-demo.csv",
                ["事务别名", "名称", "平均响应时间(ms)", "总耗时(ms)", "耗时百分比(%)", "请求数", "吞吐率(tps)", "错误率(%)", "错误数", "慢次数", "应用"],
                [["alias/demo", "URI/demo/request", "2400", "240000", "15", "100", "1.2", "2.5", "6", "20", "demo-app"]],
            )
            self._write_json(
                raw / "action" / "action_list_export__summary.json",
                {"case_key": "action_list_export", "selected_export": {"export_key": "action_list_export"}},
            )
            self._write_csv(
                raw / "request" / "graph_overview_export_request__request_overview-demo.csv",
                ["事务名称", "应用名称", "Apdex", "响应时间中位数(ms)", "响应时间 P75 (ms)", "响应时间 P95 (ms)", "响应时间 P99 (ms)", "平均请求时间", "吞吐率 (/s)", "请求数", "错误率(%)", "错误次数", "慢次数", "异常次数", "请求类型"],
                [["URI/demo/request", "demo-app", "0.70", "100", "200", "500", "900", "2400", "1.2", "100", "2.5", "6", "20", "3", "Web请求"]],
            )
            self._write_json(
                raw / "request" / "graph_overview_export_request__summary.json",
                {"case_key": "graph_overview_export_request", "selected_export": {"export_key": "graph_overview_export"}},
            )

            prepare_summary = prepare_master_table_inputs(
                diagnostics,
                system_key="bizsystem_1065",
                batch_key="2026-04-12-check",
            )
            self.assertEqual(prepare_summary["row_counts"]["interface_cluster"], 1)
            self.assertTrue(any("synthesized from request_prepared" in item for item in prepare_summary["warnings"]))

            materialize_summary = materialize_master_tables(
                diagnostics,
                system_key="bizsystem_1065",
                batch_key="2026-04-12-check",
            )
            self.assertIn("interface_cluster_evidence_index.csv", materialize_summary["outputs"])
            interface_master = (diagnostics / "02_master_tables" / "interface_cluster_master.csv").read_text(encoding="utf-8")
            self.assertIn("URI/demo/request", interface_master)
            self.assertIn("related_request_count", interface_master)
            interface_evidence = diagnostics / "03_evidence_indexes" / "interface_cluster_evidence_index.csv"
            self.assertTrue(interface_evidence.exists())

    def test_initialize_deep_dive_bundle_creates_registry_and_bundle_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            diagnostics = Path(tmpdir) / "diagnostics"
            manifest = initialize_deep_dive_bundle(
                diagnostics,
                system_key="bizsystem_1065",
                batch_key="2026-04-12-check",
                object_id="db_main:abc123",
                object_type="sql",
                source_master_table="sql_master.csv",
                deep_dive_id="sql-dd-001",
                deep_dive_kind="sql_bottleneck",
                deep_dive_scope="core_path",
                pack_source="sql_fact_sheet;database_component_pack",
                summary="首轮补 trace 与组件上下文。",
            )
            bundle_dir = Path(manifest["bundle_path"])
            self.assertTrue((bundle_dir / "summary.json").exists())
            self.assertTrue((bundle_dir / "evidence_index.csv").exists())
            self.assertTrue((bundle_dir / "page_links.json").exists())
            registry = (diagnostics / "04_deep_dive" / "deep_dive_registry.csv").read_text(encoding="utf-8")
            self.assertIn("sql-dd-001", registry)
            self.assertIn("sql_master.csv", registry)

    def test_materialize_deep_dive_from_source_updates_registry_master_and_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            diagnostics = Path(tmpdir) / "diagnostics"
            master_root = diagnostics / "02_master_tables"
            evidence_root = diagnostics / "03_evidence_indexes"
            master_root.mkdir(parents=True, exist_ok=True)
            evidence_root.mkdir(parents=True, exist_ok=True)

            self._write_csv(
                master_root / "request_master.csv",
                [
                    "object_id",
                    "object_type",
                    "system_key",
                    "batch_key",
                    "canonical_name",
                    "display_name",
                    "alias_name",
                    "application_name",
                    "request_type",
                    "interface_cluster_key",
                    "avg_rt_ms",
                    "p50_ms",
                    "p75_ms",
                    "p95_ms",
                    "p99_ms",
                    "apdex",
                    "total_time_ms",
                    "time_share_pct",
                    "request_count",
                    "tps",
                    "error_rate_pct",
                    "error_count",
                    "slow_count",
                    "exception_count",
                    "bucket_hits",
                    "screening_score",
                    "screening_reason",
                    "selected_for_master",
                    "selected_for_deep_dive",
                    "followup_status",
                    "followup_note",
                    "deep_dive_count",
                    "deep_dive_status",
                    "latest_deep_dive_id",
                    "latest_deep_dive_at",
                    "evidence_status",
                    "related_sql_count",
                    "related_object_ids",
                    "report_group_hint",
                    "writing_note",
                ],
                [[
                    "req-1", "request", "bizsystem_1065", "2026-04-12-check", "URI/demo/request", "URI/demo/request", "", "demo-app",
                    "Web请求", "cluster-1", "2400", "100", "200", "500", "900", "0.7", "240000", "15", "100", "1.2", "2.5", "6", "20", "3",
                    "high_avg_rt", "3", "平均响应时间命中筛选阈值", "true", "true", "待确认", "", "0", "not_started", "", "", "待补证据", "0", "", "", ""
                ]],
            )
            self._write_csv(
                master_root / "sql_master.csv",
                [
                    "object_id",
                    "object_type",
                    "system_key",
                    "batch_key",
                    "source_db_key",
                    "source_db_name",
                    "sql_group_key",
                    "representative_sql",
                    "query_object_hint",
                    "avg_rt_ms",
                    "total_time_ms",
                    "qps",
                    "exec_count",
                    "error_count",
                    "slow_count",
                    "bucket_hits",
                    "screening_score",
                    "screening_reason",
                    "selected_by_global_rank",
                    "selected_by_db_rank",
                    "selected_for_master",
                    "selected_for_deep_dive",
                    "followup_status",
                    "followup_note",
                    "deep_dive_count",
                    "deep_dive_status",
                    "latest_deep_dive_id",
                    "latest_deep_dive_at",
                    "evidence_status",
                    "related_request_ids",
                    "related_object_ids",
                    "report_group_hint",
                    "writing_note",
                ],
                [[
                    "sql-1", "sql", "bizsystem_1065", "2026-04-12-check", "db_main", "main-db", "sql-group-1", "SELECT * FROM orders", "orders",
                    "1800", "36000", "1.2", "20", "0", "5", "high_avg_rt", "3", "平均响应时间命中筛选阈值", "true", "true", "true", "true",
                    "待确认", "", "0", "not_started", "", "", "待补证据", "", "", "", ""
                ]],
            )
            self._write_csv(
                master_root / "interface_cluster_master.csv",
                [
                    "object_id",
                    "object_type",
                    "system_key",
                    "batch_key",
                    "cluster_name",
                    "application_name",
                    "total_time_ms",
                    "avg_rt_ms",
                    "request_count",
                    "tps",
                    "error_rate_pct",
                    "error_count",
                    "related_request_count",
                    "related_request_ids",
                    "bucket_hits",
                    "screening_score",
                    "screening_reason",
                    "selected_for_master",
                    "selected_for_deep_dive",
                    "followup_status",
                    "followup_note",
                    "deep_dive_count",
                    "deep_dive_status",
                    "latest_deep_dive_id",
                    "latest_deep_dive_at",
                    "evidence_status",
                    "related_object_ids",
                    "report_group_hint",
                    "writing_note",
                ],
                [[
                    "if-1", "interface_cluster", "bizsystem_1065", "2026-04-12-check", "URI/demo/request", "demo-app",
                    "240000", "2400", "100", "1.2", "2.5", "6", "1", "req-1", "high_avg_rt", "2", "平均响应时间命中筛选阈值",
                    "true", "true", "待确认", "", "0", "not_started", "", "", "待补证据", "req-1", "", ""
                ]],
            )
            self._write_csv(
                evidence_root / "request_evidence_index.csv",
                ["object_id", "object_type", "latest_deep_dive_id", "deep_dive_status", "followup_status", "evidence_status", "page_link_count", "trace_link_count", "screenshot_hint_status", "related_object_ids", "writing_note"],
                [["req-1", "request", "", "", "待确认", "待补证据", "", "", "待补充", "", ""]],
            )
            self._write_csv(
                evidence_root / "interface_cluster_evidence_index.csv",
                ["object_id", "object_type", "latest_deep_dive_id", "deep_dive_status", "followup_status", "evidence_status", "page_link_count", "trace_link_count", "screenshot_hint_status", "related_request_ids", "writing_note"],
                [["if-1", "interface_cluster", "", "", "待确认", "待补证据", "", "", "待补充", "req-1", ""]],
            )
            self._write_csv(
                evidence_root / "sql_evidence_index.csv",
                ["object_id", "object_type", "latest_deep_dive_id", "deep_dive_status", "followup_status", "evidence_status", "page_link_count", "trace_link_count", "screenshot_hint_status", "related_request_ids", "writing_note"],
                [["sql-1", "sql", "", "", "待确认", "待补证据", "", "", "待补充", "", ""]],
            )

            source_json = diagnostics / "deep_dive_source.json"
            self._write_json(
                source_json,
                {
                    "deep_dive_targets": [
                        {
                            "candidate_key": "trace:1",
                            "candidate_type": "trace",
                            "target_ref": {"kind": "trace", "trace_id_numeric": "1"},
                            "display_name": "1",
                            "selection_reason": "需要继续查看 request 代表 trace。",
                            "source_packs": ["trace_case_pack"],
                            "recommended_next_packs": ["trace_fact_sheet"],
                            "impact_scope": "core_path",
                            "evidence_strength": "strong",
                        },
                        {
                            "candidate_key": "sql:1",
                            "candidate_type": "sql",
                            "target_ref": {"kind": "sql", "component_name": "db_main", "op_name": "SELECT * FROM orders"},
                            "display_name": "sql:1",
                            "selection_reason": "需要继续查看 SQL 细节。",
                            "source_packs": ["slow_sql_pack"],
                            "recommended_next_packs": ["sql_fact_sheet", "database_component_pack"],
                            "impact_scope": "cross_object",
                            "evidence_strength": "strong",
                        },
                        {
                            "candidate_key": "interface:1",
                            "object_type": "interface_cluster",
                            "source_master_table": "interface_cluster_master.csv",
                            "deep_dive_kind": "interface_cluster_context",
                            "deep_dive_scope": "local",
                            "display_name": "URI/demo/request",
                            "selection_reason": "需要继续查看接口簇上下文。",
                            "pack_source": "action_fact_sheet",
                            "master_match_hints": {"cluster_name": "URI/demo/request", "display_name": "URI/demo/request"},
                        },
                    ],
                    "selected_target_expansions": [
                        {
                            "candidate_key": "trace:1",
                            "candidate_type": "trace",
                            "pack_type": "trace_fact_sheet",
                            "payload": {
                                "detail_summary": {"actionName": "URI/demo/request"},
                                "page_links": [{"url": "http://example/request/1", "page_type": "trace_detail"}],
                                "screenshot_hints": [{"purpose": "说明 request trace", "url": "http://example/request/1"}],
                                "evidence_linkage": {"related_traces": [{"trace_id_numeric": "1", "actionName": "URI/demo/request"}]},
                            },
                            "evidence": [{"id": "trace-1", "source_api": "trace/detail", "source_path": "/trace/detail"}],
                        },
                        {
                            "candidate_key": "sql:1",
                            "candidate_type": "sql",
                            "pack_type": "sql_fact_sheet",
                            "payload": {
                                "selector": {"opName": "SELECT * FROM orders"},
                                "page_links": [{"url": "http://example/sql/1", "page_type": "sql_detail"}],
                                "screenshot_hints": [{"purpose": "说明 SQL 明细", "url": "http://example/sql/1"}],
                                "evidence_linkage": {"related_traces": [{"trace_id_numeric": "2", "actionName": "URI/demo/request"}]},
                            },
                            "evidence": [{"id": "sql-1", "source_api": "sql/detail", "source_path": "/sql/detail"}],
                        },
                        {
                            "candidate_key": "interface:1",
                            "candidate_type": "interface_cluster",
                            "pack_type": "action_fact_sheet",
                            "payload": {
                                "action": {"name": "URI/demo/request"},
                                "page_links": [{"url": "http://example/interface/1", "page_type": "action_detail"}],
                                "screenshot_hints": [{"purpose": "说明接口簇上下文", "url": "http://example/interface/1"}],
                                "evidence_linkage": {"related_traces": [{"trace_id_numeric": "3", "actionName": "URI/demo/request"}]},
                            },
                            "evidence": [{"id": "if-1", "source_api": "action/detail", "source_path": "/action/detail"}],
                        },
                    ],
                },
            )

            summary = materialize_deep_dive_from_source(
                diagnostics,
                system_key="bizsystem_1065",
                batch_key="2026-04-12-check",
                source_json=source_json,
            )
            self.assertEqual(summary["materialized_count"], 3)
            registry_path = diagnostics / "04_deep_dive" / "deep_dive_registry.csv"
            registry_text = registry_path.read_text(encoding="utf-8")
            self.assertIn("request_master.csv", registry_text)
            self.assertIn("interface_cluster_master.csv", registry_text)
            self.assertIn("sql_master.csv", registry_text)
            request_master_text = (master_root / "request_master.csv").read_text(encoding="utf-8")
            self.assertIn("deep_dive_count", request_master_text)
            self.assertIn("completed", request_master_text)
            self.assertIn("已挂接deep-dive", request_master_text)
            interface_master_text = (master_root / "interface_cluster_master.csv").read_text(encoding="utf-8")
            self.assertIn("completed", interface_master_text)
            interface_evidence_text = (evidence_root / "interface_cluster_evidence_index.csv").read_text(encoding="utf-8")
            self.assertIn("latest_deep_dive_id", interface_evidence_text)
            self.assertIn("已生成", interface_evidence_text)
            request_evidence_text = (evidence_root / "request_evidence_index.csv").read_text(encoding="utf-8")
            self.assertIn("latest_deep_dive_id", request_evidence_text)
            self.assertIn("已生成", request_evidence_text)


if __name__ == "__main__":
    unittest.main()
