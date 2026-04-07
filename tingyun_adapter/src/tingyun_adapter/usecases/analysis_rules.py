from __future__ import annotations


ENTRY_KEYWORDS = {
    "user_entry": ("uri/", "/api/", "/grcv", "/dwr/", "/rest/", "/openapi/"),
    "internal_entry": ("springcontroller/", "controller/", "service/", "job", "task"),
}

CORE_BUSINESS_KEYWORDS = (
    "contract",
    "business",
    "case",
    "law",
    "approval",
    "workflow",
    "assess",
    "product",
    "user",
)

SUPPORT_KEYWORDS = (
    "upload",
    "download",
    "attachment",
    "template",
    "preview",
    "file",
    "export",
    "import",
)

BACKGROUND_KEYWORDS = (
    "batch",
    "cron",
    "schedule",
    "scheduled",
    "job",
    "timer",
    "listener",
    "mq",
    "async",
    "warmup",
    "init",
    "afterpropertiesset",
    "startup",
)

MAINTENANCE_KEYWORDS = (
    "health",
    "monitor",
    "metrics",
    "actuator",
    "cleanup",
    "reindex",
    "rebuild",
)

FRAMEWORK_NOISE_KEYWORDS = (
    "org.springframework",
    "warlauncher",
    "$$",
    "lambda$",
    "cglib",
)

IMPACT_WEIGHTS = {
    "business": {
        "real_user_visible": 20,
        "core_business_path": 18,
        "important_support_path": 10,
        "user_entry": 8,
    },
    "failure": {
        "error_rate_high": 30,
        "error_rate_medium": 18,
        "error_count_present": 10,
    },
    "performance": {
        "response_very_high": 25,
        "response_high": 18,
        "response_medium": 10,
        "slow_count_high": 8,
    },
    "repeatability": {
        "persistent": 18,
        "recurring": 12,
        "cross_application_pattern": 10,
        "systemic_pattern": 14,
        "multi_instance_localized": 8,
    },
    "evidence": {
        "trace_present": 10,
        "sql_present": 10,
        "dependency_present": 8,
    },
    "penalty": {
        "low_frequency": 8,
    },
}

COMPARISON_THRESHOLDS = {
    "response_time_ms": {"min_delta": 100.0, "ratio": 0.2},
    "error_count": {"min_delta": 3.0, "ratio": 0.3},
    "count": {"min_delta": 5.0, "ratio": 0.3},
}
