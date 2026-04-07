from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tingyun_adapter.config.settings import AdapterSettings
from tingyun_adapter.invocation.sdk import Adapter
from tingyun_adapter.usecases.report_support import make_console_link


class ReportSupportTests(unittest.TestCase):
    def _write_json(self, path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def test_make_console_link_prefers_direct_object_url_from_captured_page_context(self) -> None:
        tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(tempdir.cleanup)
        root = Path(tempdir.name)

        self._write_json(
            root / "index.json",
            {
                "generated_at": "2026-04-07T12:00:00+08:00",
                "total_endpoint_paths": 1,
                "endpoints": [
                    {
                        "relative_path": "webaction/overview",
                        "path": "/server-api/webaction/overview",
                        "count_seen": 1,
                        "methods": ["POST"],
                        "file": "webaction/overview.json",
                        "purposes": {},
                    }
                ],
            },
        )
        self._write_json(
            root / "webaction" / "overview.json",
            {
                "relative_path": "webaction/overview",
                "path": "/server-api/webaction/overview",
                "methods": {
                    "POST": {
                        "sample_requests": [
                            {
                                "seen_at": "2026-04-07T12:02:00+08:00",
                                "query": {},
                                "body": {"bizSystemId": "1059", "applicationId": "1648", "actionId": "20441"},
                                "page_context": {
                                    "captured_page_url": "https://console.example.com/",
                                    "document_url": "https://console.example.com/app/action/20441?ts=1",
                                    "frame_url": "https://console.example.com/frame/action/20441",
                                    "page_title": "Action 20441",
                                    "request_timestamp": "2026-04-07T12:02:00+08:00",
                                },
                            }
                        ],
                        "page_context_summary": {
                            "latest": {
                                "captured_page_url": "https://console.example.com/",
                                "document_url": "https://console.example.com/app/action/20441?ts=1",
                                "frame_url": "https://console.example.com/frame/action/20441",
                                "request_timestamp": "2026-04-07T12:02:00+08:00",
                            },
                            "latest_non_empty": {
                                "captured_page_url": "https://console.example.com/",
                                "document_url": "https://console.example.com/app/action/20441?ts=1",
                                "frame_url": "https://console.example.com/frame/action/20441",
                                "request_timestamp": "2026-04-07T12:02:00+08:00",
                            },
                            "candidates": [
                                {
                                    "captured_page_url": "https://console.example.com/",
                                    "document_url": "https://console.example.com/app/action/20441?ts=1",
                                    "frame_url": "https://console.example.com/frame/action/20441",
                                    "request_timestamp": "2026-04-07T12:02:00+08:00",
                                }
                            ],
                        },
                    }
                },
            },
        )

        adapter = Adapter(
            AdapterSettings(
                captured_api_dir=str(root),
                console_public_base_url="https://console.example.com",
            )
        )
        context = adapter.build_context(biz_system_id=1059, end_time="2026-04-03 12:20", period_minutes=30)

        link = make_console_link(
            adapter,
            context,
            page_type="action_overview",
            label="热点接口详情页",
            why_relevant="test",
            suggested_report_section="3.3",
            navigation_path=["应用", "1648", "事务与服务接口", "20441"],
            target_ref={"kind": "action", "biz_system_id": 1059, "application_id": 1648, "action_id": 20441},
        )

        self.assertEqual(link["url_status"], "direct")
        self.assertEqual(link["url"], "https://console.example.com/app/action/20441?ts=1")
        self.assertEqual(link["direct_url"], "https://console.example.com/app/action/20441?ts=1")
        self.assertEqual(link["fallback_url"], "https://console.example.com")
        self.assertEqual(link["url_source"], "document_url")
        self.assertIn("https://console.example.com/frame/action/20441", link["related_console_urls"])

    def test_make_console_link_marks_navigation_only_when_no_real_url_exists(self) -> None:
        adapter = Adapter(AdapterSettings(console_public_base_url="https://console.example.com"))
        context = adapter.build_context(biz_system_id=1059, end_time="2026-04-03 12:20", period_minutes=30)

        link = make_console_link(
            adapter,
            context,
            page_type="business_system_overview",
            label="业务系统总览页",
            why_relevant="test",
            suggested_report_section="3.1",
            navigation_path=["业务系统", "1059", "总览"],
            target_ref={"kind": "biz_system", "biz_system_id": 1059},
        )

        self.assertEqual(link["url_status"], "navigation_only")
        self.assertIsNone(link["direct_url"])
        self.assertEqual(link["url"], "https://console.example.com")
        self.assertEqual(link["url_source"], "fallback_root_navigation")


if __name__ == "__main__":
    unittest.main()
