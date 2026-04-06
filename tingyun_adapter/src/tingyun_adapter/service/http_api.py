from __future__ import annotations

import argparse
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Optional
from urllib.error import HTTPError, URLError

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from pydantic import BaseModel, Field

from tingyun_adapter.config.settings import AdapterSettings
from tingyun_adapter.domain.models.common import ActionRef, ConnectionPoolRef, DatabaseComponentRef, NoSQLComponentRef, TraceRef
from tingyun_adapter.invocation.sdk import Adapter


PACK_TYPES = {
    "system_snapshot",
    "action_hotspot_pack",
    "diagnostic_candidate_pack",
    "action_fact_sheet",
    "trace_case_pack",
    "trace_fact_sheet",
    "report_fact_pack",
    "database_component_pack",
    "nosql_component_pack",
    "connection_pool_pack",
    "instance_analysis_pack",
    "topology_dependency_pack",
    "external_dependency_pack",
    "slow_sql_pack",
    "sql_fact_sheet",
    "action_dependency_breakdown_pack",
}


@dataclass
class InMemoryRateLimiter:
    min_interval_ms: int
    max_requests_per_minute: int
    _lock: threading.Lock = field(default_factory=threading.Lock)
    _recent_requests: dict[str, deque[float]] = field(default_factory=dict)
    _last_request_at: dict[str, float] = field(default_factory=dict)

    def check(self, identifier: str, *, now: Optional[float] = None) -> Optional[float]:
        if self.min_interval_ms <= 0 and self.max_requests_per_minute <= 0:
            return None
        now = time.monotonic() if now is None else now
        min_interval_seconds = max(self.min_interval_ms, 0) / 1000.0
        with self._lock:
            recent = self._recent_requests.setdefault(identifier, deque())
            cutoff = now - 60.0
            while recent and recent[0] <= cutoff:
                recent.popleft()
            if self.max_requests_per_minute > 0 and len(recent) >= self.max_requests_per_minute:
                return max(0.0, 60.0 - (now - recent[0]))
            last = self._last_request_at.get(identifier)
            if last is not None and min_interval_seconds > 0:
                wait_seconds = min_interval_seconds - (now - last)
                if wait_seconds > 0:
                    return wait_seconds
            recent.append(now)
            self._last_request_at[identifier] = now
        return None


class BuildPackRequest(BaseModel):
    biz_system_id: int = Field(..., alias="bizSystemId")
    end_time: str = Field(..., alias="endTime")
    period_minutes: int = Field(30, alias="periodMinutes")
    source_mode: str = Field("auto", alias="sourceMode")
    limit: int = 5
    application_id: Optional[int] = Field(None, alias="applicationId")
    instance_id: Optional[int] = Field(None, alias="instanceId")
    action_id: Optional[int] = Field(None, alias="actionId")
    action_type: str = Field("TX", alias="actionType")
    component_name: Optional[str] = Field(None, alias="componentName")
    component_subtype: Optional[str] = Field(None, alias="componentSubtype")
    metric_category: Optional[str] = Field(None, alias="metricCategory")
    trace_id: Optional[str] = Field(None, alias="traceId")
    query_timestamp: Optional[str] = Field(None, alias="queryTimestamp")
    trace_guid: Optional[str] = Field(None, alias="traceGuid")
    action_guid: Optional[str] = Field(None, alias="actionGuid")
    request_id: Optional[str] = Field(None, alias="requestId")
    op_name: Optional[str] = Field(None, alias="opName")

    model_config = {"populate_by_name": True}


def _http_error_detail(exc: HTTPError) -> dict[str, Any]:
    body = ""
    try:
        raw = exc.read()
        if raw:
            body = raw.decode("utf-8", errors="replace")[:1000]
    except Exception:
        body = ""
    return {
        "code": "upstream_http_error",
        "message": "Upstream Tingyun API returned an HTTP error.",
        "upstream_status": exc.code,
        "upstream_url": exc.filename,
        "upstream_body": body,
        "hint": "Check Tingyun token validity, permissions, and whether the selected sourceMode should be sample or live.",
    }


def create_app(*, config_path: Optional[str] = None) -> FastAPI:
    settings = AdapterSettings.from_env(config_path=config_path)
    adapter = Adapter(settings)
    rate_limiter = InMemoryRateLimiter(
        min_interval_ms=settings.service_min_interval_ms,
        max_requests_per_minute=settings.service_max_requests_per_minute,
    )
    app = FastAPI(
        title="Tingyun Adapter Service",
        version="0.1.0",
        description="Expose Tingyun adapter packs over HTTP for remote agents and skills.",
    )

    def _authorize(
        request: Request,
        x_adapter_api_key: Optional[str] = Header(default=None),
        authorization: Optional[str] = Header(default=None),
    ) -> None:
        expected = settings.service_api_key
        bearer = None
        if authorization and authorization.startswith("Bearer "):
            bearer = authorization[len("Bearer ") :]
        if not expected:
            client_host = request.client.host if request.client else "unknown"
            wait_seconds = rate_limiter.check(client_host)
            if wait_seconds:
                raise HTTPException(
                    status_code=429,
                    detail=f"Rate limit exceeded, retry after {wait_seconds:.2f}s",
                    headers={"Retry-After": str(max(1, int(wait_seconds) + 1))},
                )
            return
        if x_adapter_api_key != expected and bearer != expected:
            raise HTTPException(status_code=401, detail="Unauthorized")
        client_host = request.client.host if request.client else "unknown"
        client_key = (x_adapter_api_key or bearer or "anonymous")[:8]
        wait_seconds = rate_limiter.check(f"{client_host}:{client_key}")
        if wait_seconds:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded, retry after {wait_seconds:.2f}s",
                headers={"Retry-After": str(max(1, int(wait_seconds) + 1))},
            )

    @app.get("/healthz")
    def healthz() -> dict[str, Any]:
        return {
            "status": "ok",
            "service": "tingyun-adapter",
            "version": "0.1.0",
            "config": {
                "base_url": settings.base_url,
                "captured_api_dir": settings.captured_api_dir,
                "service_host": settings.service_host,
                "service_port": settings.service_port,
                "service_public_base_url": settings.service_public_base_url,
                "service_api_key_enabled": bool(settings.service_api_key),
                "service_min_interval_ms": settings.service_min_interval_ms,
                "service_max_requests_per_minute": settings.service_max_requests_per_minute,
            },
            "capabilities": {
                "captured_api_attached": bool(adapter.captured_api and adapter.captured_api.exists()),
                "has_tingyun_token": bool(settings.token),
            },
        }

    @app.get("/v1/meta")
    def meta() -> dict[str, Any]:
        return {
            "service": "tingyun-adapter",
            "version": "0.1.0",
            "pack_types": sorted(PACK_TYPES),
            "source_modes": ["auto", "sample", "live"],
            "public_base_url": settings.service_public_base_url,
            "rate_limit": {
                "min_interval_ms": settings.service_min_interval_ms,
                "max_requests_per_minute": settings.service_max_requests_per_minute,
            },
        }

    @app.post("/v1/packs/{pack_type}")
    def build_pack(pack_type: str, request: BuildPackRequest, _auth: None = Depends(_authorize)) -> dict[str, Any]:
        if pack_type not in PACK_TYPES:
            raise HTTPException(status_code=404, detail=f"Unsupported pack type: {pack_type}")

        try:
            context = adapter.build_context(
                biz_system_id=request.biz_system_id,
                end_time=request.end_time,
                period_minutes=request.period_minutes,
            )
            if pack_type == "system_snapshot":
                envelope = adapter.build_system_snapshot(context, source_mode=request.source_mode)
            elif pack_type == "action_hotspot_pack":
                envelope = adapter.build_action_hotspot_pack(context, source_mode=request.source_mode)
            elif pack_type == "diagnostic_candidate_pack":
                envelope = adapter.build_diagnostic_candidate_pack(
                    context,
                    source_mode=request.source_mode,
                    limit=request.limit,
                )
            elif pack_type == "action_fact_sheet":
                action_ref = None
                if request.action_id and request.application_id:
                    action_ref = ActionRef(
                        biz_system_id=request.biz_system_id,
                        application_id=request.application_id,
                        action_id=request.action_id,
                        action_type=request.action_type,
                    )
                envelope = adapter.build_action_fact_sheet(
                    context,
                    source_mode=request.source_mode,
                    action_ref=action_ref,
                    trace_limit=request.limit,
                )
            elif pack_type == "trace_case_pack":
                envelope = adapter.build_trace_case_pack(context, source_mode=request.source_mode)
            elif pack_type == "trace_fact_sheet":
                action_ref = None
                if request.action_id and request.application_id:
                    action_ref = ActionRef(
                        biz_system_id=request.biz_system_id,
                        application_id=request.application_id,
                        action_id=request.action_id,
                        action_type=request.action_type,
                    )
                trace_ref = None
                if request.trace_id or request.query_timestamp or request.trace_guid or request.action_guid or request.request_id:
                    trace_ref = TraceRef(
                        biz_system_id=request.biz_system_id,
                        trace_id_numeric=request.trace_id,
                        query_timestamp=request.query_timestamp,
                        trace_guid=request.trace_guid,
                        action_guid=request.action_guid,
                        request_id=request.request_id,
                    )
                envelope = adapter.build_trace_fact_sheet(
                    context,
                    source_mode=request.source_mode,
                    action_ref=action_ref,
                    trace_ref=trace_ref,
                )
            elif pack_type == "report_fact_pack":
                envelope = adapter.build_report_fact_pack(context, source_mode=request.source_mode)
            elif pack_type == "database_component_pack":
                component_ref = None
                if request.component_name:
                    component_ref = DatabaseComponentRef(
                        biz_system_id=request.biz_system_id,
                        component_name=request.component_name,
                        component_subtype=request.component_subtype,
                    )
                envelope = adapter.build_database_component_pack(
                    context,
                    source_mode=request.source_mode,
                    component_ref=component_ref,
                )
            elif pack_type == "nosql_component_pack":
                component_ref = None
                if request.component_name:
                    component_ref = NoSQLComponentRef(
                        biz_system_id=request.biz_system_id,
                        component_name=request.component_name,
                        component_subtype=request.component_subtype,
                    )
                envelope = adapter.build_nosql_component_pack(
                    context,
                    source_mode=request.source_mode,
                    component_ref=component_ref,
                )
            elif pack_type == "connection_pool_pack":
                pool_ref = None
                if request.metric_category or request.application_id or request.instance_id:
                    pool_ref = ConnectionPoolRef(
                        biz_system_id=request.biz_system_id,
                        metric_category=request.metric_category,
                        application_id=request.application_id,
                        instance_id=request.instance_id,
                    )
                envelope = adapter.build_connection_pool_pack(
                    context,
                    source_mode=request.source_mode,
                    pool_ref=pool_ref,
                )
            elif pack_type == "instance_analysis_pack":
                envelope = adapter.build_instance_analysis_pack(
                    context,
                    source_mode=request.source_mode,
                    application_id=request.application_id,
                    instance_id=request.instance_id,
                )
            elif pack_type == "topology_dependency_pack":
                envelope = adapter.build_topology_dependency_pack(context, source_mode=request.source_mode)
            elif pack_type == "external_dependency_pack":
                envelope = adapter.build_external_dependency_pack(context, source_mode=request.source_mode)
            elif pack_type == "slow_sql_pack":
                component_ref = None
                if request.component_name:
                    component_ref = DatabaseComponentRef(
                        biz_system_id=request.biz_system_id,
                        component_name=request.component_name,
                        component_subtype=request.component_subtype,
                    )
                envelope = adapter.build_slow_sql_pack(
                    context,
                    source_mode=request.source_mode,
                    component_ref=component_ref,
                    limit=request.limit,
                )
            elif pack_type == "sql_fact_sheet":
                component_ref = None
                if request.component_name:
                    component_ref = DatabaseComponentRef(
                        biz_system_id=request.biz_system_id,
                        component_name=request.component_name,
                        component_subtype=request.component_subtype,
                    )
                envelope = adapter.build_sql_fact_sheet(
                    context,
                    source_mode=request.source_mode,
                    component_ref=component_ref,
                    op_name=request.op_name,
                    limit=request.limit,
                )
            else:
                action_ref = None
                if request.action_id and request.application_id:
                    action_ref = ActionRef(
                        biz_system_id=request.biz_system_id,
                        application_id=request.application_id,
                        action_id=request.action_id,
                        action_type=request.action_type,
                    )
                envelope = adapter.build_action_dependency_breakdown_pack(
                    context,
                    source_mode=request.source_mode,
                    action_ref=action_ref,
                )
            return envelope.to_dict()
        except HTTPError as exc:
            raise HTTPException(status_code=502, detail=_http_error_detail(exc)) from exc
        except URLError as exc:
            raise HTTPException(
                status_code=502,
                detail={
                    "code": "upstream_network_error",
                    "message": "Failed to reach upstream Tingyun API.",
                    "reason": str(exc.reason),
                    "hint": "Check base_url connectivity from machine A and verify the upstream service is reachable.",
                },
            ) from exc
        except RuntimeError as exc:
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "adapter_runtime_error",
                    "message": str(exc),
                },
            ) from exc
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail={
                    "code": "adapter_internal_error",
                    "message": str(exc),
                },
            ) from exc

    return app


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Tingyun adapter HTTP service.")
    parser.add_argument("--config")
    parser.add_argument("--host")
    parser.add_argument("--port", type=int)
    args = parser.parse_args()

    settings = AdapterSettings.from_env(config_path=args.config)
    host = args.host or settings.service_host
    port = args.port or settings.service_port

    import uvicorn

    app = create_app(config_path=args.config)
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
