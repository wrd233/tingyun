from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from tingyun_adapter_client.master_tables_pipeline import (
    build_export_registry,
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
            sql_evidence = diagnostics / "03_evidence_indexes" / "sql_evidence_index.csv"
            self.assertTrue(sql_evidence.exists())
            nosql_prepared = diagnostics / "01_prepared_tables" / "nosql_prepared.csv"
            self.assertIn("source_component_key", nosql_prepared.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
