from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from typing import Optional

from .constants import DEFAULT_BASE_URL, DEFAULT_LANG, DEFAULT_TIMEOUT_SECONDS, DEFAULT_TIMEZONE


def _project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _load_config_file(config_path: Path) -> dict[str, Any]:
    if not config_path.exists():
        return {}
    with config_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise RuntimeError(f"Adapter config must be a JSON object: {config_path}")
    return payload


def _resolve_optional_path(base_dir: Path, value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = (base_dir / path).resolve()
    return str(path)


@dataclass(frozen=True)
class AdapterSettings:
    base_url: str = DEFAULT_BASE_URL
    token: Optional[str] = None
    token_env: str = "TINGYUN_TOKEN"
    lang: str = DEFAULT_LANG
    timezone: str = DEFAULT_TIMEZONE
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS
    captured_api_dir: Optional[str] = None
    config_path: Optional[str] = None

    @classmethod
    def default_config_path(cls) -> Path:
        return _project_root() / "config.local.json"

    @classmethod
    def from_env(cls, config_path: Optional[str] = None) -> "AdapterSettings":
        resolved_config_path = Path(config_path).expanduser() if config_path else cls.default_config_path()
        raw = _load_config_file(resolved_config_path)
        token_env = os.environ.get("TINGYUN_TOKEN_ENV", raw.get("token_env", "TINGYUN_TOKEN"))
        token = (
            os.environ.get(token_env)
            or os.environ.get("TINGYUN_TOKEN")
            or os.environ.get("TOKEN")
            or raw.get("token")
        )
        captured_api_dir = os.environ.get("TINGYUN_CAPTURED_API_DIR", raw.get("captured_api_dir"))
        return cls(
            base_url=os.environ.get("TINGYUN_BASE_URL", raw.get("base_url", DEFAULT_BASE_URL)),
            token=token,
            token_env=token_env,
            lang=os.environ.get("TINGYUN_LANG", raw.get("lang", DEFAULT_LANG)),
            timezone=os.environ.get("TINGYUN_TIMEZONE", raw.get("timezone", DEFAULT_TIMEZONE)),
            timeout_seconds=int(
                os.environ.get("TINGYUN_TIMEOUT_SECONDS", raw.get("timeout_seconds", DEFAULT_TIMEOUT_SECONDS))
            ),
            captured_api_dir=_resolve_optional_path(resolved_config_path.parent, captured_api_dir),
            config_path=str(resolved_config_path),
        )
