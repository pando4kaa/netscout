"""
DNS Scanner - legacy wrapper around `src.enrichers.dns.DnsEnricher`.

Kept for backwards compatibility (CLI scripts and existing tests).
New code should depend on the enricher directly.
"""

from typing import Any, Dict, List


def _empty_dns_dict(domain: str) -> Dict[str, Any]:
    return {
        "domain": domain,
        "a_records": [],
        "aaaa_records": [],
        "mx_records": [],
        "txt_records": [],
        "ns_records": [],
        "cname_records": [],
    }


def get_dns_records(domain: str) -> Dict[str, Any]:
    """Resolve common DNS records for `domain` and return a flat dict."""
    from src.enrichers.dns import DnsEnricher  # local import: avoid import cycle

    dns_info = DnsEnricher().enrich(domain).get("dns_info")
    if dns_info is None:
        return _empty_dns_dict(domain)

    return {
        "domain": dns_info.domain,
        "a_records": dns_info.a_records,
        "aaaa_records": dns_info.aaaa_records,
        "mx_records": [{"priority": m.priority, "host": m.host} for m in dns_info.mx_records],
        "txt_records": dns_info.txt_records,
        "ns_records": dns_info.ns_records,
        "cname_records": dns_info.cname_records,
    }
