from __future__ import annotations

from typing import Any

from .base import BaseClient


class InstanceClient(BaseClient):
    def list_instances(self, *, biz_system_id: int, application_id: int, end_time: str, time_period: int) -> Any:
        return self.post_form(
            "/server-api/application/instance/select",
            {
                "applicationId": str(application_id),
                "bizSystemId": str(biz_system_id),
                "endTime": end_time,
                "lang": self.lang,
                "timePeriod": str(time_period),
            },
        )

    def cpu_chart(
        self,
        *,
        biz_system_id: int,
        application_id: int,
        instance_id: int,
        end_time: str,
        time_period: int,
        data: str = "cpu",
        name: str = "CPU",
    ) -> Any:
        return self.post_form(
            "/server-api/instance/cpu/chart",
            {
                "applicationId": str(application_id),
                "bizSystemId": str(biz_system_id),
                "data": data,
                "endTime": end_time,
                "instanceId": str(instance_id),
                "lang": self.lang,
                "name": name,
                "timePeriod": str(time_period),
            },
        )

    def jvm_chart(
        self,
        *,
        biz_system_id: int,
        application_id: int,
        instance_id: int,
        end_time: str,
        time_period: int,
        metric_name: str = "ActiveSessions,ExpiredSessions,RejectedSessions,AverageAliveTime",
        metric_scope: str = "Session",
        name: str = "Session",
        only_query_type: bool = False,
    ) -> Any:
        return self.post_form(
            "/server-api/instance/jvm/chart",
            {
                "applicationId": str(application_id),
                "bizSystemId": str(biz_system_id),
                "endTime": end_time,
                "instanceId": str(instance_id),
                "lang": self.lang,
                "metricName": metric_name,
                "metricScope": metric_scope,
                "name": name,
                "onlyQueryType": str(only_query_type).lower(),
                "timePeriod": str(time_period),
            },
        )
