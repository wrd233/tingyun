from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional


class CapturedApiRepository:
    def __init__(self, base_dir: str | Path) -> None:
        self.base_dir = Path(base_dir)
        self.index_path = self.base_dir / "index.json"

    def exists(self) -> bool:
        return self.index_path.exists()

    def load_index(self) -> dict[str, Any]:
        return self._read_json(self.index_path)

    def list_relative_paths(self) -> list[str]:
        index = self.load_index()
        endpoints = index.get("endpoints", [])
        return [str(endpoint.get("relative_path")) for endpoint in endpoints if endpoint.get("relative_path")]

    def endpoint_path(self, relative_path: str) -> Path:
        return self.base_dir / f"{relative_path}.json"

    def load_endpoint(self, relative_path: str) -> dict[str, Any]:
        return self._read_json(self.endpoint_path(relative_path))

    def load_method_entry(self, relative_path: str, method: str = "POST") -> dict[str, Any]:
        endpoint = self.load_endpoint(relative_path)
        methods = endpoint.get("methods", {})
        if method not in methods:
            available = ", ".join(sorted(methods.keys()))
            raise KeyError(f"method {method!r} not found for {relative_path!r}; available: {available}")
        return methods[method]

    def load_first_sample_response(self, relative_path: str, method: str = "POST") -> Optional[Any]:
        method_entry = self.load_method_entry(relative_path, method)
        sample_responses = method_entry.get("sample_responses") or []
        if not sample_responses:
            return None
        return sample_responses[0].get("body")

    def load_first_sample_request(self, relative_path: str, method: str = "POST") -> Optional[dict[str, Any]]:
        method_entry = self.load_method_entry(relative_path, method)
        sample_requests = method_entry.get("sample_requests") or []
        if not sample_requests:
            return None
        return sample_requests[0]

    def find_relative_paths(self, pattern: str) -> list[str]:
        pattern_lower = pattern.lower()
        return [path for path in self.list_relative_paths() if pattern_lower in path.lower()]

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
