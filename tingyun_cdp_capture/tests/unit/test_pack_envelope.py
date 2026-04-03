import unittest

from tingyun_adapter.domain.models.common import AnalysisContext, AuthConfig, PackEnvelope, TimeWindow


class PackEnvelopeTests(unittest.TestCase):
    def test_pack_envelope_to_dict(self) -> None:
        context = AnalysisContext(
            base_url="http://example.com",
            biz_system_id=1065,
            time_window=TimeWindow(end_time="2026-04-03 12:20", period_minutes=30),
            auth=AuthConfig(token_env="TINGYUN_TOKEN"),
        )
        envelope = PackEnvelope(pack_type="system_snapshot", context=context, payload={"hello": "world"})
        data = envelope.to_dict()
        self.assertEqual(data["pack_type"], "system_snapshot")
        self.assertEqual(data["context"]["biz_system_id"], 1065)
        self.assertEqual(data["payload"]["hello"], "world")


if __name__ == "__main__":
    unittest.main()
