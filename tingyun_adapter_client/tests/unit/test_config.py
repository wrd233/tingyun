from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tingyun_adapter_client.config import RemoteClientSettings


class RemoteClientSettingsTest(unittest.TestCase):
    def test_default_config_path_points_to_client_project(self) -> None:
        self.assertEqual(
            str(RemoteClientSettings.default_config_path()),
            "/Users/wangrundong/work/mywork/tingyun_adapter_client/config.local.json",
        )

    def test_loads_config_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.local.json"
            config_path.write_text(
                json.dumps(
                    {
                        "service_base_url": "http://127.0.0.1:8000/",
                        "service_api_key": "abc123",
                        "timeout_seconds": 15,
                        "default_source_mode": "live",
                    }
                ),
                encoding="utf-8",
            )
            settings = RemoteClientSettings.from_env(str(config_path))
        self.assertEqual(settings.service_base_url, "http://127.0.0.1:8000")
        self.assertEqual(settings.service_api_key, "abc123")
        self.assertEqual(settings.timeout_seconds, 15)
        self.assertEqual(settings.default_source_mode, "live")
