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
