from __future__ import annotations

from typing import Any

from .base import BaseClient


class HealthClient(BaseClient):
    def health_level_statistics(self, *, biz_system_id: int, end_time: str, time_period: int) -> Any:
        return self.post_form(
            "/server-api/health/healthLevelStatistics",
            {
                "timePeriod": str(time_period),
                "bizSystemId": str(biz_system_id),
                "endTime": end_time,
                "lang": self.lang,
            },
        )
