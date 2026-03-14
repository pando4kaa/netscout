"""
Tests for Subdomain Enricher
"""

import unittest
from unittest.mock import patch

from src.enrichers.subdomain import (
    _extract_subdomains_from_crt,
    SubdomainEnricher,
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
        # Wildcard *.example.com becomes example.com which is root domain, discarded
        self.assertEqual(len(result), 0)

    def test_filters_invalid(self):
        data = [
            {"name_value": "user@example.com"},
            {"name_value": "other.com"},
        ]
        result = _extract_subdomains_from_crt("example.com", data)
        self.assertEqual(len(result), 0)


class TestSubdomainEnricher(unittest.TestCase):
    @patch("src.enrichers.subdomain._fetch_crtsh_json")
    @patch("src.enrichers.subdomain._fetch_crobat")
    def test_enrich_returns_subdomains(self, mock_crobat, mock_crtsh):
        mock_crtsh.return_value = [
            {"name_value": "www.example.com"},
            {"name_value": "mail.example.com"},
        ]
        mock_crobat.return_value = set()
        enricher = SubdomainEnricher(enable_bruteforce=False)
        result = enricher.enrich("example.com")
        self.assertIn("subdomains", result)
        self.assertIsInstance(result["subdomains"], list)
