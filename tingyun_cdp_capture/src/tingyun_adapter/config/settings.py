from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from .constants import DEFAULT_BASE_URL, DEFAULT_LANG, DEFAULT_TIMEOUT_SECONDS, DEFAULT_TIMEZONE


@dataclass(frozen=True)
class AdapterSettings:
    base_url: str = DEFAULT_BASE_URL
    token_env: str = "TINGYUN_TOKEN"
    lang: str = DEFAULT_LANG
    timezone: str = DEFAULT_TIMEZONE
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS
    captured_api_dir: Optional[str] = None

    @classmethod
    def from_env(cls) -> "AdapterSettings":
        return cls(
            base_url=os.environ.get("TINGYUN_BASE_URL", DEFAULT_BASE_URL),
            token_env=os.environ.get("TINGYUN_TOKEN_ENV", "TINGYUN_TOKEN"),
            lang=os.environ.get("TINGYUN_LANG", DEFAULT_LANG),
            timezone=os.environ.get("TINGYUN_TIMEZONE", DEFAULT_TIMEZONE),
            timeout_seconds=int(os.environ.get("TINGYUN_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS)),
            captured_api_dir=os.environ.get("TINGYUN_CAPTURED_API_DIR"),
        )
