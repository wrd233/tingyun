from __future__ import annotations

import base64
import json
import tempfile
import unittest
from pathlib import Path

from tingyun_adapter.invocation.export_runner import persist_export_artifacts


class ExportRunnerTests(unittest.TestCase):
    def test_persist_export_artifacts_writes_binary_export_and_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            envelope = {
                "payload": {
                    "scope": {"exportKind": "action_list_export"},
                    "selected_export": {
                        "export_key": "action_list_export",
                        "suggested_filename": "actions.xlsx",
                    },
                    "execution": {
                        "status": "executed",
                        "suggested_filename": "actions.xlsx",
                        "content_base64": base64.b64encode(b"demo-bytes").decode("ascii"),
                        "byte_size": 10,
                        "mime_type": "application/octet-stream",
                    },
                }
            }
            result = persist_export_artifacts(envelope, output_dir=tempdir, save_manifest=True)
            output_dir = Path(tempdir)

            export_file = output_dir / "actions.xlsx"
            manifest_file = output_dir / "action_list_export_actions_xlsx_manifest.json"

            self.assertTrue(export_file.exists())
            self.assertEqual(export_file.read_bytes(), b"demo-bytes")
            self.assertTrue(manifest_file.exists())
            self.assertTrue(result["saved_content"])
            self.assertEqual(result["execution_status"], "executed")

    def test_persist_export_artifacts_writes_json_response_when_no_binary_content(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            envelope = {
                "payload": {
                    "scope": {"exportKind": "error_export_task_list"},
                    "selected_export": {
                        "export_key": "error_export_task_list",
                        "suggested_filename": "error_tasks",
                    },
                    "execution": {
                        "status": "executed",
                        "suggested_filename": "error_tasks",
                        "response_json": {"tasks": [{"id": 1}]},
                        "mime_type": "application/json",
                    },
                }
            }
            result = persist_export_artifacts(envelope, output_dir=tempdir, save_manifest=False)
            output_dir = Path(tempdir)

            export_file = output_dir / "error_tasks.json"
            self.assertTrue(export_file.exists())
            self.assertEqual(json.loads(export_file.read_text(encoding="utf-8")), {"tasks": [{"id": 1}]})
            self.assertTrue(result["saved_content"])
            self.assertFalse(result["manifest_saved"])


if __name__ == "__main__":
    unittest.main()
