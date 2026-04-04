from __future__ import annotations

import unittest

from tingyun_adapter.service.http_api import InMemoryRateLimiter


class InMemoryRateLimiterTest(unittest.TestCase):
    def test_blocks_when_requests_are_too_close(self) -> None:
        limiter = InMemoryRateLimiter(min_interval_ms=800, max_requests_per_minute=30)
        self.assertIsNone(limiter.check("client-a", now=0.0))
        wait_seconds = limiter.check("client-a", now=0.1)
        self.assertIsNotNone(wait_seconds)
        assert wait_seconds is not None
        self.assertGreater(wait_seconds, 0.6)

    def test_blocks_when_requests_per_minute_exceeded(self) -> None:
        limiter = InMemoryRateLimiter(min_interval_ms=0, max_requests_per_minute=2)
        self.assertIsNone(limiter.check("client-a", now=0.0))
        self.assertIsNone(limiter.check("client-a", now=1.0))
        wait_seconds = limiter.check("client-a", now=2.0)
        self.assertIsNotNone(wait_seconds)
        assert wait_seconds is not None
        self.assertGreater(wait_seconds, 50.0)

    def test_allows_again_after_window_expires(self) -> None:
        limiter = InMemoryRateLimiter(min_interval_ms=0, max_requests_per_minute=2)
        self.assertIsNone(limiter.check("client-a", now=0.0))
        self.assertIsNone(limiter.check("client-a", now=1.0))
        self.assertIsNone(limiter.check("client-a", now=61.0))
