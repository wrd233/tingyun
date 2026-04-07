import json
import tempfile
import unittest
from pathlib import Path

from tingyun_adapter.sources.knowledge_repository import KnowledgeRepository


class KnowledgeRepositoryTests(unittest.TestCase):
    def _write_json(self, path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def test_merge_pending_proposals_merges_same_object_and_detects_conflict(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = KnowledgeRepository(tmpdir)
            biz_dir = Path(tmpdir) / "biz_system_1065"
            action_ref = {"kind": "action", "biz_system_id": 1065, "application_id": 1648, "action_id": 31376, "action_type": "TX"}
            self._write_json(
                biz_dir / "action_labels.json",
                {
                    "schema_version": "v1",
                    "biz_system": {"id": 1065, "key": "biz_system_1065"},
                    "file_type": "action_labels",
                    "entries": [
                        {
                            "entry_id": "confirmed:1",
                            "entry_type": "action_label",
                            "object_ref": action_ref,
                            "summary": "人工确认是支撑链路。",
                            "attributes": {"confirmed_labels": ["important_support_path"]},
                            "status": "confirmed",
                            "staleness": "active",
                        }
                    ],
                    "stale_entries": [],
                    "metadata": {"created_at": "2026-04-07T10:00:00+08:00", "updated_at": "2026-04-07T10:00:00+08:00", "entry_count": 1},
                },
            )
            result = repo.merge_pending_proposals(
                1065,
                [
                    {
                        "proposal_id": "proposal:1",
                        "proposal_type": "action_labels",
                        "target_file_hint": "action_labels",
                        "object_ref": action_ref,
                        "summary": "模型建议该对象也属于核心链路。",
                        "attributes": {"candidate_labels": ["core_business_path"]},
                        "dedupe_key": "same-object",
                        "provenance": {"source_refs": [], "confidence": 0.6},
                    },
                    {
                        "proposal_id": "proposal:2",
                        "proposal_type": "action_labels",
                        "target_file_hint": "action_labels",
                        "object_ref": action_ref,
                        "summary": "模型建议补充用户可见标签。",
                        "attributes": {"candidate_labels": ["core_business_path", "real_user_visible"]},
                        "dedupe_key": "same-object",
                        "provenance": {"source_refs": [], "confidence": 0.8},
                    },
                ],
            )
            self.assertEqual(result["merge_summary"]["created_count"], 1)
            self.assertEqual(result["merge_summary"]["merged_count"], 0)
            self.assertEqual(result["merge_summary"]["deduplicated_count"], 1)
            self.assertGreaterEqual(result["merge_summary"]["conflict_count"], 1)
            self.assertEqual(len(result["review_queue"]["pending"]), 1)


if __name__ == "__main__":
    unittest.main()
