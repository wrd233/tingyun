from __future__ import annotations

from typing import Any, Optional

from .base import BaseClient


class DatabaseClient(BaseClient):
    def list_components(self, *, biz_system_id: int, end_time: str, time_period: int, schema: bool = False) -> Any:
        return self.post_form(
            "/server-api/Database/list",
            {
                "bizSystemId": str(biz_system_id),
                "componentType": "Database",
                "dataType": "COMP",
                "endTime": end_time,
                "lang": self.lang,
                "schema": str(schema).lower(),
                "timePeriod": str(time_period),
            },
        )

    def component_info(
        self,
        *,
        biz_system_id: int,
        component_name: str,
        component_subtype: str,
        end_time: str,
        time_period: int,
        data_type: str = "COMP",
        application_id: str = "",
        instance_id: str = "",
        op_name: str = "",
        tx_action_id: str = "",
    ) -> Any:
        return self.post_form(
            "/server-api/Database/info",
            {
                "applicationId": application_id,
                "bizSystemId": str(biz_system_id),
                "componentName": component_name,
                "componentSubtype": component_subtype,
                "componentType": "Database",
                "dataType": data_type,
                "endTime": end_time,
                "instanceId": instance_id,
                "lang": self.lang,
                "opName": op_name,
                "timePeriod": str(time_period),
                "txActionId": tx_action_id,
                "sortDirection": "DESC",
                "sortField": "respTime",
            },
        )

    def analysis(
        self,
        *,
        biz_system_id: int,
        component_name: str,
        component_subtype: str,
        end_time: str,
        time_period: int,
        data_type: str = "OP",
        page_number: int = 1,
        page_size: int = 1000,
        limit: bool = True,
    ) -> Any:
        return self.post_form(
            "/server-api/Database/analysis",
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

    def action_list(
        self,
        *,
        biz_system_id: int,
        component_name: str,
        component_subtype: str,
        end_time: str,
        time_period: int,
        data_type: str = "COMP",
        application_id: str = "",
        instance_id: str = "",
        op_name: str = "",
        tx_action_id: str = "",
    ) -> Any:
        return self.post_form(
            "/server-api/component/database/actionList",
            {
                "applicationId": application_id,
                "bizSystemId": str(biz_system_id),
                "componentName": component_name,
                "componentSubtype": component_subtype,
                "componentType": "Database",
                "dataType": data_type,
                "endTime": end_time,
                "instanceId": instance_id,
                "lang": self.lang,
                "opName": op_name,
                "timePeriod": str(time_period),
                "txActionId": tx_action_id,
            },
        )

    def action_trace_list(
        self,
        *,
        biz_system_id: int,
        component_name: str,
        component_subtype: str,
        end_time: str,
        time_period: int,
        action_id: int,
        action_type: str,
        data_type: str = "COMP",
        application_id: str = "",
        instance_id: str = "",
        op_name: str = "",
        tx_action_id: str = "",
    ) -> Any:
        return self.post_form(
            "/server-api/component/database/actionTraceList",
            {
                "actionId": str(action_id),
                "actionType": action_type,
                "applicationId": application_id,
                "bizSystemId": str(biz_system_id),
                "componentName": component_name,
                "componentSubtype": component_subtype,
                "componentType": "Database",
                "dataType": data_type,
                "endTime": end_time,
                "instanceId": instance_id,
                "lang": self.lang,
                "opName": op_name,
                "timePeriod": str(time_period),
                "txActionId": tx_action_id,
            },
        )

    def action_name_list(
        self,
        *,
        biz_system_id: int,
        component_name: str,
        component_subtype: str,
        end_time: str,
        time_period: int,
        data_type: str = "OP",
        page_number: int = 1,
        page_size: int = 1000,
        limit: bool = True,
    ) -> Any:
        return self.post_form(
            "/server-api/Database/actionName/list",
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

    def application_name_list(
        self,
        *,
        biz_system_id: int,
        component_name: str,
        component_subtype: str,
        end_time: str,
        time_period: int,
        data_type: str = "OP",
        page_number: int = 1,
        page_size: int = 1000,
        limit: bool = True,
    ) -> Any:
        return self.post_form(
            "/server-api/Database/applicationName/list",
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
