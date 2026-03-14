"""
DNS Scanner Module (legacy wrapper — use src.enrichers.dns.DnsEnricher)
"""

from typing import Dict


def get_dns_records(domain: str) -> Dict:
    """
    Retrieves DNS records for a domain (legacy wrapper).
    """
    from src.enrichers.dns import DnsEnricher
    enricher = DnsEnricher()
    data = enricher.enrich(domain)
    dns_info = data.get("dns_info")
    if dns_info is None:
        return {"domain": domain, "a_records": [], "aaaa_records": [], "mx_records": [], "txt_records": [], "ns_records": [], "cname_records": []}
    return {
        "domain": dns_info.domain,
        "a_records": dns_info.a_records,
        "aaaa_records": dns_info.aaaa_records,
        "mx_records": [{"priority": m.priority, "host": m.host} for m in dns_info.mx_records],
        "txt_records": dns_info.txt_records,
        "ns_records": dns_info.ns_records,
        "cname_records": dns_info.cname_records,
    }
