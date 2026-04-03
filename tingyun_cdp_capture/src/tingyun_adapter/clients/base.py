from __future__ import annotations

import json
import os
import uuid
from typing import Any, Optional
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from tingyun_adapter.config.constants import DEFAULT_LANG, DEFAULT_TIMEOUT_SECONDS


class BaseClient:
    def __init__(
        self,
        *,
        base_url: str,
        token: Optional[str] = None,
        token_env: str = "TINGYUN_TOKEN",
        timeout: int = DEFAULT_TIMEOUT_SECONDS,
        lang: str = DEFAULT_LANG,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token or os.environ.get(token_env) or os.environ.get("TOKEN")
        self.timeout = timeout
        self.lang = lang

    def require_token(self) -> str:
        if not self.token:
            raise RuntimeError("Missing Tingyun token. Set token or export TINGYUN_TOKEN.")
        return self.token

    def _headers(self, content_type: str) -> dict[str, str]:
        return {
            "Accept": "application/json, text/plain, */*",
            "Authorization": f"Bearer {self.require_token()}",
            "BuiltInRequestId": str(uuid.uuid4()),
            "Content-Type": content_type,
        }

    def post_form(self, path: str, form: dict[str, Any], query: Optional[dict[str, Any]] = None) -> Any:
        url = f"{self.base_url}{path}"
        if query:
            url = f"{url}?{urlencode(query, doseq=True)}"
        request = Request(
            url,
            data=urlencode(form, doseq=True).encode("utf-8"),
            headers=self._headers("application/x-www-form-urlencoded"),
            method="POST",
        )
        return self._execute(request)

    def post_json(self, path: str, payload: dict[str, Any], query: Optional[dict[str, Any]] = None) -> Any:
        url = f"{self.base_url}{path}"
        if query:
            url = f"{url}?{urlencode(query, doseq=True)}"
        request = Request(
            url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers=self._headers("application/json"),
            method="POST",
        )
        return self._execute(request)

    def get(self, path: str, query: Optional[dict[str, Any]] = None) -> Any:
        url = f"{self.base_url}{path}"
        if query:
            url = f"{url}?{urlencode(query, doseq=True)}"
        request = Request(url, headers=self._headers("application/json"), method="GET")
        return self._execute(request)

    def _execute(self, request: Request) -> Any:
        with urlopen(request, timeout=self.timeout) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            body = response.read().decode(charset, errors="replace")
        return json.loads(body)
