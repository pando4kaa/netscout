"""
Unit tests for ExternalApiEnricher orchestrator (src/enrichers/external_apis.py):
  _flatten_virustotal    — extracts last_analysis_stats & reputation
  _collect_unique_ips    — from dns_info dict/object and port_scan
  _merge_results         — per-IP grouping, VT flattening, None/Exception pairs
  fetch_single_external_api — dispatches to correct provider (sync wrapper)
  ExternalApiEnricher.enrich — full integration with mocked _fetch_external_apis_async
"""

import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from src.enrichers.external_apis import (
    ExternalApiEnricher,
    _flatten_virustotal,
    _collect_unique_ips,
    _merge_results,
    fetch_single_external_api,
    _MAX_IPS,
)
from src.core.models import DNSInfo


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _dns_obj(a_records=None, aaaa_records=None) -> DNSInfo:
    return DNSInfo(
        domain="example.com",
        a_records=a_records or [],
        aaaa_records=aaaa_records or [],
        ns_records=[], txt_records=[], mx_records=[], cname_records=[],
    )


# ---------------------------------------------------------------------------
# _flatten_virustotal
# ---------------------------------------------------------------------------

class TestFlattenVirustotal(unittest.TestCase):

    def test_extracts_last_analysis_stats(self):
        raw = {"data": {"attributes": {
            "last_analysis_stats": {"malicious": 2, "harmless": 50},
            "reputation": -10,
        }}}
        result = _flatten_virustotal(raw)
        self.assertIn("last_analysis_stats", result)
        self.assertEqual(result["last_analysis_stats"]["malicious"], 2)

    def test_extracts_reputation(self):
        raw = {"data": {"attributes": {
            "last_analysis_stats": {"malicious": 0},
            "reputation": -15,
        }}}
        result = _flatten_virustotal(raw)
        self.assertEqual(result["reputation"], -15)

    def test_missing_data_key_returns_empty_values(self):
        # _flatten_virustotal({}) → {"last_analysis_stats": None, "reputation": None}
        result = _flatten_virustotal({})
        self.assertIn("last_analysis_stats", result)
        self.assertIsNone(result["last_analysis_stats"])

    def test_clean_domain_zero_malicious(self):
        raw = {"data": {"attributes": {
            "last_analysis_stats": {"malicious": 0, "harmless": 72},
            "reputation": 0,
        }}}
        result = _flatten_virustotal(raw)
        self.assertEqual(result["last_analysis_stats"]["malicious"], 0)
        self.assertEqual(result["reputation"], 0)


# ---------------------------------------------------------------------------
# _collect_unique_ips
# ---------------------------------------------------------------------------

class TestCollectUniqueIps(unittest.TestCase):

    def test_from_dns_info_dict(self):
        context = {"dns_info": {"a_records": ["1.1.1.1", "8.8.8.8"], "aaaa_records": []}}
        ips = _collect_unique_ips(context)
        self.assertIn("1.1.1.1", ips)
        self.assertIn("8.8.8.8", ips)

    def test_from_dns_info_object(self):
        context = {"dns_info": _dns_obj(a_records=["1.2.3.4", "5.6.7.8"])}
        ips = _collect_unique_ips(context)
        self.assertIn("1.2.3.4", ips)
        self.assertIn("5.6.7.8", ips)

    def test_from_port_scan_ips(self):
        context = {
            "dns_info": None,
            "port_scan": [
                {"ip": "10.0.0.1", "port": 80},
                {"ip": "10.0.0.2", "port": 443},
            ],
        }
        ips = _collect_unique_ips(context)
        self.assertIn("10.0.0.1", ips)
        self.assertIn("10.0.0.2", ips)

    def test_deduplication(self):
        context = {"dns_info": {"a_records": ["1.1.1.1", "1.1.1.1"], "aaaa_records": []}}
        ips = _collect_unique_ips(context)
        self.assertEqual(ips.count("1.1.1.1"), 1)

    def test_cap_at_max_ips(self):
        many = [f"1.2.3.{i}" for i in range(1, _MAX_IPS + 10)]
        context = {"dns_info": {"a_records": many, "aaaa_records": []}}
        ips = _collect_unique_ips(context)
        self.assertLessEqual(len(ips), _MAX_IPS)

    def test_empty_context_returns_empty(self):
        self.assertEqual(_collect_unique_ips({}), [])

    def test_none_context_returns_empty(self):
        self.assertEqual(_collect_unique_ips(None), [])


# ---------------------------------------------------------------------------
# _merge_results  — takes List[tuple] where each tuple is (key, payload)
# ---------------------------------------------------------------------------

class TestMergeResults(unittest.TestCase):

    def test_ripestat_per_ip_assigned(self):
        pairs = [
            ("ripestat", {"ip": "8.8.8.8", "asn": 15169,
                           "asn_name": "GOOGLE", "prefix": "8.8.8.0/24"}),
        ]
        merged = _merge_results(pairs)
        self.assertIn("ripestat", merged)
        self.assertIn("ips", merged["ripestat"])
        self.assertIn("8.8.8.8", merged["ripestat"]["ips"])
        self.assertEqual(merged["ripestat"]["ips"]["8.8.8.8"]["asn"], 15169)

    def test_abuseipdb_per_ip_assigned(self):
        pairs = [
            ("abuseipdb", {"ip": "1.1.1.1", "abuseConfidenceScore": 0, "totalReports": 0}),
        ]
        merged = _merge_results(pairs)
        self.assertIn("abuseipdb", merged)
        self.assertIn("ips", merged["abuseipdb"])
        self.assertIn("1.1.1.1", merged["abuseipdb"]["ips"])

    def test_virustotal_flattened(self):
        raw_vt = {"data": {"attributes": {
            "last_analysis_stats": {"malicious": 0, "harmless": 60},
            "reputation": 0,
        }}}
        merged = _merge_results([("virustotal", raw_vt)])
        self.assertIn("virustotal", merged)
        self.assertIn("last_analysis_stats", merged["virustotal"])

    def test_none_result_skipped(self):
        pairs = [
            ("urlscan", None),
            ("securitytrails", {"subdomain_count": 5}),
        ]
        merged = _merge_results(pairs)
        self.assertNotIn("urlscan", merged)
        self.assertIn("securitytrails", merged)

    def test_exception_payload_skipped(self):
        pairs = [
            ("threatcrowd", Exception("timeout")),
            ("alienvault", {"pulse_count": 2}),
        ]
        merged = _merge_results(pairs)
        self.assertNotIn("threatcrowd", merged)
        self.assertIn("alienvault", merged)

    def test_multiple_ips_ripestat(self):
        pairs = [
            ("ripestat", {"ip": "1.1.1.1", "asn": 13335,
                          "asn_name": "CLOUDFLARE", "prefix": "1.1.1.0/24"}),
            ("ripestat", {"ip": "8.8.8.8", "asn": 15169,
                          "asn_name": "GOOGLE", "prefix": "8.8.8.0/24"}),
        ]
        merged = _merge_results(pairs)
        self.assertIn("1.1.1.1", merged["ripestat"]["ips"])
        self.assertIn("8.8.8.8", merged["ripestat"]["ips"])


# ---------------------------------------------------------------------------
# fetch_single_external_api — sync function, dispatches by api_name
# ---------------------------------------------------------------------------

class TestFetchSingleExternalApi(unittest.TestCase):

    def test_urlscan_dispatched(self):
        with patch("src.enrichers.external_apis.fetch_urlscan_search",
                   return_value={"total": 3, "urls": ["https://example.com"]}) as mock_fn:
            result = fetch_single_external_api("urlscan", domain="example.com")
        # The underlying async fn is called inside asyncio.run(); result is passed through
        self.assertIsNotNone(result)
        self.assertEqual(result["total"], 3)

    def test_virustotal_dispatched(self):
        with patch("src.enrichers.external_apis.fetch_virustotal_domain",
                   return_value={"last_analysis_stats": {"malicious": 0}, "reputation": 0}):
            result = fetch_single_external_api("virustotal", domain="example.com")
        self.assertIsNotNone(result)

    def test_ripestat_dispatched_with_ip(self):
        with patch("src.enrichers.external_apis.fetch_ripestat_ip",
                   return_value={"asn": 15169, "asn_name": "GOOGLE",
                                 "prefix": "8.8.8.0/24", "ip": "8.8.8.8"}):
            result = fetch_single_external_api("ripestat", ip="8.8.8.8")
        self.assertEqual(result["asn"], 15169)

    def test_legacy_bgpview_id_calls_ripestat(self):
        with patch("src.enrichers.external_apis.fetch_ripestat_ip",
                   return_value={"asn": 15169, "asn_name": "GOOGLE",
                                 "prefix": "8.8.8.0/24", "ip": "8.8.8.8"}):
            result = fetch_single_external_api("bgpview", ip="8.8.8.8")
        self.assertEqual(result["asn"], 15169)

    def test_abuseipdb_dispatched_with_ip(self):
        with patch("src.enrichers.external_apis.fetch_abuseipdb_check",
                   return_value={"ip": "1.1.1.1", "abuseConfidenceScore": 0}):
            result = fetch_single_external_api("abuseipdb", ip="1.1.1.1")
        self.assertIsNotNone(result)

    def test_unknown_api_name_returns_none(self):
        result = fetch_single_external_api("nonexistent_api", domain="example.com")
        self.assertIsNone(result)


# ---------------------------------------------------------------------------
# ExternalApiEnricher.enrich
# ---------------------------------------------------------------------------

_FULL_RESULTS = {
    "virustotal": {"last_analysis_stats": {"malicious": 0}, "reputation": 0},
    "alienvault": {"pulse_count": 0},
    "urlscan": {"total": 5, "urls": ["https://example.com"]},
    "ripestat": {"ips": {
        "93.184.216.34": {"asn": 15133, "asn_name": "MCI", "prefix": "93.184.216.0/24"}
    }},
}


def _async_returning(value):
    """Return an async function that returns ``value`` when awaited."""
    async def _coro(*args, **kwargs):
        return value
    return _coro


class TestExternalApiEnricher(unittest.TestCase):

    def test_enrich_returns_external_apis_key(self):
        enricher = ExternalApiEnricher()
        context = {"dns_info": _dns_obj(a_records=["93.184.216.34"])}
        with patch("src.enrichers.external_apis._fetch_external_apis_async",
                   new=_async_returning(_FULL_RESULTS)):
            result = enricher.enrich("example.com", context)
        self.assertIn("external_apis", result)

    def test_enrich_result_is_dict(self):
        enricher = ExternalApiEnricher()
        context = {"dns_info": _dns_obj(a_records=["1.1.1.1"])}
        with patch("src.enrichers.external_apis._fetch_external_apis_async",
                   new=_async_returning(_FULL_RESULTS)):
            result = enricher.enrich("example.com", context)
        self.assertIsInstance(result["external_apis"], dict)

    def test_enrich_with_no_ips(self):
        # When async returns {}, enrich returns {} (falsy → no "external_apis" key)
        enricher = ExternalApiEnricher()
        context = {"dns_info": _dns_obj(a_records=[])}
        with patch("src.enrichers.external_apis._fetch_external_apis_async",
                   new=_async_returning({})):
            result = enricher.enrich("example.com", context)
        self.assertIsInstance(result, dict)

    def test_enrich_no_dns_info(self):
        # No context → no IPs → empty external API result
        enricher = ExternalApiEnricher()
        with patch("src.enrichers.external_apis._fetch_external_apis_async",
                   new=_async_returning({})):
            result = enricher.enrich("example.com", {})
        self.assertIsInstance(result, dict)

    def test_virustotal_key_in_results(self):
        enricher = ExternalApiEnricher()
        context = {"dns_info": _dns_obj(a_records=["93.184.216.34"])}
        api_data = {"virustotal": {"last_analysis_stats": {"malicious": 0}, "reputation": 0}}
        with patch("src.enrichers.external_apis._fetch_external_apis_async",
                   new=_async_returning(api_data)):
            result = enricher.enrich("example.com", context)
        self.assertIn("virustotal", result["external_apis"])

    def test_all_providers_none_returns_no_external_apis_key(self):
        # enrich returns {} (not {"external_apis": {}}) when result is empty/falsy
        enricher = ExternalApiEnricher()
        context = {"dns_info": _dns_obj(a_records=["1.2.3.4"])}
        with patch("src.enrichers.external_apis._fetch_external_apis_async",
                   new=_async_returning({})):
            result = enricher.enrich("example.com", context)
        self.assertEqual(result, {})


if __name__ == "__main__":
    unittest.main()
