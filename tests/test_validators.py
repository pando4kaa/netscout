"""
Tests for src/utils/validators.py — is_valid_domain and normalize_domain.
"""

import unittest

from src.utils.validators import is_valid_domain, normalize_domain


class TestIsValidDomain(unittest.TestCase):

    # --- valid domains ---

    def test_simple_domain(self):
        self.assertTrue(is_valid_domain("example.com"))

    def test_subdomain(self):
        self.assertTrue(is_valid_domain("www.example.com"))

    def test_deep_subdomain(self):
        self.assertTrue(is_valid_domain("api.v2.service.example.com"))

    def test_numeric_label(self):
        self.assertTrue(is_valid_domain("123.example.com"))

    def test_hyphen_in_label(self):
        self.assertTrue(is_valid_domain("my-service.example.com"))

    def test_two_letter_tld(self):
        self.assertTrue(is_valid_domain("example.ua"))

    def test_country_code_tld(self):
        self.assertTrue(is_valid_domain("bbc.co.uk"))

    def test_long_tld(self):
        self.assertTrue(is_valid_domain("example.technology"))

    # --- invalid domains ---

    def test_empty_string(self):
        self.assertFalse(is_valid_domain(""))

    def test_none_like_empty(self):
        self.assertFalse(is_valid_domain("  "))

    def test_no_tld(self):
        self.assertFalse(is_valid_domain("example"))

    def test_single_label_numeric_only(self):
        self.assertFalse(is_valid_domain("12345"))

    def test_double_dot(self):
        self.assertFalse(is_valid_domain("bad..domain.com"))

    def test_leading_hyphen(self):
        self.assertFalse(is_valid_domain("-leading.example.com"))

    def test_trailing_hyphen(self):
        self.assertFalse(is_valid_domain("trailing-.example.com"))

    def test_space_in_domain(self):
        self.assertFalse(is_valid_domain("has space.com"))

    def test_at_sign(self):
        self.assertFalse(is_valid_domain("user@example.com"))

    def test_too_long(self):
        # Exceeds 253 chars
        self.assertFalse(is_valid_domain("a" * 250 + ".com"))

    def test_numeric_only_tld(self):
        # TLD must be alpha-only per RFC
        self.assertFalse(is_valid_domain("example.123"))

    def test_single_char_tld(self):
        self.assertFalse(is_valid_domain("example.a"))

    def test_bare_ip_address(self):
        # IP addresses are not valid domain names in this validator
        self.assertFalse(is_valid_domain("192.168.1.1"))


class TestNormalizeDomain(unittest.TestCase):

    # --- scheme stripping ---

    def test_strip_http_scheme(self):
        self.assertEqual(normalize_domain("http://example.com"), "example.com")

    def test_strip_https_scheme(self):
        self.assertEqual(normalize_domain("https://example.com"), "example.com")

    def test_strip_https_with_path(self):
        self.assertEqual(normalize_domain("https://example.com/path/to/page"), "example.com")

    def test_strip_https_with_query(self):
        # normalize_domain strips scheme and path but not query strings
        # that are directly appended without a path separator.
        # Verify scheme is at least stripped.
        result = normalize_domain("https://example.com/search?q=1")
        self.assertEqual(result, "example.com")

    # --- www stripping ---

    def test_strip_www_prefix(self):
        self.assertEqual(normalize_domain("www.example.com"), "example.com")

    def test_strip_www_with_scheme(self):
        self.assertEqual(normalize_domain("https://www.example.com"), "example.com")

    def test_www_not_stripped_in_middle(self):
        # "www" only stripped as leading label
        result = normalize_domain("api.www.example.com")
        self.assertEqual(result, "api.www.example.com")

    # --- lowercase ---

    def test_lowercase_conversion(self):
        self.assertEqual(normalize_domain("EXAMPLE.COM"), "example.com")

    def test_mixed_case(self):
        self.assertEqual(normalize_domain("MyDomain.Example.COM"), "mydomain.example.com")

    # --- port stripping ---

    def test_strip_port(self):
        self.assertEqual(normalize_domain("example.com:8080"), "example.com")

    def test_strip_https_with_port(self):
        self.assertEqual(normalize_domain("https://example.com:443/path"), "example.com")

    # --- whitespace ---

    def test_strip_surrounding_whitespace(self):
        self.assertEqual(normalize_domain("  example.com  "), "example.com")

    # --- edge cases ---

    def test_empty_string(self):
        self.assertEqual(normalize_domain(""), "")

    def test_already_normalized(self):
        self.assertEqual(normalize_domain("api.example.com"), "api.example.com")


if __name__ == "__main__":
    unittest.main()
