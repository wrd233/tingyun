from __future__ import annotations

from typing import Any

from .base import BaseClient


class NoSQLClient(BaseClient):
    def list_components(self, *, biz_system_id: int, end_time: str, time_period: int, schema: bool = False) -> Any:
        return self.post_form(
            "/server-api/NoSQL/list",
            {
                "bizSystemId": str(biz_system_id),
                "componentType": "NoSQL",
                "dataType": "COMP",
                "endTime": end_time,
                "lang": self.lang,
                "schema": str(schema).lower(),
                "timePeriod": str(time_period),
            },
        )

    def overview(
        self,
        *,
        biz_system_id: int,
        component_name: str,
        component_subtype: str,
        end_time: str,
        time_period: int,
        data_type: str = "COMP",
    ) -> Any:
        return self.post_form(
            "/server-api/NoSQL/overview",
            {
                "bizSystemId": str(biz_system_id),
                "componentName": component_name,
                "componentSubtype": component_subtype,
                "componentType": "NoSQL",
                "dataType": data_type,
                "endTime": end_time,
                "lang": self.lang,
                "sortDirection": "DESC",
                "sortField": "respTime",
                "timePeriod": str(time_period),
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
            "/server-api/NoSQL/analysis",
            {
                "bizSystemId": str(biz_system_id),
                "componentName": component_name,
                "componentSubtype": component_subtype,
                "componentType": "NoSQL",
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

    def trace(
        self,
        *,
        biz_system_id: int,
        component_name: str,
        component_subtype: str,
        end_time: str,
        time_period: int,
        op_name: str,
        page_number: int = 1,
        page_size: int = 20,
        limit: bool = True,
    ) -> Any:
        return self.post_form(
            "/server-api/NoSQL/trace",
            {
                "bizSystemId": str(biz_system_id),
                "componentName": component_name,
                "componentSubtype": component_subtype,
                "componentType": "NoSQL",
                "dataType": "OP",
                "endTime": end_time,
                "lang": self.lang,
                "limit": str(limit).lower(),
                "opName": op_name,
                "pageNumber": str(page_number),
                "pageSize": str(page_size),
                "sortDirection": "DESC",
                "sortField": "respTime",
                "timePeriod": str(time_period),
            },
        )

    def error_type_amount(self, *, biz_system_id: int, component_name: str, end_time: str, time_period: int) -> Any:
        return self.post_form(
            "/server-api/NoSQL/errorTypeAmount",
            {
                "bizSystemId": str(biz_system_id),
                "componentName": component_name,
                "componentType": "NoSQL",
                "endTime": end_time,
                "lang": self.lang,
                "timePeriod": str(time_period),
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
            "/server-api/NoSQL/actionName/list",
            {
                "bizSystemId": str(biz_system_id),
                "componentName": component_name,
                "componentSubtype": component_subtype,
                "componentType": "NoSQL",
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
            "/server-api/NoSQL/applicationName/list",
            {
                "bizSystemId": str(biz_system_id),
                "componentName": component_name,
                "componentSubtype": component_subtype,
                "componentType": "NoSQL",
                "dataType": data_type,
                "endTime": end_time,
                "lang": self.lang,
                "limit": str(limit).lower(),
                "pageNumber": str(page_number),
                "pageSize": str(page_size),
                "timePeriod": str(time_period),
            },
        )
