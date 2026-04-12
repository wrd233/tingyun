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
            raise RuntimeError("Missing Tingyun token. Set token, config.local.json token, or export TINGYUN_TOKEN.")
        return self.token

    def _headers(self, content_type: str) -> dict[str, str]:
        return {
            "Accept": "application/json, text/plain, */*",
            "Authorization": f"Bearer {self.require_token()}",
            "BuiltInRequestId": str(uuid.uuid4()),
            "Content-Type": content_type,
        }

    def _build_url(self, path: str, query: Optional[dict[str, Any]] = None) -> str:
        url = f"{self.base_url}{path}"
        if query:
            url = f"{url}?{urlencode(query, doseq=True)}"
        return url

    def post_form(self, path: str, form: dict[str, Any], query: Optional[dict[str, Any]] = None) -> Any:
        url = self._build_url(path, query)
        request = Request(
            url,
            data=urlencode(form, doseq=True).encode("utf-8"),
            headers=self._headers("application/x-www-form-urlencoded"),
            method="POST",
        )
        return self._execute(request)

    def post_json(self, path: str, payload: dict[str, Any], query: Optional[dict[str, Any]] = None) -> Any:
        url = self._build_url(path, query)
        request = Request(
            url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers=self._headers("application/json"),
            method="POST",
        )
        return self._execute(request)

    def get(self, path: str, query: Optional[dict[str, Any]] = None) -> Any:
        url = self._build_url(path, query)
        request = Request(url, headers=self._headers("application/json"), method="GET")
        return self._execute(request)

    def post_form_raw(self, path: str, form: dict[str, Any], query: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        url = self._build_url(path, query)
        request = Request(
            url,
            data=urlencode(form, doseq=True).encode("utf-8"),
            headers=self._headers("application/x-www-form-urlencoded"),
            method="POST",
        )
        return self._execute_raw(request)

    def post_json_raw(self, path: str, payload: dict[str, Any], query: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        url = self._build_url(path, query)
        request = Request(
            url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers=self._headers("application/json"),
            method="POST",
        )
        return self._execute_raw(request)

    def get_raw(self, path: str, query: Optional[dict[str, Any]] = None, *, content_type: str = "application/json") -> dict[str, Any]:
        url = self._build_url(path, query)
        request = Request(url, headers=self._headers(content_type), method="GET")
        return self._execute_raw(request)

    def _execute(self, request: Request) -> Any:
        with urlopen(request, timeout=self.timeout) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            body = response.read().decode(charset, errors="replace")
        return json.loads(body)

    def _execute_raw(self, request: Request) -> dict[str, Any]:
        with urlopen(request, timeout=self.timeout) as response:
            body = response.read()
            headers = {key: value for key, value in response.headers.items()}
            return {
                "status": getattr(response, "status", None),
                "url": response.geturl(),
                "headers": headers,
                "mime_type": response.headers.get_content_type(),
                "charset": response.headers.get_content_charset(),
                "body_bytes": body,
            }
