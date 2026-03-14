"""
Tests for Risk Detection module
"""

import unittest
from datetime import datetime, timedelta

from src.analysis.risk import (
    detect_port_risks,
    detect_ssl_risks,
    detect_subdomain_takeover,
    detect_outdated_tech,
    _parse_server_version,
)
from src.core.models import (
    Alert,
    DNSInfo,
    SslInfo,
    CertificateInfo,
    PortScanResult,
    OpenPort,
)


class TestDetectPortRisks(unittest.TestCase):
    def test_detect_risky_mysql_port(self):
        port_scan = [
            PortScanResult(ip="192.168.1.1", open_ports=[OpenPort(port=3306, protocol="tcp", service="mysql")])
        ]
        alerts = detect_port_risks(port_scan)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0].type, "open_port")
        self.assertIn("MySQL", alerts[0].message)
        self.assertEqual(alerts[0].level.value, "HIGH")

    def test_detect_risky_rdp_port(self):
        port_scan = [
            PortScanResult(ip="10.0.0.1", open_ports=[OpenPort(port=3389, protocol="tcp", service="rdp")])
        ]
        alerts = detect_port_risks(port_scan)
        self.assertEqual(len(alerts), 1)
        self.assertIn("RDP", alerts[0].message)

    def test_no_risks_for_safe_ports(self):
        port_scan = [
            PortScanResult(ip="192.168.1.1", open_ports=[OpenPort(port=80, protocol="tcp", service="http")])
        ]
        alerts = detect_port_risks(port_scan)
        self.assertEqual(len(alerts), 0)


class TestDetectSslRisks(unittest.TestCase):
    def test_detect_expired_certificate(self):
        cert = CertificateInfo(
            host="test.example.com",
            not_after=datetime.utcnow() - timedelta(days=1),
            is_expired=True,
        )
        ssl_info = SslInfo(certificates=[cert])
        alerts = detect_ssl_risks(ssl_info)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0].type, "expired_ssl")
        self.assertIn("test.example.com", alerts[0].message)

    def test_no_risks_for_valid_certs(self):
        cert = CertificateInfo(
            host="test.example.com",
            not_after=datetime.utcnow() + timedelta(days=30),
            is_expired=False,
        )
        ssl_info = SslInfo(certificates=[cert])
        alerts = detect_ssl_risks(ssl_info)
        self.assertEqual(len(alerts), 0)

    def test_empty_ssl_info_returns_empty(self):
        alerts = detect_ssl_risks(None)
        self.assertEqual(len(alerts), 0)


class TestParseServerVersion(unittest.TestCase):
    def test_parse_nginx(self):
        self.assertEqual(_parse_server_version("nginx/1.18.0"), ("nginx", "1.18.0"))

    def test_parse_apache(self):
        self.assertEqual(_parse_server_version("Apache/2.4.49"), ("apache", "2.4.49"))

    def test_parse_invalid_returns_none(self):
        self.assertIsNone(_parse_server_version(""))


class TestDetectOutdatedTech(unittest.TestCase):
    def test_detect_outdated_nginx(self):
        tech_stack = {
            "https://example.com": {"server": "nginx/1.18.0"},
        }
        alerts = detect_outdated_tech(tech_stack)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0].type, "outdated_tech")
        self.assertIn("nginx", alerts[0].message)


class TestDetectSubdomainTakeover(unittest.TestCase):
    def test_detect_github_io_cname(self):
        dns_info = DNSInfo(
            domain="example.com",
            cname_records=["victim.github.io"],
        )
        alerts = detect_subdomain_takeover(["sub.example.com"], dns_info)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0].type, "subdomain_takeover")
        self.assertIn("github.io", alerts[0].message)

    def test_no_takeover_without_cname(self):
        dns_info = DNSInfo(domain="example.com", cname_records=[])
        alerts = detect_subdomain_takeover(["www.example.com"], dns_info)
        self.assertEqual(len(alerts), 0)
