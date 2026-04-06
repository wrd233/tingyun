from __future__ import annotations

from typing import Any

from .base import BaseClient


class WebActionClient(BaseClient):
    def list_actions(
        self,
        *,
        biz_system_id: int,
        end_time: str,
        time_period: int,
        application_id: int = 0,
        sort_field: str = "response",
        sort_direction: str = "DESC",
        favorites: bool = False,
        action_name: str = "",
    ) -> Any:
        return self.post_form(
            "/server-api/webaction/list/actionList",
            {
                "timePeriod": str(time_period),
                "endTime": end_time,
                "bizSystemId": str(biz_system_id),
                "sortField": sort_field,
                "sortDirection": sort_direction,
                "actionName": action_name,
                "applicationId": str(application_id),
                "favorites": str(favorites).lower(),
                "lang": self.lang,
            },
        )

    def action_overview(
        self,
        *,
        biz_system_id: int,
        application_id: int,
        action_id: int,
        action_type: str,
        end_time: str,
        time_period: int,
    ) -> Any:
        return self.post_form(
            "/server-api/webaction/overview",
            {
                "timePeriod": str(time_period),
                "endTime": end_time,
                "bizSystemId": str(biz_system_id),
                "applicationId": str(application_id),
                "actionId": str(action_id),
                "actionType": action_type,
                "lang": self.lang,
            },
        )

    def performance_breakdown(
        self,
        *,
        biz_system_id: int,
        application_id: int,
        action_id: int,
        action_type: str,
        begin_time: str,
        end_time: str,
        time_period: int,
        breakdown_type: str = "ACTION_TRACE",
    ) -> Any:
        return self.post_form(
            "/server-api/webaction/performance/breakdown",
            {
                "actionId": str(action_id),
                "actionType": action_type,
                "applicationId": str(application_id),
                "beginTime": begin_time,
                "bizSystemId": str(biz_system_id),
                "breakdownType": breakdown_type,
                "endTime": end_time,
                "lang": self.lang,
                "timePeriod": str(time_period),
            },
        )

    def thread_analysis_list(
        self,
        *,
        biz_system_id: int,
        biz_system_name: str,
        application_id: int,
        action_id: int,
        action_name: str,
        action_alias: str,
        action_type: str,
        begin_time: str,
        end_time: str,
        time_period: int,
        name: str = "",
    ) -> Any:
        return self.post_form(
            "/server-api/webaction/threadAnalysisList",
            {
                "actionAlias": action_alias,
                "actionId": str(action_id),
                "actionName": action_name,
                "actionType": action_type,
                "applicationId": str(application_id),
                "beginTime": begin_time,
                "bizSystemId": str(biz_system_id),
                "bizSystemName": biz_system_name,
                "curP": "",
                "endTime": end_time,
                "lang": self.lang,
                "localeOptionContent": "undefined",
                "name": name,
                "timePeriod": str(time_period),
            },
        )
