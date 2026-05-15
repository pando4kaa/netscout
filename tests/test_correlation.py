"""
Tests for src/analysis/correlation.py — build_correlation_summary.

Real DNS resolution and reverse PTR lookups are mocked via:
  - src.analysis.correlation.group_subdomains_by_ip
  - src.analysis.correlation.reverse_dns_neighbors
  - src.analysis.correlation.shared_certificate_hosts

Signature: build_correlation_summary(subdomains, dns_info, ssl_info=None, root_domain="")
"""

import unittest
from unittest.mock import patch

from src.core.models import DNSInfo
from src.analysis.correlation import build_correlation_summary


def _make_dns(domain: str = "example.com",
              a_records=None, aaaa_records=None) -> DNSInfo:
    return DNSInfo(
        domain=domain,
        a_records=a_records or [],
        aaaa_records=aaaa_records or [],
        ns_records=[],
        txt_records=[],
        mx_records=[],
        cname_records=[],
    )


# ---------------------------------------------------------------------------
# Patches applied to every test to avoid network calls
# ---------------------------------------------------------------------------

_GROUP_BY_IP = "src.analysis.correlation.group_subdomains_by_ip"
_REV_DNS = "src.analysis.correlation.reverse_dns_neighbors"
_SHARED_CERT = "src.analysis.correlation.shared_certificate_hosts"


class TestBuildCorrelationSummaryBasicStructure(unittest.TestCase):

    def _run(self, subdomains=None, dns_info=None,
             ip_to_sub=None, ptr=None, shared=None):
        ip_to_sub = ip_to_sub or {}
        ptr = ptr or {}
        shared = shared or []
        with (
            patch(_GROUP_BY_IP, return_value=ip_to_sub),
            patch(_REV_DNS, return_value=ptr),
            patch(_SHARED_CERT, return_value=shared),
        ):
            return build_correlation_summary(
                subdomains=subdomains or [],
                dns_info=dns_info,
            )

    def test_returns_dict(self):
        result = self._run()
        self.assertIsInstance(result, dict)

    def test_required_keys_present(self):
        result = self._run()
        for key in ("unique_ips", "subdomain_count",
                    "ip_to_subdomains", "ptr_records",
                    "shared_certificate_hosts"):
            self.assertIn(key, result, f"Missing key: {key}")

    def test_unique_ips_is_int(self):
        result = self._run()
        self.assertIsInstance(result["unique_ips"], int)

    def test_subdomain_count_is_int(self):
        result = self._run()
        self.assertIsInstance(result["subdomain_count"], int)

    def test_ip_to_subdomains_is_dict(self):
        result = self._run()
        self.assertIsInstance(result["ip_to_subdomains"], dict)

    def test_ptr_records_is_dict(self):
        result = self._run()
        self.assertIsInstance(result["ptr_records"], dict)

    def test_shared_cert_hosts_is_list(self):
        result = self._run()
        self.assertIsInstance(result["shared_certificate_hosts"], list)


class TestBuildCorrelationSummaryIpCounting(unittest.TestCase):

    def _run_with_dns(self, a_records, subdomains=None, extra_ips=None):
        dns = _make_dns(a_records=a_records)
        # group_subdomains_by_ip may add IPs discovered via subdomain resolution
        ip_to_sub = {ip: [] for ip in (extra_ips or [])}
        with (
            patch(_GROUP_BY_IP, return_value=ip_to_sub),
            patch(_REV_DNS, return_value={}),
            patch(_SHARED_CERT, return_value=[]),
        ):
            return build_correlation_summary(
                subdomains=subdomains or [],
                dns_info=dns,
            )

    def test_no_a_records_unique_ips_zero(self):
        result = self._run_with_dns(a_records=[])
        self.assertEqual(result["unique_ips"], 0)

    def test_single_a_record(self):
        result = self._run_with_dns(a_records=["93.184.216.34"])
        self.assertEqual(result["unique_ips"], 1)

    def test_multiple_unique_a_records(self):
        result = self._run_with_dns(
            a_records=["1.1.1.1", "8.8.8.8", "93.184.216.34"]
        )
        self.assertEqual(result["unique_ips"], 3)

    def test_duplicate_a_records_counted_once(self):
        result = self._run_with_dns(a_records=["1.1.1.1", "1.1.1.1"])
        self.assertEqual(result["unique_ips"], 1)


class TestBuildCorrelationSummarySubdomainCount(unittest.TestCase):

    def _run(self, subdomains):
        dns = _make_dns(a_records=["1.1.1.1"])
        with (
            patch(_GROUP_BY_IP, return_value={}),
            patch(_REV_DNS, return_value={}),
            patch(_SHARED_CERT, return_value=[]),
        ):
            return build_correlation_summary(subdomains=subdomains, dns_info=dns)

    def test_empty_subdomains(self):
        result = self._run([])
        self.assertEqual(result["subdomain_count"], 0)

    def test_several_subdomains(self):
        result = self._run(["www.example.com", "api.example.com", "mail.example.com"])
        self.assertEqual(result["subdomain_count"], 3)


class TestBuildCorrelationSummaryIpToSubdomains(unittest.TestCase):

    def test_ip_to_subdomains_populated_by_group_function(self):
        dns = _make_dns(a_records=["93.184.216.34"])
        expected = {
            "93.184.216.34": ["www.example.com", "api.example.com"]
        }
        with (
            patch(_GROUP_BY_IP, return_value=expected),
            patch(_REV_DNS, return_value={}),
            patch(_SHARED_CERT, return_value=[]),
        ):
            result = build_correlation_summary(
                subdomains=["www.example.com", "api.example.com"],
                dns_info=dns,
            )

        ip_to_sub = result["ip_to_subdomains"]
        self.assertIn("93.184.216.34", ip_to_sub)
        self.assertIn("www.example.com", ip_to_sub["93.184.216.34"])
        self.assertIn("api.example.com", ip_to_sub["93.184.216.34"])

    def test_ip_to_subdomains_empty_when_group_returns_empty(self):
        dns = _make_dns(a_records=["93.184.216.34"])
        with (
            patch(_GROUP_BY_IP, return_value={}),
            patch(_REV_DNS, return_value={}),
            patch(_SHARED_CERT, return_value=[]),
        ):
            result = build_correlation_summary(
                subdomains=["www.example.com"],
                dns_info=dns,
            )
        self.assertEqual(result["ip_to_subdomains"], {})

    def test_shared_ips_across_multiple_subdomains(self):
        dns = _make_dns(a_records=["1.1.1.1"])
        expected = {
            "1.1.1.1": ["www.example.com", "mail.example.com", "api.example.com"]
        }
        with (
            patch(_GROUP_BY_IP, return_value=expected),
            patch(_REV_DNS, return_value={}),
            patch(_SHARED_CERT, return_value=[]),
        ):
            result = build_correlation_summary(
                subdomains=["www.example.com", "mail.example.com", "api.example.com"],
                dns_info=dns,
            )
        self.assertEqual(len(result["ip_to_subdomains"]["1.1.1.1"]), 3)


class TestBuildCorrelationSummaryPtrRecords(unittest.TestCase):

    def test_ptr_records_populated(self):
        dns = _make_dns(a_records=["93.184.216.34"])
        ptr = {"93.184.216.34": "93-184-216-34.deploy.static.akamaitechnologies.com"}
        with (
            patch(_GROUP_BY_IP, return_value={}),
            patch(_REV_DNS, return_value=ptr),
            patch(_SHARED_CERT, return_value=[]),
        ):
            result = build_correlation_summary(
                subdomains=[],
                dns_info=dns,
            )

        self.assertIn("93.184.216.34", result["ptr_records"])
        self.assertIn("akamaitechnologies", result["ptr_records"]["93.184.216.34"])

    def test_no_ptr_when_no_a_records(self):
        dns = _make_dns(a_records=[])
        with (
            patch(_GROUP_BY_IP, return_value={}),
            patch(_REV_DNS, return_value={}),
            patch(_SHARED_CERT, return_value=[]),
        ):
            result = build_correlation_summary(subdomains=[], dns_info=dns)
        self.assertEqual(result["ptr_records"], {})


class TestBuildCorrelationSummaryNoDnsInfo(unittest.TestCase):

    def test_no_dns_info_returns_minimal_result(self):
        with (
            patch(_GROUP_BY_IP, return_value={}),
            patch(_REV_DNS, return_value={}),
            patch(_SHARED_CERT, return_value=[]),
        ):
            result = build_correlation_summary(
                subdomains=["www.example.com"],
                dns_info=None,
            )
        self.assertEqual(result["unique_ips"], 0)
        self.assertIsInstance(result, dict)
        self.assertEqual(result["subdomain_count"], 1)


class TestBuildCorrelationSummarySharedCerts(unittest.TestCase):

    def test_shared_cert_hosts_from_ssl_info(self):
        dns = _make_dns(a_records=["1.2.3.4"])
        shared = ["www.example.com", "mail.example.com", "cdn.example.com"]
        with (
            patch(_GROUP_BY_IP, return_value={}),
            patch(_REV_DNS, return_value={}),
            patch(_SHARED_CERT, return_value=shared),
        ):
            result = build_correlation_summary(
                subdomains=[],
                dns_info=dns,
                ssl_info=None,
            )
        self.assertEqual(result["shared_certificate_hosts"], shared)
        self.assertIn("www.example.com", result["shared_certificate_hosts"])


if __name__ == "__main__":
    unittest.main()
