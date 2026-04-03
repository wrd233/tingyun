import unittest

from tingyun_adapter.normalizers.component_key_resolver import resolve_component_keys


class ComponentKeyResolverTests(unittest.TestCase):
    def test_resolve_database_component(self) -> None:
        record = {
            "bizSystemId": 1065,
            "componentType": "Database",
            "componentSubtype": "MySQL",
            "componentName": "10.190.22.21:3306",
            "metricCategory": "10.190.22.21:3306/Database-abc",
        }
        keys = resolve_component_keys(record)
        self.assertEqual(keys.biz_system_id, 1065)
        self.assertEqual(keys.component_type, "Database")
        self.assertEqual(keys.component_subtype, "MySQL")
        self.assertEqual(keys.component_name, "10.190.22.21:3306")
        self.assertEqual(keys.metric_category, "10.190.22.21:3306/Database-abc")


if __name__ == "__main__":
    unittest.main()
