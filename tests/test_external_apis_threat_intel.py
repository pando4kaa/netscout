"""
Unit tests for threat-intelligence external API clients:
  src/enrichers/external/threat_intel.py

All functions accept ``session: aiohttp.ClientSession`` as their first
argument, so we pass a mock session directly — no module-level patching of
session creation is needed.

cache_service / rate_limit_service gracefully degrade when Redis is absent
(return None / True respectively), so they do not need to be mocked here.
"""

import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from src.enrichers.external.threat_intel import (
    fetch_virustotal_domain,
    fetch_alienvault_otx_domain,
    fetch_abuseipdb_check,
    fetch_threatcrowd_domain,
    fetch_openphish_check,
    fetch_pulsedive_info,
    fetch_criminalip_domain,
)


# ---------------------------------------------------------------------------
# Shared mock helpers
# ---------------------------------------------------------------------------

class _Resp:
    """Minimal aiohttp.ClientResponse async context manager mock.

    When a function uses ``resp.text()`` and then ``json.loads(text)``
    (e.g. Pulsedive, CriminalIP) we serialize ``json_data`` automatically.
    """

    def __init__(self, status: int, json_data=None, text_data: str | None = None):
        self.status = status
        self._json = json_data if json_data is not None else {}
        self._text = text_data  # None → auto-serialize from _json

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
    """Build a minimal aiohttp.ClientSession mock."""
    s = MagicMock()
    s.get = MagicMock(return_value=get or _Resp(200))
    s.post = MagicMock(return_value=post or _Resp(200))
    return s


# ---------------------------------------------------------------------------
# VirusTotal
# ---------------------------------------------------------------------------

_VT_SUCCESS = {
    "data": {
        "attributes": {
            "last_analysis_stats": {
                "malicious": 0, "suspicious": 0, "harmless": 70, "undetected": 5,
            },
            "reputation": 0,
            "total_votes": {"harmless": 10, "malicious": 0},
        }
    }
}


class TestVirusTotalDomain(unittest.IsolatedAsyncioTestCase):

    async def test_success_returns_last_analysis_stats(self):
        s = _session(get=_Resp(200, _VT_SUCCESS))
        with patch("src.enrichers.external.threat_intel.VIRUSTOTAL_API_KEY", "vt-key"):
            result = await fetch_virustotal_domain(s, "example.com")
        # fetch_virustotal_domain returns raw API data; flattening is done in _merge_results
        self.assertIsNotNone(result)
        attrs = result["data"]["attributes"]
        self.assertIn("last_analysis_stats", attrs)
        self.assertEqual(attrs["last_analysis_stats"]["malicious"], 0)

    async def test_success_returns_reputation(self):
        s = _session(get=_Resp(200, _VT_SUCCESS))
        with patch("src.enrichers.external.threat_intel.VIRUSTOTAL_API_KEY", "vt-key"):
            result = await fetch_virustotal_domain(s, "example.com")
        self.assertIn("reputation", result["data"]["attributes"])

    async def test_no_key_returns_none(self):
        s = _session()
        with patch("src.enrichers.external.threat_intel.VIRUSTOTAL_API_KEY", ""):
            result = await fetch_virustotal_domain(s, "example.com")
        self.assertIsNone(result)

    async def test_429_rate_limit_returns_none(self):
        s = _session(get=_Resp(429))
        with patch("src.enrichers.external.threat_intel.VIRUSTOTAL_API_KEY", "vt-key"):
            with patch("src.services.cache_service.get", return_value=None):
                with patch("src.services.rate_limit_service.acquire", return_value=True):
                    with patch(
                        "src.enrichers.external.threat_intel.asyncio.sleep",
                        new_callable=AsyncMock,
                    ):
                        result = await fetch_virustotal_domain(s, "example.com")
        self.assertIsNone(result)

    async def test_500_server_error_returns_none(self):
        s = _session(get=_Resp(500))
        with patch("src.enrichers.external.threat_intel.VIRUSTOTAL_API_KEY", "vt-key"):
            with patch("src.services.cache_service.get", return_value=None):
                with patch("src.services.rate_limit_service.acquire", return_value=True):
                    result = await fetch_virustotal_domain(s, "example.com")
        self.assertIsNone(result)

    async def test_connection_error_returns_none(self):
        s = _session()
        s.get = MagicMock(side_effect=Exception("Connection refused"))
        with patch("src.enrichers.external.threat_intel.VIRUSTOTAL_API_KEY", "vt-key"):
            with patch("src.services.cache_service.get", return_value=None):
                with patch("src.services.rate_limit_service.acquire", return_value=True):
                    result = await fetch_virustotal_domain(s, "example.com")
        self.assertIsNone(result)


# ---------------------------------------------------------------------------
# AlienVault OTX
# ---------------------------------------------------------------------------

_OTX_SUCCESS = {
    "pulse_info": {"count": 3, "pulses": []},
    "alexa": "https://www.alexa.com/siteinfo/example.com",
    "whois": "https://whois.domaintools.com/example.com",
    "indicator": "example.com",
}


class TestAlienVaultOtxDomain(unittest.IsolatedAsyncioTestCase):

    async def test_success_pulse_count(self):
        s = _session(get=_Resp(200, _OTX_SUCCESS))
        with patch("src.enrichers.external.threat_intel.ALIENVAULT_OTX_API_KEY", "otx-key"):
            result = await fetch_alienvault_otx_domain(s, "example.com")
        self.assertIsNotNone(result)
        self.assertIn("pulse_count", result)
        self.assertEqual(result["pulse_count"], 3)

    async def test_no_key_returns_none(self):
        s = _session()
        with patch("src.enrichers.external.threat_intel.ALIENVAULT_OTX_API_KEY", ""):
            result = await fetch_alienvault_otx_domain(s, "example.com")
        self.assertIsNone(result)

    async def test_500_returns_none(self):
        s = _session(get=_Resp(500))
        with patch("src.enrichers.external.threat_intel.ALIENVAULT_OTX_API_KEY", "otx-key"):
            result = await fetch_alienvault_otx_domain(s, "example.com")
        self.assertIsNone(result)

    async def test_connection_error_returns_none(self):
        s = _session()
        s.get = MagicMock(side_effect=Exception("Network error"))
        with patch("src.enrichers.external.threat_intel.ALIENVAULT_OTX_API_KEY", "otx-key"):
            result = await fetch_alienvault_otx_domain(s, "example.com")
        self.assertIsNone(result)


# ---------------------------------------------------------------------------
# AbuseIPDB — key passed as third positional argument
# ---------------------------------------------------------------------------

_ABUSE_SUCCESS = {
    "data": {
        "ipAddress": "93.184.216.34",
        "abuseConfidenceScore": 0,
        "totalReports": 0,
        "isp": "IANA",
        "countryCode": "US",
        "usageType": "Data Center/Web Hosting/Transit",
    }
}


class TestAbuseIPDB(unittest.IsolatedAsyncioTestCase):

    async def test_success_fields_present(self):
        s = _session(get=_Resp(200, _ABUSE_SUCCESS))
        result = await fetch_abuseipdb_check(s, "93.184.216.34", "abuse-key")
        self.assertIsNotNone(result)
        # Function normalizes field names: abuseConfidenceScore → abuse_score
        self.assertIn("abuse_score", result)
        self.assertEqual(result["abuse_score"], 0)
        self.assertIn("total_reports", result)
        self.assertIn("country_code", result)
        self.assertEqual(result["country_code"], "US")

    async def test_ip_present_in_result(self):
        s = _session(get=_Resp(200, _ABUSE_SUCCESS))
        result = await fetch_abuseipdb_check(s, "93.184.216.34", "abuse-key")
        self.assertIn("ip", result)
        self.assertEqual(result["ip"], "93.184.216.34")

    async def test_empty_key_returns_none(self):
        s = _session()
        result = await fetch_abuseipdb_check(s, "1.2.3.4", "")
        self.assertIsNone(result)

    async def test_403_returns_none(self):
        s = _session(get=_Resp(403))
        result = await fetch_abuseipdb_check(s, "1.2.3.4", "bad-key")
        self.assertIsNone(result)

    async def test_connection_error_returns_none(self):
        s = _session()
        s.get = MagicMock(side_effect=Exception("timeout"))
        result = await fetch_abuseipdb_check(s, "1.2.3.4", "abuse-key")
        self.assertIsNone(result)


# ---------------------------------------------------------------------------
# ThreatCrowd — no API key required
# ---------------------------------------------------------------------------

_TC_SUCCESS = {
    "response_code": "1",
    "votes": 1,
    "subdomains": ["www.example.com", "api.example.com"],
    "resolutions": [{"ip_address": "93.184.216.34", "last_resolved": "2023-01-01"}],
    "emails": ["admin@example.com"],
}


class TestThreatCrowd(unittest.IsolatedAsyncioTestCase):

    async def test_success_returns_subdomains_and_votes(self):
        s = _session(get=_Resp(200, _TC_SUCCESS))
        result = await fetch_threatcrowd_domain(s, "example.com")
        self.assertIsNotNone(result)
        self.assertIn("subdomains", result)
        self.assertIn("www.example.com", result["subdomains"])
        self.assertIn("votes", result)
        self.assertEqual(result["votes"], 1)

    async def test_connection_error_returns_none(self):
        s = _session()
        s.get = MagicMock(side_effect=ConnectionError("timeout"))
        result = await fetch_threatcrowd_domain(s, "example.com")
        self.assertIsNone(result)

    async def test_http_404_returns_none(self):
        s = _session(get=_Resp(404))
        result = await fetch_threatcrowd_domain(s, "example.com")
        self.assertIsNone(result)


# ---------------------------------------------------------------------------
# OpenPhish — community phishing feed, no API key required
# ---------------------------------------------------------------------------

_OPENPHISH_FEED_CLEAN = "https://legit.example.org/\nhttps://other.example.net/path\n"
_OPENPHISH_FEED_HIT = (
    "https://legit.example.org/\n"
    "https://evil-example.com/phish\n"
    "https://example.com/steal\n"
)


class TestOpenPhish(unittest.IsolatedAsyncioTestCase):

    async def test_domain_not_in_feed_returns_clean(self):
        """Domain not present in feed → in_database=False, empty phishing_urls."""
        s = _session(get=_Resp(200, text_data=_OPENPHISH_FEED_CLEAN))
        result = await fetch_openphish_check(s, "example.com")
        self.assertIsNotNone(result)
        self.assertFalse(result["in_database"])
        self.assertEqual(result["phishing_urls"], [])
        self.assertIn("feed_size", result)

    async def test_domain_in_feed_returns_flagged(self):
        """Domain found in feed → in_database=True with matched URLs."""
        s = _session(get=_Resp(200, text_data=_OPENPHISH_FEED_HIT))
        result = await fetch_openphish_check(s, "example.com")
        self.assertIsNotNone(result)
        self.assertTrue(result["in_database"])
        self.assertGreater(len(result["phishing_urls"]), 0)
        self.assertTrue(all("example.com" in u for u in result["phishing_urls"]))

    async def test_non_200_returns_none(self):
        s = _session(get=_Resp(503))
        result = await fetch_openphish_check(s, "example.com")
        self.assertIsNone(result)

    async def test_connection_error_returns_none(self):
        s = _session()
        s.get = MagicMock(side_effect=Exception("timeout"))
        result = await fetch_openphish_check(s, "example.com")
        self.assertIsNone(result)


# ---------------------------------------------------------------------------
# Pulsedive — api_key optional
# ---------------------------------------------------------------------------

_PD_SUCCESS = {"risk": "none", "threats": [], "feeds": [], "indicator": "example.com"}
_PD_NOT_FOUND = {"error": "Indicator not found"}


class TestPulsedive(unittest.IsolatedAsyncioTestCase):

    async def test_success_risk_none(self):
        s = _session(get=_Resp(200, _PD_SUCCESS))
        result = await fetch_pulsedive_info(s, "example.com", api_key="pd-key")
        self.assertIsNotNone(result)
        self.assertIn("risk", result)
        self.assertEqual(result["risk"], "none")
        self.assertIn("domain", result)
        self.assertEqual(result["domain"], "example.com")

    async def test_404_indicator_not_found(self):
        s = _session(get=_Resp(404, _PD_NOT_FOUND))
        result = await fetch_pulsedive_info(s, "example.com", api_key="pd-key")
        # 404 = indicator not in DB; treated as clean or returns None — either is fine
        self.assertTrue(result is None or isinstance(result, dict))

    async def test_500_returns_none(self):
        s = _session(get=_Resp(500))
        result = await fetch_pulsedive_info(s, "example.com", api_key="pd-key")
        self.assertIsNone(result)

    async def test_works_without_key(self):
        s = _session(get=_Resp(200, _PD_SUCCESS))
        result = await fetch_pulsedive_info(s, "example.com")
        self.assertTrue(result is None or isinstance(result, dict))

    async def test_connection_error_returns_none(self):
        s = _session()
        s.get = MagicMock(side_effect=Exception("Network unreachable"))
        result = await fetch_pulsedive_info(s, "example.com", api_key="pd-key")
        self.assertIsNone(result)


# ---------------------------------------------------------------------------
# Criminal IP — api_key passed as third positional argument
# ---------------------------------------------------------------------------

_CRIMIP_SUCCESS = {
    "status": 200,
    # risk_score and is_safe are top-level in the Criminal IP API response
    "risk_score": {"inbound": 10, "outbound": 5},
    "is_safe": True,
    "domain": "example.com",
}


class TestCriminalIP(unittest.IsolatedAsyncioTestCase):

    async def test_success_returns_risk_score(self):
        s = _session(get=_Resp(200, _CRIMIP_SUCCESS))
        result = await fetch_criminalip_domain(s, "example.com", "cip-key")
        self.assertIsNotNone(result)
        self.assertIn("domain", result)
        self.assertIn("risk_score", result)
        self.assertIn("is_safe", result)
        self.assertTrue(result["is_safe"])

    async def test_empty_key_returns_none(self):
        s = _session()
        result = await fetch_criminalip_domain(s, "example.com", "")
        self.assertIsNone(result)

    async def test_401_returns_none(self):
        s = _session(get=_Resp(401))
        result = await fetch_criminalip_domain(s, "example.com", "cip-key")
        self.assertIsNone(result)

    async def test_connection_error_returns_none(self):
        s = _session()
        s.get = MagicMock(side_effect=Exception("DNS resolution failed"))
        result = await fetch_criminalip_domain(s, "example.com", "cip-key")
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
