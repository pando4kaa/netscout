"""
Tests for SSL Certificate Enricher
"""

import unittest
from unittest.mock import patch, MagicMock

from src.enrichers.ssl import _get_cert_info, SslEnricher


class TestSslEnricher(unittest.TestCase):
    def test_get_cert_info_with_error_returns_certificate_info(self):
        with patch("socket.create_connection") as mock_conn:
            mock_conn.side_effect = Exception("Connection refused")
            result = _get_cert_info("test.example.com")
            self.assertIsNotNone(result)
            self.assertEqual(result.host, "test.example.com")
            self.assertIsNotNone(result.error)

    def test_ssl_enricher_returns_ssl_info(self):
        with patch("src.enrichers.ssl._get_cert_info") as mock_get:
            mock_get.return_value = None
            enricher = SslEnricher()
            result = enricher.enrich("example.com")
            self.assertIn("ssl_info", result)
            self.assertIsNotNone(result["ssl_info"])
