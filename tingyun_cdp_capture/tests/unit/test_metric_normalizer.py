import unittest

from tingyun_adapter.normalizers.metric_normalizer import normalize_metric_fields


class MetricNormalizerTests(unittest.TestCase):
    def test_normalize_core_metric_fields(self) -> None:
        record = {
            "response": 2967,
            "totalResponse": 5934,
            "throught": 0.22,
            "errorCount": 3,
            "status": True,
        }
        normalized = normalize_metric_fields(record)
        self.assertEqual(normalized["response_time_ms"], 2967.0)
        self.assertEqual(normalized["total_response_time_ms"], 5934.0)
        self.assertEqual(normalized["throughput"], 0.22)
        self.assertEqual(normalized["error_count"], 3)
        self.assertTrue(normalized["trace_status"])


if __name__ == "__main__":
    unittest.main()
