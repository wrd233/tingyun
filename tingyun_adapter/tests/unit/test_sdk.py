import unittest
from pathlib import Path

from tingyun_adapter.config.settings import AdapterSettings
from tingyun_adapter.domain.models.common import TimeWindow
from tingyun_adapter.invocation.sdk import Adapter


ROOT = Path(__file__).resolve().parents[2]


class AdapterSdkTests(unittest.TestCase):
    def test_build_context_uses_time_window_model(self) -> None:
        adapter = Adapter(AdapterSettings())
        context = adapter.build_context(biz_system_id=1065, end_time="2026-04-03 12:20", period_minutes=30)
        self.assertEqual(context.biz_system_id, 1065)
        self.assertIsInstance(context.time_window, TimeWindow)
        self.assertEqual(context.time_window.end_time, "2026-04-03 12:20")
        self.assertEqual(context.time_window.period_minutes, 30)

    def test_adapter_initializes_knowledge_repository_when_configured(self) -> None:
        adapter = Adapter(AdapterSettings(knowledge_dir=str(ROOT.parent / "knowledge" / "monitored_systems")))
        self.assertIsNotNone(adapter.knowledge_repository)

    def test_adapter_exposes_data_export_pack_builder(self) -> None:
        adapter = Adapter(AdapterSettings())
        self.assertTrue(callable(getattr(adapter, "build_data_export_pack")))


if __name__ == "__main__":
    unittest.main()
