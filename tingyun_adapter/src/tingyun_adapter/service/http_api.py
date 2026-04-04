from __future__ import annotations

import argparse
from typing import Any, Optional

from fastapi import Depends, FastAPI, Header, HTTPException
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
}


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

    model_config = {"populate_by_name": True}


def create_app(*, config_path: Optional[str] = None) -> FastAPI:
    settings = AdapterSettings.from_env(config_path=config_path)
    adapter = Adapter(settings)
    app = FastAPI(
        title="Tingyun Adapter Service",
        version="0.1.0",
        description="Expose Tingyun adapter packs over HTTP for remote agents and skills.",
    )

    def _authorize(
        x_adapter_api_key: Optional[str] = Header(default=None),
        authorization: Optional[str] = Header(default=None),
    ) -> None:
        expected = settings.service_api_key
        if not expected:
            return
        bearer = None
        if authorization and authorization.startswith("Bearer "):
            bearer = authorization[len("Bearer ") :]
        if x_adapter_api_key == expected or bearer == expected:
            return
        raise HTTPException(status_code=401, detail="Unauthorized")

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
        }

    @app.post("/v1/packs/{pack_type}")
    def build_pack(pack_type: str, request: BuildPackRequest, _auth: None = Depends(_authorize)) -> dict[str, Any]:
        if pack_type not in PACK_TYPES:
            raise HTTPException(status_code=404, detail=f"Unsupported pack type: {pack_type}")

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
            envelope = adapter.build_diagnostic_candidate_pack(context, source_mode=request.source_mode, limit=request.limit)
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
            envelope = adapter.build_database_component_pack(context, source_mode=request.source_mode, component_ref=component_ref)
        elif pack_type == "nosql_component_pack":
            component_ref = None
            if request.component_name:
                component_ref = NoSQLComponentRef(
                    biz_system_id=request.biz_system_id,
                    component_name=request.component_name,
                    component_subtype=request.component_subtype,
                )
            envelope = adapter.build_nosql_component_pack(context, source_mode=request.source_mode, component_ref=component_ref)
        else:
            pool_ref = None
            if request.metric_category or request.application_id or request.instance_id:
                pool_ref = ConnectionPoolRef(
                    biz_system_id=request.biz_system_id,
                    metric_category=request.metric_category,
                    application_id=request.application_id,
                    instance_id=request.instance_id,
                )
            envelope = adapter.build_connection_pool_pack(context, source_mode=request.source_mode, pool_ref=pool_ref)
        return envelope.to_dict()

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
