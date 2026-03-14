"""
Tests for Port Scanner Enricher
"""

import unittest
from unittest.mock import patch, MagicMock

from src.enrichers.port import _scan_port, PortEnricher


class TestPortScanner(unittest.TestCase):
    @patch("src.enrichers.port.socket.socket")
    def test_scan_port_closed_returns_none(self, mock_socket):
        mock_sock = MagicMock()
        mock_socket.return_value = mock_sock
        mock_sock.connect_ex.return_value = 1  # Connection refused
        result = _scan_port("127.0.0.1", 80)
        self.assertIsNone(result)

    @patch("src.enrichers.port.socket.socket")
    def test_scan_port_open_returns_open_port(self, mock_socket):
        mock_sock = MagicMock()
        mock_socket.return_value = mock_sock
        mock_sock.connect_ex.return_value = 0
        mock_sock.recv.return_value = b"HTTP/1.1 200 OK"  # Banner grabbing
        result = _scan_port("127.0.0.1", 80)
        self.assertIsNotNone(result)
        self.assertEqual(result.port, 80)
        self.assertEqual(result.service, "http")


class TestPortEnricher(unittest.TestCase):
    def test_enrich_returns_port_scan_without_context(self):
        enricher = PortEnricher()
        result = enricher.enrich("example.com", {})
        self.assertIn("port_scan", result)
        self.assertEqual(result["port_scan"], [])
