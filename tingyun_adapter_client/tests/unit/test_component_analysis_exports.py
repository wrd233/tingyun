from __future__ import annotations

import base64
import json
import tempfile
import unittest
from pathlib import Path

from tingyun_adapter_client.component_analysis_exports import export_component_analysis_raw


class _FakeRemoteClient:
    def build_pack(self, pack_type: str, payload: dict) -> dict:
        if pack_type == "database_component_pack":
            return {
                "payload": {
                    "summary": {
                        "component_name": "10.190.22.21:3306",
                        "component_subtype": "MySQL",
                    },
                    "component": {
                        "component_name": "10.190.22.21:3306",
                        "component_subtype": "MySQL",
                    },
                    "evidence": [
                        {
                            "source_api": "Database/list",
                            "response_excerpt": {
                                "componentName": "10.190.22.21:3306",
                                "componentSubtype": "MySQL",
                                "schemas": ["bpmapp_hg"],
                            },
                        }
                    ],
                }
            }
        if pack_type == "nosql_component_pack":
            return {
                "payload": {
                    "summary": {
                        "component_name": "10.190.22.20:6379/1",
                        "component_subtype": "Redis",
                    },
                    "component": {
                        "component_name": "10.190.22.20:6379/1",
                        "component_subtype": "Redis",
                    },
                    "evidence": [
                        {
                            "source_api": "NoSQL/list",
                            "response_excerpt": {
                                "componentName": "10.190.22.20:6379/1",
                                "componentSubtype": "Redis",
                            },
                        }
                    ],
                }
            }
        if pack_type == "data_export_pack":
            export_params = payload.get("exportParams") or {}
            component_type = export_params.get("componentType")
            filename = "component_analysis_export_Database_MySQL.xls" if component_type == "Database" else "component_analysis_export_NoSQL_Redis.xls"
            content = b"SQL\xe6\x96\x87\xe6\x9c\xac,\xe5\xb9\xb3\xe5\x9d\x87\xe5\x93\x8d\xe5\xba\x94\xe6\x97\xb6\xe9\x97\xb4(ms)\nSELECT 1,12\n" if component_type == "Database" else b"SQL\xe6\x96\x87\xe6\x9c\xac,\xe5\xb9\xb3\xe5\x9d\x87\xe5\x93\x8d\xe5\xba\x94\xe6\x97\xb6\xe9\x97\xb4(ms)\nGET cache:key,3\n"
            return {
                "generated_at": "2026-04-12T22:15:00+08:00",
                "context": {"biz_system_id": payload.get("bizSystemId")},
                "payload": {
                    "selected_export": {"export_key": "component_analysis_export"},
                    "execution": {
                        "status": "executed",
                        "mime_type": "application/octet-stream",
                        "suggested_filename": filename,
                        "content_base64": base64.b64encode(content).decode("ascii"),
                    },
                },
            }
        raise AssertionError(f"unexpected pack_type: {pack_type}")


class ComponentAnalysisExportTests(unittest.TestCase):
    def test_export_component_analysis_raw_writes_structured_sql_and_nosql_directories(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            diagnostics = Path(tmpdir) / "diagnostics"
            payload = export_component_analysis_raw(
                _FakeRemoteClient(),  # type: ignore[arg-type]
                diagnostics_dir=diagnostics,
                biz_system_id=1065,
                end_time="2026-04-12 22:15",
                period_minutes=2880,
                source_mode="live",
            )

            self.assertEqual(len(payload["sql_exports"]), 1)
            self.assertEqual(len(payload["nosql_exports"]), 1)

            sql_dir = diagnostics / "00_raw_exports" / "sql_database" / "db_mysql_10_190_22_21_3306"
            nosql_dir = diagnostics / "00_raw_exports" / "nosql" / "nosql_redis_10_190_22_20_6379_1"
            self.assertTrue((sql_dir / "component_analysis_export_database__SQL_.xls").exists())
            self.assertTrue((sql_dir / "summary.json").exists())
            self.assertTrue((nosql_dir / "component_analysis_export_nosql__SQL_.xls").exists())
            self.assertTrue((nosql_dir / "summary.json").exists())

            summary = json.loads((sql_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual(summary["source_db_name"], "10.190.22.21:3306")
            self.assertEqual(summary["schemas"], ["bpmapp_hg"])


if __name__ == "__main__":
    unittest.main()
