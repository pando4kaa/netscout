"""
Tests for WHOIS Enricher
"""

import unittest
from unittest.mock import patch, MagicMock

from src.enrichers.whois import WhoisEnricher, _normalize_date, _parse_compact_date, _parse_whois_raw


class TestWhoisNormalizeDate(unittest.TestCase):
    def test_normalize_compact_format(self):
        self.assertEqual(_parse_compact_date("20090716153419"), "2009-07-16")
        self.assertEqual(_parse_compact_date("0-UANIC 20090716153419"), "2009-07-16")
        self.assertEqual(_parse_compact_date("20260716153413"), "2026-07-16")

    def test_normalize_date_none(self):
        self.assertIsNone(_normalize_date(None))

    def test_normalize_date_datetime(self):
        from datetime import datetime
        self.assertEqual(_normalize_date(datetime(2020, 5, 15)), "2020-05-15")


class TestWhoisParseRaw(unittest.TestCase):
    def test_parse_raw_creates_info(self):
        raw = """
domain: example.com
creation date: 2009-07-16 15:34:19
expiration date: 2026-07-16 15:34:13
nserver: ns1.example.com
status: ok
"""
        info = _parse_whois_raw(raw, "example.com")
        self.assertIsNotNone(info)
        self.assertEqual(info.domain, "example.com")
        self.assertEqual(info.creation_date, "2009-07-16")
        self.assertEqual(info.expiration_date, "2026-07-16")
        self.assertIn("ns1.example.com", info.name_servers)


class TestWhoisEnricher(unittest.TestCase):
    @patch("src.enrichers.whois.whois")
    def test_enrich_returns_whois_info(self, mock_whois):
        mock_whois.whois.return_value = MagicMock(
            creation_date="2020-01-15",
            expiration_date="2025-01-15",
            registrar="Test Registrar",
            name_servers=["ns1.test.com"],
            emails=["admin@test.com"],
            status="active",
        )
        enricher = WhoisEnricher()
        result = enricher.enrich("example.com")
        self.assertIn("whois_info", result)
        self.assertEqual(result["whois_info"].domain, "example.com")
