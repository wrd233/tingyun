from __future__ import annotations

from tingyun_adapter.clients.application_client import ApplicationClient
from tingyun_adapter.clients.connection_client import ConnectionClient
from tingyun_adapter.clients.database_client import DatabaseClient
from tingyun_adapter.clients.graph_client import GraphClient
from tingyun_adapter.clients.health_client import HealthClient
from tingyun_adapter.clients.instance_client import InstanceClient
from tingyun_adapter.clients.logtrace_client import LogTraceClient
from tingyun_adapter.clients.nosql_client import NoSQLClient
from tingyun_adapter.clients.trace_client import TraceClient
from tingyun_adapter.clients.webaction_client import WebActionClient
from tingyun_adapter.config.settings import AdapterSettings
from tingyun_adapter.domain.models.common import (
    ActionRef,
    AnalysisContext,
    AuthConfig,
    TraceRef,
    ConnectionPoolRef,
    DatabaseComponentRef,
    NoSQLComponentRef,
    TimeWindow,
)
from tingyun_adapter.sources.captured_api_repository import CapturedApiRepository
from tingyun_adapter.usecases.builders import (
    build_action_hotspot_pack,
    build_action_fact_sheet,
    build_diagnostic_candidate_pack,
    build_report_fact_pack,
    build_system_snapshot,
    build_trace_fact_sheet,
    build_trace_case_pack,
)
from tingyun_adapter.usecases.component_builders import (
    build_connection_pool_pack,
    build_database_component_pack,
    build_nosql_component_pack,
)
from tingyun_adapter.usecases.enhancement_builders import (
    build_business_labels_pack,
    build_comparison_signals_pack,
    build_impact_signals_pack,
    build_page_experience_pack,
    build_stability_signals_pack,
)
from tingyun_adapter.usecases.extended_builders import (
    build_action_dependency_breakdown_pack,
    build_external_dependency_pack,
    build_instance_analysis_pack,
    build_slow_sql_pack,
    build_sql_fact_sheet,
    build_topology_dependency_pack,
)


class Adapter:
    def __init__(self, settings: AdapterSettings) -> None:
        self.settings = settings
        kwargs = {
            "base_url": settings.base_url,
            "token": settings.token,
            "token_env": settings.token_env,
            "lang": settings.lang,
            "timeout": settings.timeout_seconds,
        }
        self.application = ApplicationClient(**kwargs)
        self.webaction = WebActionClient(**kwargs)
        self.graph = GraphClient(**kwargs)
        self.trace = TraceClient(**kwargs)
        self.database = DatabaseClient(**kwargs)
        self.nosql = NoSQLClient(**kwargs)
        self.connection = ConnectionClient(**kwargs)
        self.health = HealthClient(**kwargs)
        self.instance = InstanceClient(**kwargs)
        self.logtrace = LogTraceClient(**kwargs)
        self.captured_api: CapturedApiRepository | None = None
        if settings.captured_api_dir:
            self.captured_api = CapturedApiRepository(settings.captured_api_dir)

    @classmethod
    def from_env(cls, **overrides) -> "Adapter":
        settings = AdapterSettings.from_env(config_path=overrides.get("config_path"))
        merged = AdapterSettings(
            base_url=overrides.get("base_url", settings.base_url),
            token=overrides.get("token", settings.token),
            token_env=overrides.get("token_env", settings.token_env),
            lang=overrides.get("lang", settings.lang),
            timezone=overrides.get("timezone", settings.timezone),
            timeout_seconds=overrides.get("timeout_seconds", settings.timeout_seconds),
            captured_api_dir=overrides.get("captured_api_dir", settings.captured_api_dir),
            config_path=overrides.get("config_path", settings.config_path),
        )
        return cls(merged)

    def build_context(self, *, biz_system_id: int, end_time: str, period_minutes: int) -> AnalysisContext:
        return AnalysisContext(
            base_url=self.settings.base_url,
            biz_system_id=biz_system_id,
            time_window=TimeWindow(end_time=end_time, period_minutes=period_minutes),
            auth=AuthConfig(token=self.settings.token, token_env=self.settings.token_env),
            lang=self.settings.lang,
            timezone=self.settings.timezone,
        )

    def build_system_snapshot(self, context: AnalysisContext, *, source_mode: str = "auto"):
        return build_system_snapshot(self, context, source_mode=source_mode)

    def build_action_hotspot_pack(self, context: AnalysisContext, *, source_mode: str = "auto"):
        return build_action_hotspot_pack(self, context, source_mode=source_mode)

    def build_diagnostic_candidate_pack(self, context: AnalysisContext, *, source_mode: str = "auto", limit: int = 5):
        return build_diagnostic_candidate_pack(self, context, source_mode=source_mode, limit=limit)

    def build_action_fact_sheet(
        self,
        context: AnalysisContext,
        *,
        source_mode: str = "auto",
        action_ref: ActionRef | None = None,
        trace_limit: int = 10,
    ):
        return build_action_fact_sheet(self, context, source_mode=source_mode, action_ref=action_ref, trace_limit=trace_limit)

    def build_trace_case_pack(self, context: AnalysisContext, *, source_mode: str = "auto"):
        return build_trace_case_pack(self, context, source_mode=source_mode)

    def build_trace_fact_sheet(
        self,
        context: AnalysisContext,
        *,
        source_mode: str = "auto",
        action_ref: ActionRef | None = None,
        trace_ref: TraceRef | None = None,
    ):
        return build_trace_fact_sheet(self, context, source_mode=source_mode, action_ref=action_ref, trace_ref=trace_ref)

    def build_report_fact_pack(self, context: AnalysisContext, *, source_mode: str = "auto"):
        return build_report_fact_pack(self, context, source_mode=source_mode)

    def build_database_component_pack(
        self,
        context: AnalysisContext,
        *,
        source_mode: str = "auto",
        component_ref: DatabaseComponentRef | None = None,
    ):
        return build_database_component_pack(self, context, source_mode=source_mode, component_ref=component_ref)

    def build_nosql_component_pack(
        self,
        context: AnalysisContext,
        *,
        source_mode: str = "auto",
        component_ref: NoSQLComponentRef | None = None,
    ):
        return build_nosql_component_pack(self, context, source_mode=source_mode, component_ref=component_ref)

    def build_connection_pool_pack(
        self,
        context: AnalysisContext,
        *,
        source_mode: str = "auto",
        pool_ref: ConnectionPoolRef | None = None,
    ):
        return build_connection_pool_pack(self, context, source_mode=source_mode, pool_ref=pool_ref)

    def build_instance_analysis_pack(
        self,
        context: AnalysisContext,
        *,
        source_mode: str = "auto",
        application_id: int | None = None,
        instance_id: int | None = None,
    ):
        return build_instance_analysis_pack(
            self,
            context,
            source_mode=source_mode,
            application_id=application_id,
            instance_id=instance_id,
        )

    def build_topology_dependency_pack(self, context: AnalysisContext, *, source_mode: str = "auto"):
        return build_topology_dependency_pack(self, context, source_mode=source_mode)

    def build_external_dependency_pack(self, context: AnalysisContext, *, source_mode: str = "auto"):
        return build_external_dependency_pack(self, context, source_mode=source_mode)

    def build_slow_sql_pack(
        self,
        context: AnalysisContext,
        *,
        source_mode: str = "auto",
        component_ref: DatabaseComponentRef | None = None,
        limit: int = 10,
    ):
        return build_slow_sql_pack(
            self,
            context,
            source_mode=source_mode,
            component_ref=component_ref,
            limit=limit,
        )

    def build_sql_fact_sheet(
        self,
        context: AnalysisContext,
        *,
        source_mode: str = "auto",
        component_ref: DatabaseComponentRef | None = None,
        op_name: str | None = None,
        limit: int = 10,
    ):
        return build_sql_fact_sheet(
            self,
            context,
            source_mode=source_mode,
            component_ref=component_ref,
            op_name=op_name,
            limit=limit,
        )

    def build_action_dependency_breakdown_pack(
        self,
        context: AnalysisContext,
        *,
        source_mode: str = "auto",
        action_ref: ActionRef | None = None,
    ):
        return build_action_dependency_breakdown_pack(
            self,
            context,
            source_mode=source_mode,
            action_ref=action_ref,
        )

    def build_business_labels_pack(self, context: AnalysisContext, *, source_mode: str = "auto", limit: int = 10):
        return build_business_labels_pack(self, context, source_mode=source_mode, limit=limit)

    def build_stability_signals_pack(self, context: AnalysisContext, *, source_mode: str = "auto", limit: int = 10):
        return build_stability_signals_pack(self, context, source_mode=source_mode, limit=limit)

    def build_impact_signals_pack(self, context: AnalysisContext, *, source_mode: str = "auto", limit: int = 10):
        return build_impact_signals_pack(self, context, source_mode=source_mode, limit=limit)

    def build_comparison_signals_pack(self, context: AnalysisContext, *, source_mode: str = "auto", limit: int = 10):
        return build_comparison_signals_pack(self, context, source_mode=source_mode, limit=limit)

    def build_page_experience_pack(self, context: AnalysisContext, *, source_mode: str = "auto", limit: int = 10):
        return build_page_experience_pack(self, context, source_mode=source_mode, limit=limit)
