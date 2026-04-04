#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen


DEFAULT_BASE_URL = "http://169.169.173.25:8080"
DEFAULT_FILTER_LIST = "Service,Exception,External,Database,NoSQL,Pool,MQ,Code,Dataitem"
DEFAULT_CONFIG_PATH = Path(__file__).resolve().with_name("config.local.json")


def now_minute_string() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def pretty_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=False)


def load_local_config(config_path: str | None) -> tuple[Path, dict[str, Any]]:
    resolved = Path(config_path).expanduser() if config_path else DEFAULT_CONFIG_PATH
    if not resolved.exists():
        return resolved, {}
    with resolved.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise SystemExit(f"Invalid config file, expected a JSON object: {resolved}")
    return resolved, payload


def unwrap_data(payload: Any) -> Any:
    if isinstance(payload, dict) and "data" in payload:
        return payload["data"]
    return payload


def parse_number(value: Any) -> float:
    if value is None:
        return float("-inf")
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return float("-inf")


class TingyunClient:
    def __init__(self, base_url: str, token: str, timeout: int = 30) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout = timeout

    def _request(
        self,
        path: str,
        *,
        query: dict[str, Any] | None = None,
        form: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> Any:
        url = f"{self.base_url}{path}"
        if query:
            url = f"{url}?{urlencode(query, doseq=True)}"

        headers = {
            "Accept": "application/json, text/plain, */*",
            "Authorization": f"Bearer {self.token}",
            "BuiltInRequestId": str(uuid.uuid4()),
        }

        data: bytes | None = None
        if json_body is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(json_body, ensure_ascii=False).encode("utf-8")
        elif form is not None:
            headers["Content-Type"] = "application/x-www-form-urlencoded"
            data = urlencode(form, doseq=True).encode("utf-8")

        request = Request(url, data=data, headers=headers, method="POST")
        with urlopen(request, timeout=self.timeout) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            raw = response.read().decode(charset, errors="replace")
        return json.loads(raw)

    def list_actions(
        self,
        *,
        biz_system_id: int,
        end_time: str,
        time_period: int,
        application_id: int = 0,
        sort_field: str = "response",
        sort_direction: str = "DESC",
    ) -> list[dict[str, Any]]:
        payload = {
            "timePeriod": str(time_period),
            "endTime": end_time,
            "bizSystemId": str(biz_system_id),
            "sortField": sort_field,
            "sortDirection": sort_direction,
            "actionName": "",
            "applicationId": str(application_id),
            "favorites": "false",
            "lang": "zh_CN",
        }
        response = self._request("/server-api/webaction/list/actionList", form=payload)
        data = unwrap_data(response) or {}
        return data.get("content", [])

    def action_overview(
        self,
        *,
        biz_system_id: int,
        application_id: int,
        action_id: int,
        action_type: str,
        end_time: str,
        time_period: int,
    ) -> dict[str, Any]:
        payload = {
            "timePeriod": str(time_period),
            "endTime": end_time,
            "bizSystemId": str(biz_system_id),
            "applicationId": str(application_id),
            "actionId": str(action_id),
            "actionType": action_type,
            "lang": "zh_CN",
        }
        response = self._request("/server-api/webaction/overview", form=payload)
        return unwrap_data(response) or {}

    def list_traces_for_action(
        self,
        *,
        biz_system_id: int,
        application_id: int,
        action_id: int,
        action_type: str,
        end_time: str,
        time_period: int,
        page_size: int = 15,
    ) -> Any:
        payload = {
            "endTime": end_time,
            "labels": {
                "actionIds": [str(action_id)],
                "actionTypes": [action_type],
                "applicationIds": [str(application_id)],
                "systemIds": [str(biz_system_id)],
            },
            "lang": "zh_CN",
            "metric": "trace_current_overview",
            "order": {"fields": ["timestamp"], "type": "desc"},
            "page": {"number": 1, "size": page_size},
            "timePeriod": time_period,
        }
        return self._request(
            "/server-api/graph/query/overview",
            query={"trace_current_overview": "", "lang": "zh_CN"},
            json_body=payload,
        )

    def trace_detail(
        self,
        *,
        biz_system_id: int,
        trace_id: str,
        query_timestamp: str,
        end_time: str,
        time_period: int,
        filter_list: str = DEFAULT_FILTER_LIST,
    ) -> dict[str, Any]:
        payload = {
            "timePeriod": str(time_period),
            "endTime": end_time,
            "traceId": str(trace_id),
            "bizSystemId": str(biz_system_id),
            "queryTimestamp": str(query_timestamp),
            "filterList": filter_list,
            "lang": "zh_CN",
        }
        response = self._request("/server-api/action/trace/detail", form=payload)
        return unwrap_data(response) or {}


def choose_slowest_action(actions: list[dict[str, Any]]) -> dict[str, Any]:
    if not actions:
        raise RuntimeError("actionList returned no actions")
    return max(actions, key=lambda item: parse_number(item.get("response")))


def looks_like_trace_row(item: Any) -> bool:
    if not isinstance(item, dict):
        return False
    has_identity = any(key in item for key in ("id", "traceId", "requestId", "traceGuid"))
    has_context = any(key in item for key in ("actionId", "applicationId", "bizSystemId", "timestamp"))
    return has_identity and has_context


def find_trace_rows(node: Any) -> list[dict[str, Any]]:
    found: list[list[dict[str, Any]]] = []

    def visit(value: Any) -> None:
        if isinstance(value, list):
            if value and all(isinstance(item, dict) for item in value):
                candidates = [item for item in value if looks_like_trace_row(item)]
                if candidates:
                    found.append(candidates)
            for item in value:
                visit(item)
        elif isinstance(value, dict):
            for child in value.values():
                visit(child)

    visit(unwrap_data(node))
    if not found:
        return []
    return max(found, key=len)


def choose_trace(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        raise RuntimeError("trace_current_overview returned no trace rows")

    def trace_score(item: dict[str, Any]) -> float:
        for key in ("respTime", "response", "responseTime", "responseTimeMillisecond", "duration", "totalTime"):
            score = parse_number(item.get(key))
            if score != float("-inf"):
                return score
        timestamp = parse_number(item.get("timestamp"))
        if timestamp != float("-inf"):
            return timestamp
        return float("-inf")

    return max(rows, key=trace_score)


def build_trace_summary(detail: dict[str, Any]) -> dict[str, Any]:
    time_line = detail.get("timeLine") or {}
    request_flow = detail.get("requestServiceFlow") or {}
    service_flow = detail.get("serviceFlow") or {}
    topology = detail.get("topology") or {}
    return {
        "requestId": detail.get("requestId"),
        "traceGuid": detail.get("traceGuid"),
        "actionGuid": detail.get("actionGuid"),
        "bizSystemId": detail.get("bizSystemId"),
        "bizSystemName": detail.get("bizSystemName"),
        "applicationId": detail.get("applicationId"),
        "applicationName": detail.get("applicationName"),
        "actionId": detail.get("actionId"),
        "actionName": detail.get("actionName"),
        "actionType": detail.get("actionType"),
        "instanceId": detail.get("instanceId"),
        "instanceName": detail.get("instanceName"),
        "timestamp": detail.get("timestamp"),
        "respTime": detail.get("respTime"),
        "duration": detail.get("duration"),
        "actionDuration": detail.get("actionDuration"),
        "status": detail.get("status"),
        "method": detail.get("method"),
        "uri": detail.get("uri"),
        "url": detail.get("url"),
        "threadName": detail.get("threadName"),
        "requestHeader": detail.get("requestHeader"),
        "methodTotalParam": detail.get("methodTotalParam"),
        "suspectedProblemList": detail.get("suspectedProblemList"),
        "timeLineSummary": {
            "metricType": time_line.get("metricType"),
            "metricName": time_line.get("metricName"),
            "exclusiveTime": time_line.get("exclusiveTime"),
            "method": time_line.get("method"),
            "methodStack": time_line.get("methodStack"),
        },
        "serviceFlowSummary": {
            "serviceName": service_flow.get("serviceName"),
            "serviceType": service_flow.get("serviceType"),
            "durationTotal": service_flow.get("durationTotal"),
            "requestTotalCount": service_flow.get("requestTotalCount"),
        },
        "requestServiceFlowSummary": {
            "serviceName": request_flow.get("serviceName"),
            "serviceType": request_flow.get("serviceType"),
            "durationTotal": request_flow.get("durationTotal"),
            "requestTotalCount": request_flow.get("requestTotalCount"),
        },
        "topologySummary": {
            "nodeCount": len(topology.get("nodes", [])) if isinstance(topology.get("nodes"), list) else None,
            "lineCount": len(topology.get("lines", [])) if isinstance(topology.get("lines"), list) else None,
        },
    }


def print_action_table(actions: list[dict[str, Any]], limit: int = 5) -> None:
    print("\nTop actions by response")
    for index, item in enumerate(actions[:limit], start=1):
        print(
            f"{index}. actionId={item.get('actionId')} "
            f"response={item.get('response')}ms "
            f"count={item.get('count')} "
            f"slowCount={item.get('slowCount')} "
            f"applicationId={item.get('applicationId')} "
            f"name={item.get('actionName')}"
        )


def print_trace_table(rows: list[dict[str, Any]], limit: int = 5) -> None:
    print("\nTrace candidates")
    for index, item in enumerate(rows[:limit], start=1):
        trace_id = item.get("traceId") or item.get("id") or item.get("requestId")
        duration = (
            item.get("respTime")
            or item.get("response")
            or item.get("responseTime")
            or item.get("duration")
        )
        print(
            f"{index}. traceId={trace_id} "
            f"timestamp={item.get('timestamp')} "
            f"duration={duration} "
            f"status={item.get('status')} "
            f"actionId={item.get('actionId')}"
        )


def require_token(token: str | None) -> str:
    if token:
        return token
    raise SystemExit(
        "Missing token. Set --token, put token in config.local.json, or export TINGYUN_TOKEN / TOKEN before running."
    )


def main() -> int:
    bootstrap = argparse.ArgumentParser(add_help=False)
    bootstrap.add_argument("--config")
    bootstrap_args, _ = bootstrap.parse_known_args()
    config_path, file_config = load_local_config(bootstrap_args.config)
    token_env = file_config.get("token_env", "TINGYUN_TOKEN")
    token_default = (
        os.environ.get(token_env)
        or os.environ.get("TINGYUN_TOKEN")
        or os.environ.get("TOKEN")
        or file_config.get("token")
    )

    parser = argparse.ArgumentParser(
        description="Replay the action -> overview -> trace list -> trace detail workflow against Tingyun."
    )
    parser.add_argument("--config", default=str(config_path))
    parser.add_argument("--base-url", default=os.environ.get("TINGYUN_BASE_URL", file_config.get("base_url", DEFAULT_BASE_URL)))
    parser.add_argument("--token", default=token_default)
    parser.add_argument("--biz-system-id", type=int, default=int(file_config.get("default_biz_system_id", 1065)))
    parser.add_argument("--application-id", type=int, default=0, help="0 means all applications under the business system")
    parser.add_argument("--end-time", default=now_minute_string())
    parser.add_argument("--time-period", type=int, default=30, help="Minutes")
    parser.add_argument("--page-size", type=int, default=15)
    parser.add_argument("--timeout", type=int, default=int(file_config.get("timeout", 30)))
    args = parser.parse_args()

    token = require_token(args.token)
    client = TingyunClient(base_url=args.base_url, token=token, timeout=args.timeout)

    print(f"Base URL: {args.base_url}")
    print(f"bizSystemId: {args.biz_system_id}")
    print(f"endTime: {args.end_time}")
    print(f"timePeriod: {args.time_period} minutes")

    actions = client.list_actions(
        biz_system_id=args.biz_system_id,
        application_id=args.application_id,
        end_time=args.end_time,
        time_period=args.time_period,
    )
    if not actions:
        raise RuntimeError("No actions found for the given business system.")
    actions = sorted(actions, key=lambda item: parse_number(item.get("response")), reverse=True)
    print_action_table(actions)

    slowest_action = choose_slowest_action(actions)
    print("\nSelected slowest action")
    print(pretty_json(slowest_action))

    overview = client.action_overview(
        biz_system_id=args.biz_system_id,
        application_id=int(slowest_action["applicationId"]),
        action_id=int(slowest_action["actionId"]),
        action_type=str(slowest_action["actionType"]),
        end_time=args.end_time,
        time_period=args.time_period,
    )
    print("\nAction overview")
    print(pretty_json(overview))

    trace_response = client.list_traces_for_action(
        biz_system_id=args.biz_system_id,
        application_id=int(slowest_action["applicationId"]),
        action_id=int(slowest_action["actionId"]),
        action_type=str(slowest_action["actionType"]),
        end_time=args.end_time,
        time_period=args.time_period,
        page_size=args.page_size,
    )
    trace_rows = find_trace_rows(trace_response)
    if not trace_rows:
        print("\ntrace_current_overview raw response")
        print(pretty_json(trace_response))
        raise RuntimeError("Could not find trace rows in trace_current_overview response.")

    trace_rows = sorted(
        trace_rows,
        key=lambda item: max(
            parse_number(item.get("respTime")),
            parse_number(item.get("response")),
            parse_number(item.get("responseTime")),
            parse_number(item.get("duration")),
            parse_number(item.get("timestamp")),
        ),
        reverse=True,
    )
    print_trace_table(trace_rows)

    selected_trace = choose_trace(trace_rows)
    print("\nSelected trace row")
    print(pretty_json(selected_trace))

    trace_id = selected_trace.get("traceId") or selected_trace.get("id")
    if trace_id is None:
        raise RuntimeError(f"Selected trace row does not contain a usable trace id: {selected_trace}")

    query_timestamp = (
        selected_trace.get("queryTimestamp")
        or selected_trace.get("timestamp")
        or int(time.time() * 1000)
    )

    detail = client.trace_detail(
        biz_system_id=args.biz_system_id,
        trace_id=str(trace_id),
        query_timestamp=str(query_timestamp),
        end_time=args.end_time,
        time_period=args.time_period,
    )
    print("\nTrace detail summary")
    print(pretty_json(build_trace_summary(detail)))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)
