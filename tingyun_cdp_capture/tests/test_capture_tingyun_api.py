import unittest

from tingyun_cdp_capture.capture_tingyun_api import (
    PageContextCandidate,
    PageContextSummary,
    RawLogCatalog,
    infer_purpose,
)


class PageContextTests(unittest.TestCase):
    def test_summary_keeps_latest_non_empty_and_candidates(self) -> None:
        summary = PageContextSummary()
        summary.observe(
            PageContextCandidate(
                captured_page_url="http://console/applications/1",
                document_url="http://console/applications/1",
                request_url="http://console/server-api/demo",
                request_method="POST",
                request_timestamp="2026-04-07T10:00:00+08:00",
                tab_target_id="tab-1",
            ),
            max_candidates=3,
        )
        summary.observe(
            PageContextCandidate(
                captured_page_url=None,
                document_url=None,
                request_url="http://console/server-api/demo",
                request_method="POST",
                request_timestamp="2026-04-07T10:01:00+08:00",
                tab_target_id="tab-1",
            ),
            max_candidates=3,
        )

        payload = summary.to_dict()
        self.assertIsNone(payload["latest"]["captured_page_url"])
        self.assertEqual(payload["latest_non_empty"]["captured_page_url"], "http://console/applications/1")
        self.assertEqual(len(payload["candidates"]), 2)

    def test_raw_log_merge_preserves_existing_context_candidates(self) -> None:
        existing = {
            "page_context_summary": {
                "latest": {"captured_page_url": "http://console/old", "tab_target_id": "tab-1"},
                "latest_non_empty": {"captured_page_url": "http://console/old", "tab_target_id": "tab-1"},
                "candidates": [{"captured_page_url": "http://console/old", "tab_target_id": "tab-1"}],
            }
        }
        incoming = {
            "page_context": {
                "captured_page_url": "http://console/new",
                "request_url": "http://console/server-api/demo",
                "request_method": "POST",
                "request_timestamp": "2026-04-07T10:02:00+08:00",
                "tab_target_id": "tab-1",
            },
            "capture": {},
        }

        RawLogCatalog._merge_page_context(existing, incoming)

        summary = incoming["page_context_summary"]
        self.assertEqual(summary["latest"]["captured_page_url"], "http://console/new")
        self.assertEqual(summary["latest_non_empty"]["captured_page_url"], "http://console/new")
        self.assertEqual(
            [item["captured_page_url"] for item in summary["candidates"]],
            ["http://console/new", "http://console/old"],
        )


class DownloadVariantTests(unittest.TestCase):
    def test_infer_variant_label_marks_download_file_query(self) -> None:
        label = RawLogCatalog.infer_variant_label(
            {
                "query_example": {"downloadFile": "true", "bizSystemId": "1065"},
                "query_metadata": {"keys": ["bizSystemId", "downloadFile"]},
                "metric": None,
                "body_metadata": {},
            }
        )

        self.assertEqual(label, "download_file")

    def test_infer_purpose_marks_download_file_query_as_export(self) -> None:
        purpose, basis = infer_purpose(
            "webaction/list/actionList",
            {"downloadFile": "true", "bizSystemId": "1065"},
            None,
        )

        self.assertIn("export/download", purpose)
        self.assertIn("query.downloadFile=true", basis)


if __name__ == "__main__":
    unittest.main()
