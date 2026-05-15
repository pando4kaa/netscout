"""
Unit tests for network external API client:
  src/enrichers/external/network.py

RIPEstat Data API: ``fetch_ripestat_ip(session, ip)`` — no API key required.
"""

import unittest
from unittest.mock import MagicMock

from src.enrichers.external.network import fetch_ripestat_ip


class _Resp:
    def __init__(self, status: int, json_data=None):
        self.status = status
        self._json = json_data if json_data is not None else {}

    async def json(self, **kwargs):
        return self._json

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


def _session(get_sequence) -> MagicMock:
    """Session.get returns successive responses from ``get_sequence``."""
    s = MagicMock()
    it = iter(get_sequence)

    def _next_get(*args, **kwargs):
        try:
            return next(it)
        except StopIteration:
            return _Resp(500)

    s.get = MagicMock(side_effect=_next_get)
    return s


_NETINFO_GOOGLE = {"status": "ok", "data": {"asns": ["15169"], "prefix": "8.8.8.0/24"}}
_AS_OVERVIEW = {
    "status": "ok",
    "data": {"holder": "GOOGLE - Google LLC", "resource": "15169"},
}


class TestRipestatSuccess(unittest.IsolatedAsyncioTestCase):

    async def test_success_returns_asn(self):
        s = _session([_Resp(200, _NETINFO_GOOGLE), _Resp(200, _AS_OVERVIEW)])
        result = await fetch_ripestat_ip(s, "8.8.8.8")
        self.assertIsNotNone(result)
        self.assertEqual(result["asn"], 15169)

    async def test_success_returns_prefix(self):
        s = _session([_Resp(200, _NETINFO_GOOGLE), _Resp(200, _AS_OVERVIEW)])
        result = await fetch_ripestat_ip(s, "8.8.8.8")
        self.assertEqual(result["prefix"], "8.8.8.0/24")

    async def test_success_returns_ip(self):
        s = _session([_Resp(200, _NETINFO_GOOGLE), _Resp(200, _AS_OVERVIEW)])
        result = await fetch_ripestat_ip(s, "8.8.8.8")
        self.assertEqual(result["ip"], "8.8.8.8")

    async def test_success_holder_as_asn_name(self):
        s = _session([_Resp(200, _NETINFO_GOOGLE), _Resp(200, _AS_OVERVIEW)])
        result = await fetch_ripestat_ip(s, "8.8.8.8")
        self.assertEqual(result["asn_name"], "GOOGLE - Google LLC")

    async def test_network_info_ok_without_as_overview(self):
        s = _session([_Resp(200, _NETINFO_GOOGLE), _Resp(500)])
        result = await fetch_ripestat_ip(s, "8.8.8.8")
        self.assertIsNotNone(result)
        self.assertEqual(result["asn"], 15169)
        self.assertIsNone(result["asn_name"])


class TestRipestatErrors(unittest.IsolatedAsyncioTestCase):

    async def test_empty_asns_returns_none(self):
        s = _session([_Resp(200, {"status": "ok", "data": {"asns": [], "prefix": ""}})])
        result = await fetch_ripestat_ip(s, "192.168.1.1")
        self.assertIsNone(result)

    async def test_network_info_not_ok_returns_none(self):
        s = _session([_Resp(200, {"status": "error", "data": {}})])
        result = await fetch_ripestat_ip(s, "8.8.8.8")
        self.assertIsNone(result)

    async def test_http_500_returns_none(self):
        s = _session([_Resp(500)])
        result = await fetch_ripestat_ip(s, "8.8.8.8")
        self.assertIsNone(result)

    async def test_connection_error_returns_none(self):
        s = MagicMock()
        s.get = MagicMock(side_effect=Exception("Connection refused"))
        result = await fetch_ripestat_ip(s, "8.8.8.8")
        self.assertIsNone(result)


class TestRipestatEdgeCases(unittest.IsolatedAsyncioTestCase):

    async def test_asn_string_parsed_to_int(self):
        s = _session([_Resp(200, {"status": "ok", "data": {"asns": ["13335"], "prefix": "1.1.1.0/24"}}), _Resp(200, {"status": "ok", "data": {"holder": "CLOUDFLARENET"}})])
        result = await fetch_ripestat_ip(s, "1.1.1.1")
        self.assertEqual(result["asn"], 13335)


if __name__ == "__main__":
    unittest.main()
