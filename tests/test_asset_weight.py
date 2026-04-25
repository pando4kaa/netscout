"""
Tests for asset criticality weights.
"""

import unittest

from src.analysis.asset_weight import asset_weight, classify_asset, normalize_asset_host


class TestAssetWeight(unittest.TestCase):
    def test_normalize_url_to_host(self):
        self.assertEqual(normalize_asset_host("https://API.Example.com/path"), "api.example.com")

    def test_apex_weight(self):
        self.assertEqual(classify_asset("example.com", "example.com"), "apex")
        self.assertEqual(asset_weight("example.com", "example.com"), 1.0)

    def test_critical_service_weight(self):
        self.assertEqual(classify_asset("api.example.com", "example.com"), "critical_service")
        self.assertGreater(asset_weight("api.example.com", "example.com"), 1.0)

    def test_lower_criticality_weight(self):
        self.assertEqual(classify_asset("staging.example.com", "example.com"), "lower_criticality")
        self.assertLess(asset_weight("staging.example.com", "example.com"), 1.0)

    def test_ip_weight(self):
        self.assertEqual(classify_asset("192.0.2.10", "example.com"), "ip")
        self.assertGreater(asset_weight("192.0.2.10", "example.com"), 0.0)


if __name__ == "__main__":
    unittest.main()
