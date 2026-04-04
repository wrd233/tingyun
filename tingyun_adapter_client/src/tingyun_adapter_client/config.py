from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from typing import Optional


def _project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _load_config_file(config_path: Path) -> dict[str, Any]:
    if not config_path.exists():
        return {}
    with config_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise RuntimeError(f"Client config must be a JSON object: {config_path}")
    return payload


def _normalize_base_url(value: str) -> str:
    return value.rstrip("/")


@dataclass(frozen=True)
class RemoteClientSettings:
    service_base_url: str = "http://127.0.0.1:8000"
    service_api_key: Optional[str] = None
    timeout_seconds: int = 30
    default_source_mode: str = "sample"
    config_path: Optional[str] = None

    @classmethod
    def default_config_path(cls) -> Path:
        return _project_root() / "config.local.json"

    @classmethod
    def from_env(cls, config_path: Optional[str] = None) -> "RemoteClientSettings":
        resolved_config_path = Path(config_path).expanduser() if config_path else cls.default_config_path()
        raw = _load_config_file(resolved_config_path)
        return cls(
            service_base_url=_normalize_base_url(
                os.environ.get("TINGYUN_ADAPTER_SERVICE_BASE_URL", raw.get("service_base_url", "http://127.0.0.1:8000"))
            ),
            service_api_key=os.environ.get("TINGYUN_ADAPTER_SERVICE_API_KEY", raw.get("service_api_key")),
            timeout_seconds=int(
                os.environ.get("TINGYUN_ADAPTER_CLIENT_TIMEOUT_SECONDS", raw.get("timeout_seconds", 30))
            ),
            default_source_mode=os.environ.get(
                "TINGYUN_ADAPTER_DEFAULT_SOURCE_MODE",
                raw.get("default_source_mode", "sample"),
            ),
            config_path=str(resolved_config_path),
        )
