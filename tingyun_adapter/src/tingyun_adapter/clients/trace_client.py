from __future__ import annotations

from typing import Any

from tingyun_adapter.config.constants import TRACE_FILTER_LIST

from .base import BaseClient


class TraceClient(BaseClient):
    def trace_detail(
        self,
        *,
        biz_system_id: int,
        trace_id: str,
        query_timestamp: str,
        end_time: str,
        time_period: int,
        filter_list: str = TRACE_FILTER_LIST,
    ) -> Any:
        return self.post_form(
            "/server-api/action/trace/detail",
            {
                "timePeriod": str(time_period),
                "endTime": end_time,
                "traceId": trace_id,
                "bizSystemId": str(biz_system_id),
                "queryTimestamp": query_timestamp,
                "filterList": filter_list,
                "lang": self.lang,
            },
        )

    def trace_exceptions(
        self,
        *,
        biz_system_id: int,
        trace_id: str,
        query_timestamp: str,
        tree_id: str,
        end_time: str,
        time_period: int,
    ) -> Any:
        return self.post_form(
            "/server-api/action/trace/detail/exceptions",
            {
                "bizSystemId": str(biz_system_id),
                "endTime": end_time,
                "lang": self.lang,
                "queryTimestamp": query_timestamp,
                "timePeriod": str(time_period),
                "traceId": trace_id,
                "treeId": tree_id,
            },
        )

    def call_tree(
        self,
        *,
        biz_system_id: int,
        trace_id: str,
        action_guid: str,
        query_timestamp: str,
        end_time: str,
        time_period: int,
        filter_list: str = TRACE_FILTER_LIST,
        percentile_status: bool = True,
    ) -> Any:
        return self.post_form(
            "/server-api/action/trace/callTree",
            {
                "actionGuid": action_guid,
                "bizSystemId": str(biz_system_id),
                "endTime": end_time,
                "filterList": filter_list,
                "lang": self.lang,
                "percentileStatus": str(percentile_status).lower(),
                "queryTimestamp": query_timestamp,
                "timePeriod": str(time_period),
                "traceId": trace_id,
            },
        )

    def snapshot_time_info(
        self,
        *,
        biz_system_id: int,
        trace_id: str,
        query_timestamp: str,
        end_time: str,
        time_period: int,
        trace_ids: str = "",
    ) -> Any:
        return self.post_form(
            "/server-api/action/trace/detail/snapshotTimeInfo",
            {
                "bizSystemId": str(biz_system_id),
                "endTime": end_time,
                "lang": self.lang,
                "queryTimestamp": query_timestamp,
                "timePeriod": str(time_period),
                "traceId": trace_id,
                "traceIds": trace_ids,
            },
        )

    def query_agent_version_info(self, *, instance_id: int) -> Any:
        return self.post_form(
            "/server-api/action/trace/detail/queryAgentVersionInfo",
            {
                "instanceId": str(instance_id),
                "lang": self.lang,
            },
        )
