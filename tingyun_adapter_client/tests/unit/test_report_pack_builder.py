from __future__ import annotations

import unittest

from tingyun_adapter_client.report_pack_builder import (
    _action_identity,
    _build_screenshot_rows,
    _parse_user_time,
)


class ReportPackBuilderTests(unittest.TestCase):
    def test_parse_user_time_expands_date_only_range(self) -> None:
        start = _parse_user_time("2025-12-20", end_of_day=False)
        end = _parse_user_time("2026-03-31", end_of_day=True)
        self.assertEqual(start.strftime("%Y-%m-%d %H:%M"), "2025-12-20 00:00")
        self.assertEqual(end.strftime("%Y-%m-%d %H:%M"), "2026-03-31 23:59")

    def test_action_identity_marks_naming_conflict_when_trace_uri_disagrees(self) -> None:
        action = {
            "id": 13161,
            "application_id": 1645,
            "name": "SpringController/ProductIndexController.afterPropertiesSet",
        }
        identity = _action_identity(action, "/grcv5/serverapi/v1/zg-tasks/getTaskForUias")
        self.assertEqual(identity["naming_consistency"], "conflict")
        self.assertTrue(identity["naming_review_required"])
        self.assertEqual(identity["naming_review_reason"], "action_name_uri_mismatch")

    def test_build_screenshot_rows_backfills_link_quality_from_page_links(self) -> None:
        payload = {
            "screenshot_cards": [
                {
                    "figure_id": "FIG-01",
                    "title": "上传接口截图建议",
                    "page_type": "action_overview",
                    "url": "https://console.example.com",
                    "recommended_capture": ["错误指标"],
                    "recommended_annotations": ["圈出100%失败"],
                    "usage_in_report": "接口章节取证",
                    "priority": "high",
                    "target_ref": {
                        "kind": "action",
                        "application_id": 1645,
                        "action_id": 19684,
                    },
                }
            ],
            "page_links": [
                {
                    "page_type": "action_overview",
                    "url": "https://console.example.com",
                    "url_status": "navigation_only",
                    "direct_url": None,
                    "fallback_url": "https://console.example.com",
                    "navigation_path": ["应用", "1645", "事务与服务接口", "19684"],
                    "url_source": "fallback_root_navigation",
                    "target_ref": {
                        "kind": "action",
                        "application_id": 1645,
                        "action_id": 19684,
                    },
                }
            ],
        }
        catalog = {
            "actions": {
                (1645, 19684): {
                    "display_name": "上传接口 upload",
                    "object_type": "action",
                }
            }
        }
        rows = _build_screenshot_rows(payload, catalog)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["section"], "interface")
        self.assertEqual(rows[0]["object_name"], "上传接口 upload")
        self.assertEqual(rows[0]["url_status"], "navigation_only")
        self.assertEqual(rows[0]["fallback_url"], "https://console.example.com")
        self.assertEqual(rows[0]["navigation_path"], "应用 > 1645 > 事务与服务接口 > 19684")


if __name__ == "__main__":
    unittest.main()
