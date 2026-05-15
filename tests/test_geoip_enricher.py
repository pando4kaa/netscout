"""
Tests for GeoipEnricher (src/enrichers/geoip.py).

The geoip2 database Reader is mocked to avoid shipping a real .mmdb file.
"""

import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from src.enrichers.geoip import GeoipEnricher


def _make_city_response(
    country_name: str = "United States",
    country_iso: str = "US",
    city_name: str = "San Jose",
    latitude: float = 37.3382,
    longitude: float = -121.8863,
    timezone: str = "America/Los_Angeles",
    asn: int = 15169,
    asn_org: str = "GOOGLE",
) -> MagicMock:
    """Build a mock geoip2 city() response object."""
    resp = MagicMock()
    resp.country.name = country_name
    resp.country.iso_code = country_iso
    resp.city.name = city_name
    resp.location.latitude = latitude
    resp.location.longitude = longitude
    resp.location.time_zone = timezone
    resp.traits.autonomous_system_number = asn
    resp.traits.autonomous_system_organization = asn_org
    return resp


def _make_mock_reader(city_response=None, asn_response=None):
    reader = MagicMock()
    if city_response is not None:
        reader.city = MagicMock(return_value=city_response)
    else:
        reader.city = MagicMock(side_effect=Exception("no DB"))
    reader.__enter__ = MagicMock(return_value=reader)
    reader.__exit__ = MagicMock(return_value=False)
    return reader


class TestGeoipEnricherWithIps(unittest.TestCase):

    def _run(self, context: dict, reader=None):
        enricher = GeoipEnricher()
        if reader is None:
            reader = _make_mock_reader(
                city_response=_make_city_response()
            )
        with patch("src.enrichers.geoip._get_geoip_reader", return_value=reader):
            return enricher.enrich("example.com", context)

    def test_geoip_info_key_present(self):
        context = {
            "dns_info": MagicMock(a_records=["93.184.216.34"], aaaa_records=[]),
        }
        result = self._run(context)
        self.assertIn("geoip_info", result)

    def test_geoip_info_contains_ip_entry(self):
        context = {
            "dns_info": MagicMock(a_records=["93.184.216.34"], aaaa_records=[]),
        }
        result = self._run(context)
        geoip = result["geoip_info"]
        self.assertIsInstance(geoip, dict)
        self.assertIn("93.184.216.34", geoip)

    def test_ip_entry_has_country(self):
        context = {
            "dns_info": MagicMock(a_records=["93.184.216.34"], aaaa_records=[]),
        }
        result = self._run(context)
        entry = result["geoip_info"]["93.184.216.34"]
        self.assertIn("country", entry)
        self.assertEqual(entry["country"], "United States")

    def test_ip_entry_has_country_code(self):
        context = {
            "dns_info": MagicMock(a_records=["93.184.216.34"], aaaa_records=[]),
        }
        result = self._run(context)
        entry = result["geoip_info"]["93.184.216.34"]
        self.assertIn("country_code", entry)
        self.assertEqual(entry["country_code"], "US")

    def test_ip_entry_has_city(self):
        context = {
            "dns_info": MagicMock(a_records=["93.184.216.34"], aaaa_records=[]),
        }
        result = self._run(context)
        entry = result["geoip_info"]["93.184.216.34"]
        self.assertIn("city", entry)
        self.assertEqual(entry["city"], "San Jose")

    def test_ip_entry_has_coordinates(self):
        context = {
            "dns_info": MagicMock(a_records=["93.184.216.34"], aaaa_records=[]),
        }
        result = self._run(context)
        entry = result["geoip_info"]["93.184.216.34"]
        self.assertIn("latitude", entry)
        self.assertIn("longitude", entry)
        self.assertAlmostEqual(entry["latitude"], 37.3382, places=2)
        self.assertAlmostEqual(entry["longitude"], -121.8863, places=2)

    def test_ip_entry_known_fields(self):
        # _lookup_ip returns: country, country_code, city, latitude, longitude
        # ASN/timezone come from a separate database; not included in current implementation
        context = {
            "dns_info": MagicMock(a_records=["93.184.216.34"], aaaa_records=[]),
        }
        result = self._run(context)
        entry = result["geoip_info"]["93.184.216.34"]
        for field in ("country", "country_code", "city", "latitude", "longitude"):
            self.assertIn(field, entry)

    def test_multiple_ips_in_a_records(self):
        ips = ["1.1.1.1", "8.8.8.8", "9.9.9.9"]
        context = {
            "dns_info": MagicMock(a_records=ips, aaaa_records=[]),
        }
        result = self._run(context)
        geoip = result["geoip_info"]
        for ip in ips:
            self.assertIn(ip, geoip)

    def test_aaaa_records_included(self):
        context = {
            "dns_info": MagicMock(
                a_records=["93.184.216.34"],
                aaaa_records=["2606:2800:220:1:248:1893:25c8:1946"],
            ),
        }
        result = self._run(context)
        self.assertIn("geoip_info", result)


class TestGeoipEnricherNoIps(unittest.TestCase):
    """When no IP addresses are available, enrich returns {} (no geoip_info key)."""

    def _run(self, context: dict):
        enricher = GeoipEnricher()
        reader = _make_mock_reader(city_response=_make_city_response())
        with patch("src.enrichers.geoip._get_geoip_reader", return_value=reader):
            return enricher.enrich("example.com", context)

    def test_no_dns_info_in_context(self):
        # No IPs → enrich returns {} (not {"geoip_info": {}})
        result = self._run(context={})
        self.assertEqual(result, {})

    def test_none_dns_info(self):
        result = self._run(context={"dns_info": None})
        self.assertEqual(result, {})

    def test_empty_a_records_and_aaaa_records(self):
        context = {
            "dns_info": MagicMock(a_records=[], aaaa_records=[]),
        }
        result = self._run(context)
        self.assertEqual(result, {})


class TestGeoipEnricherNoDatabase(unittest.TestCase):
    """When the GeoIP database is unavailable, enricher returns {} (graceful degradation)."""

    def test_missing_db_returns_empty_dict(self):
        # No reader → return {} immediately (not {"geoip_info": {}})
        context = {
            "dns_info": MagicMock(a_records=["1.2.3.4"], aaaa_records=[]),
        }
        enricher = GeoipEnricher()
        with patch("src.enrichers.geoip._get_geoip_reader", return_value=None):
            result = enricher.enrich("example.com", context)
        self.assertEqual(result, {})

    def test_reader_raises_exception_returns_empty_dict(self):
        # reader.city() throws → all lookups fail → geoip_info is empty → return {}
        context = {
            "dns_info": MagicMock(a_records=["1.2.3.4"], aaaa_records=[]),
        }
        reader = MagicMock()
        reader.city = MagicMock(side_effect=Exception("File not found"))
        reader.close = MagicMock()
        enricher = GeoipEnricher()
        with patch("src.enrichers.geoip._get_geoip_reader", return_value=reader):
            result = enricher.enrich("example.com", context)
        self.assertIsInstance(result, dict)
        self.assertNotIn("geoip_info", result)


if __name__ == "__main__":
    unittest.main()
