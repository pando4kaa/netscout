"""
Tests for DNS Scanner module
"""

import unittest
from src.modules.dns_scanner import get_dns_records


class TestDNSScanner(unittest.TestCase):
    
    def test_valid_domain(self):
        """Test DNS lookup for a valid domain"""
        result = get_dns_records("google.com")
        self.assertIn("a_records", result)
        self.assertIn("domain", result)
        self.assertEqual(result["domain"], "google.com")
    
    def test_domain_structure(self):
        """Test that result has all expected fields"""
        result = get_dns_records("google.com")
        expected_fields = ["domain", "a_records", "aaaa_records", "mx_records", 
                          "txt_records", "ns_records", "cname_records"]
        for field in expected_fields:
            self.assertIn(field, result)


if __name__ == "__main__":
    unittest.main()
