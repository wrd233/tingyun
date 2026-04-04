import unittest
from pathlib import Path

from tingyun_adapter.sources.captured_api_repository import CapturedApiRepository


ROOT = Path(__file__).resolve().parents[2]
CAPTURED_API_DIR = ROOT.parent / "tingyun_cdp_capture" / "captured_api"


class CapturedApiRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repository = CapturedApiRepository(CAPTURED_API_DIR)

    def test_repository_can_list_known_paths(self) -> None:
        paths = self.repository.list_relative_paths()
        self.assertIn("webaction/list/actionList", paths)
        self.assertIn("action/trace/detail", paths)

    def test_repository_can_load_sample_response(self) -> None:
        body = self.repository.load_first_sample_response("webaction/list/actionList")
        self.assertIsInstance(body, dict)
        self.assertEqual(body["code"], 200)
        self.assertIn("content", body["data"])


if __name__ == "__main__":
    unittest.main()
