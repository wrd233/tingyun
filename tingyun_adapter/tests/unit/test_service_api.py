import json
import tempfile
import unittest
from pathlib import Path

from tingyun_adapter.service.http_api import create_app


ROOT = Path(__file__).resolve().parents[2]
CAPTURED_API_DIR = ROOT.parent / "tingyun_cdp_capture" / "captured_api"


class ServiceApiTests(unittest.TestCase):
    def test_healthz_and_meta_expose_report_support_capabilities(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.local.json"
            config_path.write_text(
                json.dumps(
                    {
                        "base_url": "http://169.169.173.25:8080",
                        "captured_api_dir": str(CAPTURED_API_DIR),
                        "knowledge_dir": "../knowledge/monitored_systems",
                        "console_public_base_url": "https://console.example.com",
                        "service_public_base_url": "https://adapter.example.com",
                    }
                ),
                encoding="utf-8",
            )
            app = create_app(config_path=str(config_path))
            endpoints = {route.path: route.endpoint for route in app.routes if hasattr(route, "endpoint")}

            healthz = endpoints["/healthz"]()
            self.assertEqual(healthz["config"]["console_public_base_url"], "https://console.example.com")
            self.assertTrue(healthz["config"]["knowledge_dir"].endswith("knowledge/monitored_systems"))

            meta = endpoints["/v1/meta"]()
            self.assertEqual(meta["console_public_base_url"], "https://console.example.com")
            self.assertIn("screenshot_index_pack", meta["pack_types"])
            self.assertIn("knowledge_context_pack", meta["pack_types"])
            self.assertIn("trace_sql_pack", meta["pack_types"])
            self.assertIn("trace_execution_pack", meta["pack_types"])
            self.assertIn("deployment_inventory_pack", meta["pack_types"])
            self.assertIn("data_export_pack", meta["pack_types"])


if __name__ == "__main__":
    unittest.main()
