"""
Integration tests for external API clients — REAL HTTP calls.

These tests hit live external services without mocking.
They verify that:
  1. The endpoint URLs are still correct.
  2. The API response format matches what the parsers expect.
  3. The function returns a properly structured result (not None) for known inputs.

Skipping rules:
  - ALL tests are skipped automatically when the test machine has no internet access
    (checked at module import time via a DNS resolution attempt).
  - Tests that require a paid/private API key are skipped unless that key
    is present in the environment (loaded from .env by src.config.settings).
  - Tests that use free APIs (RIPEstat, Wayback, URLScan, ThreatCrowd, SSLLabs)
    run whenever network is available.

Target inputs:
  - domain: example.com  (IANA, stable DNS, valid SSL, long history)
  - ip:     8.8.8.8      (Google Public DNS, well-known ASN)

Run with:
  pytest tests/test_external_apis_integration.py -v -m integration
Add to pytest.ini:
  markers = integration: live network calls to real external APIs
"""

import asyncio
import os
import socket
import unittest

import aiohttp

# ---------------------------------------------------------------------------
# Detect network availability (DNS resolution attempt)
# ---------------------------------------------------------------------------

def _network_available() -> bool:
    """Check internet availability using a reliable host."""
    try:
        socket.setdefaulttimeout(5)
        socket.getaddrinfo("google.com", 443)
        return True
    except OSError:
        return False


def _host_resolvable(host: str) -> bool:
    try:
        socket.setdefaulttimeout(4)
        socket.getaddrinfo(host, 443)
        return True
    except OSError:
        return False


_HAS_NETWORK = _network_available()
_HAS_RIPESTAT = _HAS_NETWORK and _host_resolvable("stat.ripe.net")
_HAS_ZOOMEYE = _HAS_NETWORK and _host_resolvable("api.zoomeye.ai")

_SKIP_NO_NETWORK = unittest.skipUnless(
    _HAS_NETWORK,
    "No internet access — integration tests require a live network connection.",
)
_SKIP_RIPESTAT = unittest.skipUnless(
    _HAS_RIPESTAT,
    "stat.ripe.net is not reachable (RIPEstat unavailable).",
)
_SKIP_ZOOMEYE = unittest.skipUnless(
    _HAS_ZOOMEYE,
    "api.zoomeye.ai is not reachable (geographically restricted or DNS unavailable).",
)

from src.enrichers.external.threat_intel import (
    fetch_virustotal_domain,
    fetch_alienvault_otx_domain,
    fetch_abuseipdb_check,
    fetch_threatcrowd_domain,
    fetch_openphish_check,
    fetch_pulsedive_info,
    fetch_criminalip_domain,
)
from src.enrichers.external.discovery import (
    fetch_urlscan_search,
    fetch_securitytrails_domain,
    fetch_zoomeye_search,
    fetch_wayback_first_snapshot,
    fetch_ssllabs_analyze,
)
from src.enrichers.external.network import fetch_ripestat_ip

# ---------------------------------------------------------------------------
# Load API keys from .env (via settings, or directly from env)
# ---------------------------------------------------------------------------

try:
    from src.config.settings import (
        VIRUSTOTAL_API_KEY,
        ALIENVAULT_OTX_API_KEY,
        ABUSEIPDB_API_KEY,
        SECURITYTRAILS_API_KEY,
        ZOOMEYE_API_KEY,
        PULSEDIVE_API_KEY,
        CRIMINALIP_API_KEY,
    )
except Exception:
    VIRUSTOTAL_API_KEY = os.getenv("VIRUSTOTAL_API_KEY", "")
    ALIENVAULT_OTX_API_KEY = os.getenv("ALIENVAULT_OTX_API_KEY", "")
    ABUSEIPDB_API_KEY = os.getenv("ABUSEIPDB_API_KEY", "")
    SECURITYTRAILS_API_KEY = os.getenv("SECURITYTRAILS_API_KEY", "")
    ZOOMEYE_API_KEY = os.getenv("ZOOMEYE_API_KEY", "")
    PULSEDIVE_API_KEY = os.getenv("PULSEDIVE_API_KEY", "")
    CRIMINALIP_API_KEY = os.getenv("CRIMINALIP_API_KEY", "")

_DOMAIN = "example.com"
_IP = "8.8.8.8"
_TIMEOUT = aiohttp.ClientTimeout(total=30)


def _new_session(timeout: aiohttp.ClientTimeout = _TIMEOUT) -> aiohttp.ClientSession:
    """Build a session with ThreadedResolver to avoid aiodns/c-ares issues on Windows."""
    connector = aiohttp.TCPConnector(resolver=aiohttp.resolver.ThreadedResolver())
    return aiohttp.ClientSession(
        headers={"User-Agent": "NetScout-Test/1.0"},
        timeout=timeout,
        connector=connector,
    )


# ---------------------------------------------------------------------------
# Free APIs — run when network is available (no key required)
# ---------------------------------------------------------------------------

@_SKIP_RIPESTAT
class TestRipestatIntegration(unittest.IsolatedAsyncioTestCase):
    """RIPE NCC RIPEstat Data API — no API key."""

    async def test_returns_asn_for_google_dns(self):
        async with _new_session() as s:
            result = await fetch_ripestat_ip(s, _IP)

        self.assertIsNotNone(result, "RIPEstat returned None for 8.8.8.8")
        self.assertIn("asn", result)
        self.assertIsNotNone(result["asn"])
        self.assertIn(result["asn"], [15169, 36492, 36384, 19527],
                      f"Unexpected ASN for 8.8.8.8: {result['asn']}")

    async def test_result_contains_prefix(self):
        async with _new_session() as s:
            result = await fetch_ripestat_ip(s, _IP)
        self.assertIn("prefix", result)
        self.assertIsNotNone(result["prefix"])
        self.assertIn("8.8.8", result["prefix"])

    async def test_result_ip_matches_queried(self):
        async with _new_session() as s:
            result = await fetch_ripestat_ip(s, _IP)
        self.assertEqual(result["ip"], _IP)

    async def test_asn_name_from_holder(self):
        async with _new_session() as s:
            result = await fetch_ripestat_ip(s, _IP)
        self.assertIsNotNone(result.get("asn_name"))
        self.assertIn("Google", result["asn_name"])

    async def test_invalid_ip_returns_none(self):
        async with _new_session() as s:
            result = await fetch_ripestat_ip(s, "0.0.0.0")
        self.assertIsNone(result)


@_SKIP_NO_NETWORK
class TestURLScanIntegration(unittest.IsolatedAsyncioTestCase):
    """URLScan.io is free (rate-limited). Runs when network is available."""

    async def test_returns_results_for_example_com(self):
        async with _new_session() as s:
            result = await fetch_urlscan_search(s, _DOMAIN)

        self.assertIsNotNone(result, "URLScan returned None for example.com")
        self.assertIn("total", result)
        self.assertIsInstance(result["total"], int)
        self.assertGreaterEqual(result["total"], 0)

    async def test_result_has_urls_list(self):
        async with _new_session() as s:
            result = await fetch_urlscan_search(s, _DOMAIN)
        self.assertIn("urls", result)
        self.assertIsInstance(result["urls"], list)


@_SKIP_NO_NETWORK
class TestWaybackMachineIntegration(unittest.IsolatedAsyncioTestCase):
    """Wayback Machine CDX API is free. Runs when network is available."""

    async def test_example_com_has_snapshots(self):
        async with _new_session() as s:
            result = await fetch_wayback_first_snapshot(s, _DOMAIN)

        self.assertIsNotNone(result)
        # Wayback Machine may fail due to SSL/timeout/network issues
        if "error" in result:
            self.skipTest(
                f"Wayback Machine unavailable: {result['error'][:80] or 'connection error'}"
            )
        self.assertIn("first_snapshot_timestamp", result)
        # example.com has been archived since the late 1990s
        ts = result["first_snapshot_timestamp"]
        self.assertIsInstance(ts, str)
        self.assertGreater(len(ts), 0)
        # Year should be in the 1990s-2000s range
        year = int(ts[:4])
        self.assertGreaterEqual(year, 1996)
        self.assertLessEqual(year, 2010)

    async def test_result_domain_matches(self):
        async with _new_session() as s:
            result = await fetch_wayback_first_snapshot(s, _DOMAIN)
        self.assertEqual(result["domain"], _DOMAIN)


@_SKIP_NO_NETWORK
class TestSSLLabsIntegration(unittest.IsolatedAsyncioTestCase):
    """SSL Labs API is free for non-commercial use. Runs when network is available.

    Note: SSL Labs assessment can take 1-5 minutes for fresh scans.
    We use max_age to retrieve cached results if available.
    """

    async def asyncSetUp(self):
        # SSL Labs can be slow — allow a 120 second timeout for this test class
        self._timeout = aiohttp.ClientTimeout(total=120)

    async def test_example_com_grade_returned(self):
        async with _new_session(timeout=self._timeout) as s:
            result = await fetch_ssllabs_analyze(s, _DOMAIN)

        # Either a grade or an error (if API throttles or delays)
        self.assertIsNotNone(result)
        if "error" not in result:
            self.assertIn("grade", result)
            # example.com should have at least a decent grade
            self.assertIn(result["grade"], ["A+", "A", "A-", "B", "C", "T", "M"])
            self.assertIn("has_weak_protocols", result)
            self.assertIsInstance(result["has_weak_protocols"], bool)


@_SKIP_NO_NETWORK
class TestThreatCrowdIntegration(unittest.IsolatedAsyncioTestCase):
    """ThreatCrowd is free. Results may vary as service is largely deprecated."""

    async def test_example_com_returns_dict_or_none(self):
        async with _new_session() as s:
            result = await fetch_threatcrowd_domain(s, _DOMAIN)
        # ThreatCrowd may be rate-limited or deprecated — None is acceptable
        self.assertTrue(result is None or isinstance(result, dict))

    async def test_result_structure_if_available(self):
        async with _new_session() as s:
            result = await fetch_threatcrowd_domain(s, _DOMAIN)
        if result is not None:
            # When available, must contain expected keys
            self.assertTrue(
                "subdomains" in result or "votes" in result,
                f"Unexpected structure: {list(result.keys())}",
            )


# ---------------------------------------------------------------------------
# API-key-dependent tests — skipped unless key is configured AND network available
# ---------------------------------------------------------------------------

@_SKIP_NO_NETWORK
class TestVirusTotalIntegration(unittest.IsolatedAsyncioTestCase):

    @unittest.skipUnless(VIRUSTOTAL_API_KEY, "VIRUSTOTAL_API_KEY not configured")
    async def test_example_com_analysis_stats(self):
        async with _new_session() as s:
            result = await fetch_virustotal_domain(s, _DOMAIN)

        self.assertIsNotNone(result, "VirusTotal returned None")
        # fetch_virustotal_domain returns the raw API response;
        # last_analysis_stats lives at result["data"]["attributes"]
        attrs = result["data"]["attributes"]
        self.assertIn("last_analysis_stats", attrs)
        stats = attrs["last_analysis_stats"]
        self.assertIn("malicious", stats)
        self.assertIn("harmless", stats)
        # example.com is a legitimate IANA domain — should have zero malicious
        self.assertEqual(stats["malicious"], 0,
                         f"Unexpected malicious count: {stats['malicious']}")

    @unittest.skipUnless(VIRUSTOTAL_API_KEY, "VIRUSTOTAL_API_KEY not configured")
    async def test_example_com_reputation(self):
        async with _new_session() as s:
            result = await fetch_virustotal_domain(s, _DOMAIN)
        attrs = result["data"]["attributes"]
        self.assertIn("reputation", attrs)
        self.assertIsInstance(attrs["reputation"], int)


@_SKIP_NO_NETWORK
class TestAlienVaultOTXIntegration(unittest.IsolatedAsyncioTestCase):

    @unittest.skipUnless(ALIENVAULT_OTX_API_KEY, "OTX_API_KEY not configured")
    async def test_example_com_pulse_count(self):
        async with _new_session() as s:
            result = await fetch_alienvault_otx_domain(s, _DOMAIN)

        self.assertIsNotNone(result)
        self.assertIn("pulse_count", result)
        self.assertIsInstance(result["pulse_count"], int)


@_SKIP_NO_NETWORK
class TestAbuseIPDBIntegration(unittest.IsolatedAsyncioTestCase):

    @unittest.skipUnless(ABUSEIPDB_API_KEY, "ABUSEIPDB_API_KEY not configured")
    async def test_google_dns_clean(self):
        async with _new_session() as s:
            result = await fetch_abuseipdb_check(s, _IP, ABUSEIPDB_API_KEY)

        self.assertIsNotNone(result)
        # fetch_abuseipdb_check normalizes field names:
        # abuseConfidenceScore → abuse_score, totalReports → total_reports
        self.assertIn("abuse_score", result)
        self.assertIn("ip", result)
        self.assertEqual(result["ip"], _IP)
        # 8.8.8.8 (Google Public DNS) should have a very low abuse confidence score
        self.assertLessEqual(result["abuse_score"], 15,
                             f"8.8.8.8 abuse score unexpectedly high: {result['abuse_score']}")


@_SKIP_NO_NETWORK
class TestSecurityTrailsIntegration(unittest.IsolatedAsyncioTestCase):

    @unittest.skipUnless(SECURITYTRAILS_API_KEY, "SECURITYTRAILS_API_KEY not configured")
    async def test_example_com_subdomain_count(self):
        async with _new_session() as s:
            result = await fetch_securitytrails_domain(s, _DOMAIN, SECURITYTRAILS_API_KEY)

        # SecurityTrails may return None when quota is exhausted (HTTP 429)
        if result is None:
            self.skipTest("SecurityTrails returned None — likely quota exceeded (HTTP 429)")
        self.assertIn("subdomain_count", result)
        self.assertIsInstance(result["subdomain_count"], int)


@_SKIP_ZOOMEYE
class TestZoomEyeIntegration(unittest.IsolatedAsyncioTestCase):

    @unittest.skipUnless(ZOOMEYE_API_KEY, "ZOOMEYE_API_KEY not configured")
    async def test_example_com_returns_results(self):
        async with _new_session() as s:
            result = await fetch_zoomeye_search(s, _DOMAIN, ZOOMEYE_API_KEY)

        # ZoomEye may return None if the domain is not indexed
        if result is None:
            self.skipTest("ZoomEye returned None — domain may not be indexed")
        self.assertIn("total", result)
        self.assertIn("hosts", result)


@_SKIP_NO_NETWORK
class TestPulsediveIntegration(unittest.IsolatedAsyncioTestCase):

    @unittest.skipUnless(PULSEDIVE_API_KEY, "PULSEDIVE_API_KEY not configured")
    async def test_example_com_risk(self):
        async with _new_session() as s:
            result = await fetch_pulsedive_info(s, _DOMAIN, api_key=PULSEDIVE_API_KEY)

        # May return None if indicator not in Pulsedive DB
        self.assertTrue(result is None or "risk" in result)


@_SKIP_NO_NETWORK
class TestCriminalIPIntegration(unittest.IsolatedAsyncioTestCase):

    @unittest.skipUnless(CRIMINALIP_API_KEY, "CRIMINALIP_API_KEY not configured")
    async def test_example_com_risk_score(self):
        async with _new_session() as s:
            result = await fetch_criminalip_domain(s, _DOMAIN, CRIMINALIP_API_KEY)

        self.assertIsNotNone(result)
        self.assertIn("risk_score", result)


@_SKIP_NO_NETWORK
class TestOpenPhishIntegration(unittest.IsolatedAsyncioTestCase):
    """OpenPhish community feed — no API key required."""

    async def test_example_com_not_phishing(self):
        async with _new_session() as s:
            result = await fetch_openphish_check(s, _DOMAIN)

        # Feed may be temporarily unavailable → None is acceptable
        if result is None:
            self.skipTest("OpenPhish feed unavailable")
        self.assertIn("in_database", result)
        self.assertIn("phishing_urls", result)
        self.assertIn("feed_size", result)
        self.assertIsInstance(result["feed_size"], int)
        # example.com is a legitimate IANA domain — must not appear in phishing feed
        self.assertFalse(result["in_database"],
                         "example.com incorrectly listed in OpenPhish feed!")

    async def test_feed_contains_entries(self):
        """Feed must return at least one URL when available."""
        async with _new_session() as s:
            result = await fetch_openphish_check(s, _DOMAIN)
        if result is None:
            self.skipTest("OpenPhish feed unavailable")
        self.assertGreater(result["feed_size"], 0, "OpenPhish feed is unexpectedly empty")


if __name__ == "__main__":
    unittest.main()
