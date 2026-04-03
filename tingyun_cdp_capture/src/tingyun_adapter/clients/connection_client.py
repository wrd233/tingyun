from __future__ import annotations

from typing import Any, Optional

from .base import BaseClient


class ConnectionClient(BaseClient):
    def list_pools(
        self,
        *,
        biz_system_id: int,
        biz_system_name: str,
        begin_time: str,
        end_time: str,
        time_period: int,
        application_id: int = 0,
        instance_id: Optional[int] = None,
        service_group_id: int = 0,
    ) -> Any:
        payload = {
            "applicationId": str(application_id),
            "beginTime": begin_time,
            "bizSystemId": str(biz_system_id),
            "bizSystemName": biz_system_name,
            "curP": "",
            "endTime": end_time,
            "lang": self.lang,
            "localeOptionContent": "undefined",
            "timePeriod": str(time_period),
        }
        if instance_id is not None:
            payload["instanceId"] = str(instance_id)
        if service_group_id:
            payload["serviceGroupId"] = str(service_group_id)
        return self.post_form("/server-api/connection/list", payload)

    def pool_chart(
        self,
        *,
        biz_system_id: int,
        biz_system_name: str,
        begin_time: str,
        end_time: str,
        time_period: int,
        metric_category: str,
        application_id: int = 0,
        instance_id: Optional[int] = None,
        service_group_id: int = 0,
    ) -> Any:
        payload = {
            "applicationId": str(application_id),
            "beginTime": begin_time,
            "bizSystemId": str(biz_system_id),
            "bizSystemName": biz_system_name,
            "curP": "",
            "endTime": end_time,
            "lang": self.lang,
            "localeOptionContent": "undefined",
            "metricCategory": metric_category,
            "timePeriod": str(time_period),
        }
        if instance_id is not None:
            payload["instanceId"] = str(instance_id)
        if service_group_id:
            payload["serviceGroupId"] = str(service_group_id)
        return self.post_form("/server-api/connection/chart", payload)

    def database_chart(
        self,
        *,
        biz_system_id: int,
        component_name: str,
        component_subtype: str,
        end_time: str,
        time_period: int,
        data_type: str = "OP",
        limit: bool = True,
        page_number: int = 1,
        page_size: int = 1000,
    ) -> Any:
        return self.post_form(
            "/server-api/connection/database/chart",
            {
                "bizSystemId": str(biz_system_id),
                "componentName": component_name,
                "componentSubtype": component_subtype,
                "componentType": "Database",
                "dataType": data_type,
                "endTime": end_time,
                "lang": self.lang,
                "limit": str(limit).lower(),
                "pageNumber": str(page_number),
                "pageSize": str(page_size),
                "sortDirection": "DESC",
                "sortField": "respTime",
                "timePeriod": str(time_period),
            },
        )
