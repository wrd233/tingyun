from __future__ import annotations

from typing import Any

from .base import BaseClient


class GraphClient(BaseClient):
    def query_overview(self, *, metric: str, payload: dict[str, Any]) -> Any:
        return self.post_json(
            "/server-api/graph/query/overview",
            payload,
            query={metric: "", "lang": self.lang},
        )

    def query_diagram(self, *, metric: str, payload: dict[str, Any]) -> Any:
        return self.post_json(
            "/server-api/graph/query/diagram",
            payload,
            query={"metric": metric, "lang": self.lang},
        )

    def information(self, *, metric: str, payload: dict[str, Any], request_info_style: bool = False) -> Any:
        query = {"lang": self.lang, "request_info": ""} if request_info_style else {"lang": self.lang, "metric": metric}
        return self.post_json("/server-api/graph/information", payload, query=query)

    def query_database_graph(self, *, biz_system_id: int, component_name: str, component_subtype: str, end_time: str, time_period: int) -> Any:
        return self.post_form(
            "/server-api/graph/component/queryDataBaseGraph",
            {
                "bizSystemId": str(biz_system_id),
                "componentName": component_name,
                "componentSubtype": component_subtype,
                "componentType": "Database",
                "endTime": end_time,
                "lang": self.lang,
                "timePeriod": str(time_period),
            },
        )

    def query_nosql_graph(self, *, biz_system_id: int, component_name: str, component_subtype: str, end_time: str, time_period: int) -> Any:
        return self.post_form(
            "/server-api/graph/component/queryNosqlGraph",
            {
                "bizSystemId": str(biz_system_id),
                "componentName": component_name,
                "componentSubtype": component_subtype,
                "componentType": "NoSQL",
                "endTime": end_time,
                "lang": self.lang,
                "timePeriod": str(time_period),
            },
        )

    def query_biz_system_graph(self, *, end_time: str, time_period: int) -> Any:
        return self.post_form(
            "/server-api/graph/queryBizSystenGraph",
            {
                "endTime": end_time,
                "lang": self.lang,
                "timePeriod": str(time_period),
            },
        )

    def query_biz_detail_graph(
        self,
        *,
        biz_system_id: int,
        end_time: str,
        time_period: int,
        merge_graph: str = "1",
        cascading_display: str = "1",
        is_biz_system_tree: str = "true",
        is_group_tree: str = "false",
    ) -> Any:
        return self.post_form(
            "/server-api/graph/queryBizDetailGraph",
            {
                "bizSystemId": str(biz_system_id),
                "cascadingDisplay": cascading_display,
                "endTime": end_time,
                "isBizSystemTree": is_biz_system_tree,
                "isGroupTree": is_group_tree,
                "lang": self.lang,
                "mergeGraph": merge_graph,
                "timePeriod": str(time_period),
            },
        )

    def query_action_graph(
        self,
        *,
        biz_system_id: int,
        application_id: int,
        action_id: int,
        action_type: str,
        end_time: str,
        time_period: int,
        merge_graph: str = "1",
    ) -> Any:
        return self.post_form(
            "/server-api/graph/queryActionGraph",
            {
                "actionId": str(action_id),
                "actionType": action_type,
                "applicationId": str(application_id),
                "bizSystemId": str(biz_system_id),
                "endTime": end_time,
                "lang": self.lang,
                "mergeGraph": merge_graph,
                "timePeriod": str(time_period),
            },
        )

    def query_graph_health(self, *, end_time: str, time_period: int, node_ids: dict[str, int]) -> Any:
        return self.post_json(
            "/server-api/graph/queryGraphHealth",
            {
                "endTime": end_time,
                "lang": self.lang,
                "nodeIds": node_ids,
                "timePeriod": time_period,
            },
            query={"lang": self.lang},
        )
