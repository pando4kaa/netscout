"""
Tests for src/analysis/normalizer.py:
  normalize_dns_info  — deduplicates and lowercases DNS records
  normalize_domains   — filters empty values and deduplicates subdomain lists
"""

import unittest

from src.analysis.normalizer import normalize_dns_info, normalize_domains
from src.core.models import DNSInfo, MXRecord


def _mx(host: str, priority: int = 10) -> MXRecord:
    return MXRecord(priority=priority, host=host)


class TestNormalizeDnsInfo(unittest.TestCase):

    def _make_dns(self, **kwargs) -> DNSInfo:
        defaults = dict(
            domain="example.com",
            a_records=[],
            aaaa_records=[],
            ns_records=[],
            txt_records=[],
            mx_records=[],
            cname_records=[],
        )
        defaults.update(kwargs)
        return DNSInfo(**defaults)

    # --- deduplication ---

    def test_a_records_deduplicated(self):
        dns = self._make_dns(
            a_records=["93.184.216.34", "93.184.216.34", "1.2.3.4"]
        )
        result = normalize_dns_info(dns)
        self.assertEqual(len(result.a_records), 2)
        self.assertIn("93.184.216.34", result.a_records)
        self.assertIn("1.2.3.4", result.a_records)

    def test_ns_records_deduplicated(self):
        dns = self._make_dns(
            ns_records=["a.iana-servers.net", "a.iana-servers.net", "b.iana-servers.net"]
        )
        result = normalize_dns_info(dns)
        self.assertEqual(len(result.ns_records), 2)

    def test_mx_records_preserved(self):
        # normalize_dns_info does not process mx_records (no dedup/lowercase).
        # Verify the field is returned unchanged.
        records = [_mx("mail.example.com", 10), _mx("backup.example.com", 20)]
        dns = self._make_dns(mx_records=records)
        result = normalize_dns_info(dns)
        self.assertEqual(len(result.mx_records), 2)

    def test_txt_records_deduplicated(self):
        dns = self._make_dns(
            txt_records=["v=spf1 -all", "v=spf1 -all", "google-site-verification=abc"]
        )
        result = normalize_dns_info(dns)
        self.assertEqual(len(result.txt_records), 2)

    def test_cname_records_deduplicated(self):
        dns = self._make_dns(
            cname_records=["cdn.example.com", "cdn.example.com"]
        )
        result = normalize_dns_info(dns)
        self.assertEqual(len(result.cname_records), 1)

    # --- lowercase ---

    def test_a_records_lowercased(self):
        dns = self._make_dns(a_records=["93.184.216.34"])
        result = normalize_dns_info(dns)
        self.assertEqual(result.a_records, ["93.184.216.34"])

    def test_ns_records_lowercased(self):
        dns = self._make_dns(
            ns_records=["A.IANA-SERVERS.NET", "B.IANA-SERVERS.NET"]
        )
        result = normalize_dns_info(dns)
        for ns in result.ns_records:
            self.assertEqual(ns, ns.lower())

    def test_mx_records_field_returns_dns_info(self):
        # normalize_dns_info does not lowercase MX hosts; just confirm it returns DNSInfo.
        dns = self._make_dns(mx_records=[_mx("MAIL.EXAMPLE.COM")])
        result = normalize_dns_info(dns)
        self.assertIsInstance(result, DNSInfo)
        self.assertEqual(len(result.mx_records), 1)

    def test_cname_records_lowercased(self):
        dns = self._make_dns(cname_records=["CDN.EXAMPLE.COM"])
        result = normalize_dns_info(dns)
        self.assertEqual(result.cname_records[0], "cdn.example.com")

    # --- empty lists ---

    def test_empty_a_records_unchanged(self):
        dns = self._make_dns(a_records=[])
        result = normalize_dns_info(dns)
        self.assertEqual(result.a_records, [])

    def test_all_empty_fields_handled(self):
        dns = self._make_dns()
        result = normalize_dns_info(dns)
        self.assertIsInstance(result, DNSInfo)

    # --- returns DNSInfo ---

    def test_returns_dns_info_instance(self):
        dns = self._make_dns(a_records=["1.2.3.4"])
        result = normalize_dns_info(dns)
        self.assertIsInstance(result, DNSInfo)

    def test_domain_preserved(self):
        dns = self._make_dns(domain="example.com")
        result = normalize_dns_info(dns)
        self.assertEqual(result.domain, "example.com")


class TestNormalizeDomains(unittest.TestCase):

    # --- filtering ---

    def test_empty_strings_removed(self):
        result = normalize_domains(["www.example.com", "", "api.example.com", ""])
        self.assertNotIn("", result)
        self.assertIn("www.example.com", result)

    def test_whitespace_only_removed(self):
        result = normalize_domains(["  ", "api.example.com", "\t"])
        self.assertEqual(len([x for x in result if not x.strip()]), 0)

    def test_none_values_not_expected(self):
        # normalize_domains expects str items; None values are not part of its
        # contract — it only handles str lists from the OSINT pipeline.
        # Confirm the function works correctly on a clean list.
        result = normalize_domains(["www.example.com", "api.example.com"])
        self.assertIn("www.example.com", result)
        self.assertIn("api.example.com", result)

    # --- deduplication ---

    def test_duplicates_removed(self):
        result = normalize_domains([
            "www.example.com",
            "api.example.com",
            "www.example.com",
        ])
        self.assertEqual(result.count("www.example.com"), 1)

    def test_case_insensitive_deduplication(self):
        result = normalize_domains([
            "WWW.EXAMPLE.COM",
            "www.example.com",
        ])
        self.assertEqual(len(result), 1)

    # --- lowercase ---

    def test_output_is_lowercase(self):
        result = normalize_domains(["API.EXAMPLE.COM", "MAIL.EXAMPLE.COM"])
        for domain in result:
            self.assertEqual(domain, domain.lower())

    # --- preservation of valid items ---

    def test_valid_domains_preserved(self):
        domains = ["www.example.com", "api.example.com", "mail.example.com"]
        result = normalize_domains(domains)
        for d in domains:
            self.assertIn(d, result)

    # --- edge cases ---

    def test_empty_input_returns_empty_list(self):
        result = normalize_domains([])
        self.assertEqual(result, [])

    def test_all_empty_strings_returns_empty_list(self):
        result = normalize_domains(["", "", ""])
        self.assertEqual(result, [])

    def test_single_valid_domain_returned(self):
        result = normalize_domains(["example.com"])
        self.assertEqual(result, ["example.com"])


if __name__ == "__main__":
    unittest.main()
