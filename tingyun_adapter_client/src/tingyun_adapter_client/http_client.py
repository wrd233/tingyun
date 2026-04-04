from __future__ import annotations

import json
from typing import Any
from urllib import error, request

from .config import RemoteClientSettings


class AdapterRemoteClient:
    def __init__(self, settings: RemoteClientSettings) -> None:
        self.settings = settings

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.settings.service_api_key:
            headers["X-Adapter-API-Key"] = self.settings.service_api_key
        return headers

    def _request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        body = None
        if payload is not None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = request.Request(
            f"{self.settings.service_base_url}{path}",
            data=body,
            headers=self._headers(),
            method=method,
        )
        try:
            with request.urlopen(req, timeout=self.settings.timeout_seconds) as response:
                raw = response.read().decode("utf-8")
        except error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"HTTP {exc.code}: {raw}") from exc
        except error.URLError as exc:
            raise RuntimeError(f"Network error: {exc.reason}") from exc
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Service did not return valid JSON: {raw[:300]}") from exc

    def healthz(self) -> dict[str, Any]:
        return self._request("GET", "/healthz")

    def meta(self) -> dict[str, Any]:
        return self._request("GET", "/v1/meta")

    def build_pack(self, pack_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", f"/v1/packs/{pack_type}", payload=payload)
