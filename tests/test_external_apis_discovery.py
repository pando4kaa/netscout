"""
Unit tests for discovery external API clients:
  src/enrichers/external/discovery.py

Functions accept ``session`` as first argument; API keys are passed as
positional/keyword args where required or read from module-level constants.
"""

import unittest
from unittest.mock import MagicMock, patch

from src.enrichers.external.discovery import (
    fetch_urlscan_search,
    fetch_securitytrails_domain,
    fetch_zoomeye_search,
    fetch_wayback_first_snapshot,
    fetch_ssllabs_analyze,
)


# ---------------------------------------------------------------------------
# Shared mock helpers
# ---------------------------------------------------------------------------

class _Resp:
    def __init__(self, status: int, json_data=None, text_data: str | None = None):
        self.status = status
        self._json = json_data if json_data is not None else {}
        self._text = text_data

    async def json(self, **kwargs):
        return self._json

    async def text(self):
        if self._text is not None:
            return self._text
        import json as _json
        return _json.dumps(self._json) if self._json else ""

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


def _session(get=None, post=None) -> MagicMock:
    s = MagicMock()
    s.get = MagicMock(return_value=get or _Resp(200))
    s.post = MagicMock(return_value=post or _Resp(200))
    return s


# ---------------------------------------------------------------------------
# URLScan — no API key required
# ---------------------------------------------------------------------------

_URLSCAN_SUCCESS = {
    "total": 5,
    "results": [
        {"page": {"url": "https://example.com", "status": "200"}, "_id": "a"},
        {"page": {"url": "https://www.example.com", "status": "200"}, "_id": "b"},
    ],
}


class TestURLScan(unittest.IsolatedAsyncioTestCase):

    async def test_success_total_and_urls(self):
        s = _session(get=_Resp(200, _URLSCAN_SUCCESS))
        result = await fetch_urlscan_search(s, "example.com")
        self.assertIsNotNone(result)
        self.assertIn("total", result)
        self.assertEqual(result["total"], 5)
        self.assertIn("urls", result)
        self.assertGreater(len(result["urls"]), 0)

    async def test_429_rate_limit_returns_none(self):
        s = _session(get=_Resp(429))
        result = await fetch_urlscan_search(s, "example.com")
        self.assertIsNone(result)

    async def test_empty_results_returns_zero_total(self):
        s = _session(get=_Resp(200, {"total": 0, "results": []}))
        result = await fetch_urlscan_search(s, "example.com")
        self.assertIsNotNone(result)
        self.assertEqual(result["total"], 0)

    async def test_connection_error_returns_none(self):
        s = _session()
        s.get = MagicMock(side_effect=Exception("timeout"))
        result = await fetch_urlscan_search(s, "example.com")
        self.assertIsNone(result)


# ---------------------------------------------------------------------------
# SecurityTrails — api_key passed as third positional arg
# ---------------------------------------------------------------------------

_ST_SUCCESS = {
    "subdomain_count": 10,
    "current_dns": {"a": {"values": [{"ip": "93.184.216.34"}]}},
    "tags": ["ecommerce"],
}


class TestSecurityTrails(unittest.IsolatedAsyncioTestCase):

    async def test_success_subdomain_count(self):
        s = _session(get=_Resp(200, _ST_SUCCESS))
        result = await fetch_securitytrails_domain(s, "example.com", "st-key")
        self.assertIsNotNone(result)
        self.assertIn("subdomain_count", result)
        self.assertEqual(result["subdomain_count"], 10)

    async def test_empty_key_returns_none(self):
        s = _session()
        result = await fetch_securitytrails_domain(s, "example.com", "")
        self.assertIsNone(result)

    async def test_403_forbidden_returns_none(self):
        s = _session(get=_Resp(403))
        result = await fetch_securitytrails_domain(s, "example.com", "st-key")
        self.assertIsNone(result)

    async def test_connection_error_returns_none(self):
        s = _session()
        s.get = MagicMock(side_effect=Exception("Connection timeout"))
        result = await fetch_securitytrails_domain(s, "example.com", "st-key")
        self.assertIsNone(result)


# ---------------------------------------------------------------------------
# ZoomEye — api_key passed as third positional arg
# ---------------------------------------------------------------------------

_ZE_SUCCESS = {
    "total": 2,
    "matches": [
        {"ip": "1.2.3.4", "portinfo": {"port": 443, "app": "nginx"},
         "geoinfo": {"country": {"names": {"en": "United States"}}}},
        {"ip": "5.6.7.8", "portinfo": {"port": 80, "app": "Apache"},
         "geoinfo": {"country": {"names": {"en": "Germany"}}}},
    ]
}


class TestZoomEye(unittest.IsolatedAsyncioTestCase):

    async def test_success_total_and_hosts(self):
        s = _session(get=_Resp(200, _ZE_SUCCESS))
        result = await fetch_zoomeye_search(s, "example.com", "ze-key")
        self.assertIsNotNone(result)
        self.assertIn("total", result)
        self.assertEqual(result["total"], 2)
        self.assertIn("hosts", result)
        self.assertEqual(result["hosts"][0]["ip"], "1.2.3.4")

    async def test_empty_key_returns_none(self):
        s = _session()
        result = await fetch_zoomeye_search(s, "example.com", "")
        self.assertIsNone(result)

    async def test_401_returns_none(self):
        s = _session(get=_Resp(401))
        result = await fetch_zoomeye_search(s, "example.com", "ze-key")
        self.assertIsNone(result)

    async def test_connection_error_returns_none(self):
        s = _session()
        s.get = MagicMock(side_effect=Exception("timeout"))
        result = await fetch_zoomeye_search(s, "example.com", "ze-key")
        self.assertIsNone(result)


# ---------------------------------------------------------------------------
# Wayback Machine — no API key, CDX API
# ---------------------------------------------------------------------------

_WB_CDX_SUCCESS = [
    ["urlkey", "timestamp", "original", "mimetype", "statuscode", "digest", "length"],
    ["com,example)/", "20100101000000", "http://example.com/",
     "text/html", "200", "SHA1:abc", "1234"],
]

_WB_CDX_EMPTY = [
    ["urlkey", "timestamp", "original", "mimetype", "statuscode", "digest", "length"],
]


class TestWaybackMachine(unittest.IsolatedAsyncioTestCase):

    async def test_success_first_snapshot_timestamp(self):
        s = _session(get=_Resp(200, _WB_CDX_SUCCESS))
        result = await fetch_wayback_first_snapshot(s, "example.com")
        self.assertIsNotNone(result)
        self.assertIn("first_snapshot_timestamp", result)
        self.assertEqual(result["first_snapshot_timestamp"], "20100101000000")

    async def test_no_snapshots_returns_error_dict(self):
        s = _session(get=_Resp(200, _WB_CDX_EMPTY))
        result = await fetch_wayback_first_snapshot(s, "example.com")
        self.assertIsNotNone(result)
        self.assertIn("error", result)

    async def test_connection_error_returns_error_dict(self):
        s = _session()
        s.get = MagicMock(side_effect=Exception("Network unavailable"))
        result = await fetch_wayback_first_snapshot(s, "example.com")
        self.assertIsNotNone(result)
        self.assertIn("error", result)

    async def test_domain_present_in_result(self):
        s = _session(get=_Resp(200, _WB_CDX_SUCCESS))
        result = await fetch_wayback_first_snapshot(s, "example.com")
        self.assertIn("domain", result)
        self.assertEqual(result["domain"], "example.com")


# ---------------------------------------------------------------------------
# SSL Labs — no API key
# ---------------------------------------------------------------------------

_SSLLABS_READY = {
    "status": "READY",
    "host": "example.com",
    "grade": "A",
    "endpoints": [{
        "grade": "A",
        "ipAddress": "93.184.216.34",
        "details": {
            "protocols": [
                {"name": "TLS", "version": "1.3"},
                {"name": "TLS", "version": "1.2"},
            ],
        },
    }],
}

_SSLLABS_WEAK = {
    "status": "READY",
    "host": "example.com",
    "grade": "C",
    "endpoints": [{
        "grade": "C",
        "ipAddress": "1.2.3.4",
        "details": {
            # _WEAK_TLS_PROTOCOLS = ('SSL 3.0', 'TLS 1.0', 'TLS 1.1')
            # The code checks protocol["name"] against this tuple
            "protocols": [
                {"name": "TLS 1.0"},
                {"name": "SSL 3.0"},
            ],
        },
    }],
}


class TestSSLLabs(unittest.IsolatedAsyncioTestCase):

    async def test_success_grade_a(self):
        s = _session(get=_Resp(200, _SSLLABS_READY))
        result = await fetch_ssllabs_analyze(s, "example.com")
        self.assertIsNotNone(result)
        self.assertIn("grade", result)
        self.assertEqual(result["grade"], "A")

    async def test_no_weak_protocols_when_only_tls12_13(self):
        s = _session(get=_Resp(200, _SSLLABS_READY))
        result = await fetch_ssllabs_analyze(s, "example.com")
        self.assertIn("has_weak_protocols", result)
        self.assertFalse(result["has_weak_protocols"])

    async def test_weak_protocol_tls10_detected(self):
        s = _session(get=_Resp(200, _SSLLABS_WEAK))
        result = await fetch_ssllabs_analyze(s, "example.com")
        self.assertIn("has_weak_protocols", result)
        self.assertTrue(result["has_weak_protocols"])

    async def test_server_error_returns_error_dict(self):
        s = _session(get=_Resp(500))
        result = await fetch_ssllabs_analyze(s, "example.com")
        self.assertIsNotNone(result)
        self.assertIn("error", result)

    async def test_domain_present_in_result(self):
        s = _session(get=_Resp(200, _SSLLABS_READY))
        result = await fetch_ssllabs_analyze(s, "example.com")
        self.assertIn("domain", result)

    async def test_connection_error_returns_error_dict(self):
        s = _session()
        s.get = MagicMock(side_effect=Exception("SSL connection error"))
        result = await fetch_ssllabs_analyze(s, "example.com")
        self.assertIn("error", result)


if __name__ == "__main__":
    unittest.main()
