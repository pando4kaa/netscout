"""
Tests for scan_domain orchestrator (src/core/orchestrator.py).

The enricher pipeline is completely mocked so no network calls are made.
Tests verify domain validation, normalization, and ScanResult structure.
"""

import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

from src.core.models import DNSInfo, ScanResult, ScanSummary
from src.core.orchestrator import scan_domain


def _make_pipeline_data(domain: str = "example.com") -> dict:
    """Minimal context dict that the orchestrator needs to build ScanResult."""
    return {
        "domain": domain,
        "dns_info": DNSInfo(
            domain=domain,
            a_records=["93.184.216.34"],
            aaaa_records=[],
            ns_records=["a.iana-servers.net", "b.iana-servers.net"],
            txt_records=["v=spf1 -all"],
            mx_records=[],
            cname_records=[],
        ),
        "whois_info": None,
        "subdomains": ["www.example.com"],
        "ssl_info": None,
        "port_scan": [],
        "tech_stack": None,
        "external_apis": None,
        "geoip_info": None,
    }


class TestScanDomainInvalidDomain(unittest.TestCase):

    def test_invalid_domain_raises_value_error(self):
        with self.assertRaises(ValueError):
            scan_domain("not_a_domain")

    def test_empty_domain_raises_value_error(self):
        with self.assertRaises(ValueError):
            scan_domain("")

    def test_domain_with_invalid_chars_raises(self):
        with self.assertRaises(ValueError):
            scan_domain("domain with space.com")

    def test_double_dot_raises(self):
        with self.assertRaises(ValueError):
            scan_domain("bad..domain.com")


class TestScanDomainNormalization(unittest.TestCase):

    def _run_mocked(self, domain_input: str, expected_domain: str):
        data = _make_pipeline_data(expected_domain)
        mock_pipeline = MagicMock()
        mock_pipeline.run.return_value = data

        with (
            patch("src.core.orchestrator.build_correlation_summary",
                  return_value={"unique_ips": 1, "subdomain_count": 1,
                                "ip_to_subdomains": {}, "ptr_records": {},
                                "shared_certificate_hosts": []}),
        ):
            result = scan_domain(domain_input, pipeline=mock_pipeline)

        return result, mock_pipeline

    def test_uppercase_domain_normalized(self):
        result, pipeline = self._run_mocked("EXAMPLE.COM", "example.com")
        self.assertIsInstance(result, ScanResult)
        self.assertEqual(result.target_domain, "example.com")

    def test_http_scheme_stripped(self):
        result, pipeline = self._run_mocked("http://example.com", "example.com")
        self.assertEqual(result.target_domain, "example.com")

    def test_https_scheme_stripped(self):
        result, pipeline = self._run_mocked("https://example.com/path", "example.com")
        self.assertEqual(result.target_domain, "example.com")

    def test_www_prefix_stripped(self):
        result, pipeline = self._run_mocked("www.example.com", "example.com")
        self.assertEqual(result.target_domain, "example.com")


class TestScanDomainResult(unittest.TestCase):

    def _run_mocked(self, domain: str = "example.com"):
        data = _make_pipeline_data(domain)
        mock_pipeline = MagicMock()
        mock_pipeline.run.return_value = data

        with (
            patch("src.core.orchestrator.build_correlation_summary",
                  return_value={"unique_ips": 1, "subdomain_count": 1,
                                "ip_to_subdomains": {}, "ptr_records": {},
                                "shared_certificate_hosts": []}),
        ):
            result = scan_domain(domain, pipeline=mock_pipeline)
        return result

    def test_returns_scan_result_instance(self):
        result = self._run_mocked()
        self.assertIsInstance(result, ScanResult)

    def test_target_domain_set(self):
        result = self._run_mocked()
        self.assertEqual(result.target_domain, "example.com")

    def test_scan_date_is_datetime(self):
        result = self._run_mocked()
        self.assertIsInstance(result.scan_date, datetime)

    def test_summary_is_populated(self):
        result = self._run_mocked()
        self.assertIsInstance(result.summary, ScanSummary)
        self.assertGreaterEqual(result.summary.total_subdomains, 0)

    def test_dns_info_present(self):
        result = self._run_mocked()
        self.assertIsNotNone(result.dns_info)
        self.assertIn("93.184.216.34", result.dns_info.a_records)

    def test_subdomains_normalized(self):
        result = self._run_mocked()
        for sub in result.subdomains:
            self.assertEqual(sub, sub.lower())


class TestScanDomainProgressCallback(unittest.TestCase):

    def test_progress_callback_receives_calls(self):
        data = _make_pipeline_data()
        mock_pipeline = MagicMock()
        mock_pipeline.run.return_value = data
        calls = []

        with (
            patch("src.core.orchestrator.build_correlation_summary",
                  return_value={"unique_ips": 0, "subdomain_count": 0,
                                "ip_to_subdomains": {}, "ptr_records": {},
                                "shared_certificate_hosts": []}),
        ):
            scan_domain("example.com",
                        on_progress=lambda s, p, m: calls.append((s, p, m)),
                        pipeline=mock_pipeline)

        stages = [c[0] for c in calls]
        self.assertIn("analysis", stages)

    def test_pipeline_receives_progress_callback(self):
        data = _make_pipeline_data()
        mock_pipeline = MagicMock()
        mock_pipeline.run.return_value = data
        captured_callback = []

        def fake_build_pipeline(on_progress=None):
            if on_progress:
                captured_callback.append(on_progress)
            return mock_pipeline

        with (
            patch("src.core.orchestrator._build_pipeline", side_effect=fake_build_pipeline),
            patch("src.core.orchestrator.build_correlation_summary",
                  return_value={"unique_ips": 0, "subdomain_count": 0,
                                "ip_to_subdomains": {}, "ptr_records": {},
                                "shared_certificate_hosts": []}),
        ):
            def cb(s, p, m):
                pass

            scan_domain("example.com", on_progress=cb)

        self.assertEqual(len(captured_callback), 1)
        self.assertIs(captured_callback[0], cb)


if __name__ == "__main__":
    unittest.main()
