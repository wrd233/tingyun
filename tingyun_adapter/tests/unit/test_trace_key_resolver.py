import unittest

from tingyun_adapter.normalizers.trace_key_resolver import resolve_trace_keys


class TraceKeyResolverTests(unittest.TestCase):
    def test_resolve_mixed_trace_keys(self) -> None:
        record = {
            "id": "1751280907",
            "requestId": "78aa7c93cae02935",
            "actionGuid": "78aa7c93cae02935",
            "traceGuid": "78aa7c93cae02935",
            "timestamp": 1775214419414,
        }
        keys = resolve_trace_keys(record)
        self.assertEqual(keys.trace_id_numeric, "1751280907")
        self.assertEqual(keys.trace_guid, "78aa7c93cae02935")
        self.assertEqual(keys.action_guid, "78aa7c93cae02935")
        self.assertEqual(keys.request_id, "78aa7c93cae02935")
        self.assertEqual(keys.query_timestamp, "1775214419414")


if __name__ == "__main__":
    unittest.main()
