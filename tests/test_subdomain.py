"""
Tests for the subdomain enricher.
"""

import unittest
from unittest.mock import patch

from src.enrichers.subdomain import (
    SubdomainEnricher,
    _extract_subdomains_from_crt,
)


class TestExtractSubdomainsFromCrt(unittest.TestCase):
    def test_extract_subdomains(self):
        data = [
            {"name_value": "www.example.com"},
            {"name_value": "api.example.com"},
            {"name_value": "*.example.com"},
        ]
        result = _extract_subdomains_from_crt("example.com", data)
        self.assertIn("www.example.com", result)
        self.assertIn("api.example.com", result)
        self.assertNotIn("example.com", result)

    def test_filters_wildcard(self):
        data = [{"name_value": "*.example.com"}]
        result = _extract_subdomains_from_crt("example.com", data)
        # Stripping the leading wildcard yields the apex itself, which is filtered out.
        self.assertEqual(len(result), 0)

    def test_filters_invalid(self):
        data = [
            {"name_value": "user@example.com"},
            {"name_value": "other.com"},
        ]
        result = _extract_subdomains_from_crt("example.com", data)
        self.assertEqual(len(result), 0)


class TestSubdomainEnricher(unittest.TestCase):
    @patch("src.enrichers.subdomain._fetch_passive_async")
    def test_enrich_returns_subdomains(self, mock_passive):
        async def _fake_passive(_domain):
            return {"www.example.com", "mail.example.com"}

        mock_passive.side_effect = _fake_passive
        enricher = SubdomainEnricher(enable_bruteforce=False)
        result = enricher.enrich("example.com")
        self.assertIn("subdomains", result)
        self.assertIsInstance(result["subdomains"], list)
