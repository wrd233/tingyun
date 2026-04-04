from __future__ import annotations

from typing import Any

from .base import BaseClient


class ApplicationClient(BaseClient):
    def business_overview(self, *, biz_system_id: int, end_time: str, time_period: int) -> Any:
        return self.post_form(
            f"/server-api/application/business/overview/{biz_system_id}",
            {
                "timePeriod": str(time_period),
                "endTime": end_time,
                "lang": self.lang,
            },
        )

    def response_chart(self, *, biz_system_id: int, end_time: str, time_period: int, business_type: str = "BIZ_SYSTEM") -> Any:
        return self._chart("response", biz_system_id=biz_system_id, end_time=end_time, time_period=time_period, business_type=business_type)

    def throughput_chart(self, *, biz_system_id: int, end_time: str, time_period: int, business_type: str = "BIZ_SYSTEM") -> Any:
        return self._chart("throught", biz_system_id=biz_system_id, end_time=end_time, time_period=time_period, business_type=business_type)

    def error_chart(self, *, biz_system_id: int, end_time: str, time_period: int, business_type: str = "BIZ_SYSTEM") -> Any:
        return self._chart("error", biz_system_id=biz_system_id, end_time=end_time, time_period=time_period, business_type=business_type)

    def _chart(self, chart_name: str, *, biz_system_id: int, end_time: str, time_period: int, business_type: str) -> Any:
        return self.post_form(
            f"/server-api/application/charts/{chart_name}",
            {
                "timePeriod": str(time_period),
                "endTime": end_time,
                "businessType": business_type,
                "bizSystemId": str(biz_system_id),
                "lang": self.lang,
            },
        )
