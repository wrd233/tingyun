import unittest

from tingyun_adapter.config.settings import AdapterSettings
from tingyun_adapter.domain.models.common import TimeWindow
from tingyun_adapter.invocation.sdk import Adapter


class AdapterSdkTests(unittest.TestCase):
    def test_build_context_uses_time_window_model(self) -> None:
        adapter = Adapter(AdapterSettings())
        context = adapter.build_context(biz_system_id=1065, end_time="2026-04-03 12:20", period_minutes=30)
        self.assertEqual(context.biz_system_id, 1065)
        self.assertIsInstance(context.time_window, TimeWindow)
        self.assertEqual(context.time_window.end_time, "2026-04-03 12:20")
        self.assertEqual(context.time_window.period_minutes, 30)


if __name__ == "__main__":
    unittest.main()
