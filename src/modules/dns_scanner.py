"""
DNS Scanner Module

This module provides functionality to query DNS records for a domain.
"""

import dns.resolver
import dns.exception
from typing import Dict, List, Optional


def get_dns_records(domain: str) -> Dict:
    """
    Retrieves DNS records for a domain.
    
    Args:
        domain: Domain name to query
    
    Returns:
        Dictionary with DNS records:
        {
            'a_records': [...],
            'aaaa_records': [...],
            'mx_records': [...],
            'txt_records': [...],
            'ns_records': [...],
            'cname_records': [...]
        }
    
    Raises:
        DNSException: If domain doesn't exist or DNS query fails
    """
    results = {
        "domain": domain,
        "a_records": [],
        "aaaa_records": [],
        "mx_records": [],
        "txt_records": [],
        "ns_records": [],
        "cname_records": []
    }
    
    # A records (IPv4)
    try:
        answers = dns.resolver.resolve(domain, 'A')
        results["a_records"] = [str(rdata) for rdata in answers]
    except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.exception.DNSException):
        pass
    
    # AAAA records (IPv6)
    try:
        answers = dns.resolver.resolve(domain, 'AAAA')
        results["aaaa_records"] = [str(rdata) for rdata in answers]
    except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.exception.DNSException):
        pass
    
    # MX records
    try:
        answers = dns.resolver.resolve(domain, 'MX')
        results["mx_records"] = [
            {"priority": rdata.preference, "host": str(rdata.exchange)}
            for rdata in answers
        ]
    except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.exception.DNSException):
        pass
    
    # TXT records
    try:
        answers = dns.resolver.resolve(domain, 'TXT')
        results["txt_records"] = [
            str(rdata).strip('"') for rdata in answers
        ]
    except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.exception.DNSException):
        pass
    
    # NS records
    try:
        answers = dns.resolver.resolve(domain, 'NS')
        results["ns_records"] = [str(rdata) for rdata in answers]
    except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.exception.DNSException):
        pass
    
    # CNAME records
    try:
        answers = dns.resolver.resolve(domain, 'CNAME')
        results["cname_records"] = [str(rdata) for rdata in answers]
    except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.exception.DNSException):
        pass
    
    return results
