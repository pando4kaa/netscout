"""
Correlation — grouping subdomain→IP, reverse DNS for neighbors.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Any, Optional, Set, Tuple

import dns.resolver
import dns.exception

from src.core.models import DNSInfo, SslInfo


def _resolve_subdomain_a(subdomain: str) -> List[str]:
    """Resolve A records for a subdomain."""
    try:
        answers = dns.resolver.resolve(subdomain, "A")
        return [str(r) for r in answers]
    except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.exception.DNSException):
        return []


def _ptr_lookup(ip: str) -> Optional[str]:
    """Reverse DNS lookup for IP."""
    try:
        answers = dns.resolver.resolve_address(ip)
        if answers:
            return str(answers[0]).rstrip(".")
    except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.exception.DNSException):
        pass
    return None


def group_subdomains_by_ip(
    subdomains: List[str],
    dns_info: Optional[DNSInfo],
    root_domain: str,
    resolve_subdomains: bool = True,
) -> Dict[str, List[str]]:
    """
    Group subdomains by their resolved IP.
    Returns dict: ip -> [subdomain1, subdomain2, ...]
    """
    result: Dict[str, List[str]] = {}

    # Root domain A records
    if dns_info and dns_info.a_records and root_domain:
        for ip in dns_info.a_records:
            result.setdefault(ip, []).append(root_domain)

    if not resolve_subdomains or not subdomains:
        return result

    # Resolve each subdomain to IP (limit to first 100 for performance)
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(_resolve_subdomain_a, sub): sub for sub in subdomains[:100]}
        for future in as_completed(futures):
            sub = futures[future]
            try:
                resolved_ips = future.result()
                for ip in resolved_ips:
                    if sub not in result.setdefault(ip, []):
                        result[ip].append(sub)
            except Exception:
                pass

    return result


def reverse_dns_neighbors(ips: List[str]) -> Dict[str, str]:
    """PTR lookup for IPs — find other hostnames on same server."""
    ptr_map: Dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(_ptr_lookup, ip): ip for ip in ips[:50]}
        for future in as_completed(futures):
            ip = futures[future]
            try:
                ptr = future.result()
                if ptr:
                    ptr_map[ip] = ptr
            except Exception:
                pass
    return ptr_map


def shared_certificate_hosts(ssl_info: Optional[SslInfo]) -> List[Dict[str, Any]]:
    """Group hosts that appear on the same certificate SAN/CN set."""
    if not ssl_info or not ssl_info.certificates:
        return []

    groups: Dict[str, Set[str]] = {}
    san_counts: Dict[str, int] = {}
    for cert in ssl_info.certificates:
        if getattr(cert, "error", None):
            continue
        host = (cert.host or "").lower().strip()
        san = sorted({str(name).lower().strip() for name in (cert.san or []) if name})
        subject = (cert.subject_cn or "").lower().strip()
        key_parts = san or ([subject] if subject else [])
        if not key_parts:
            continue
        key = "|".join(key_parts)
        if host:
            groups.setdefault(key, set()).add(host)
        for name in san:
            groups.setdefault(key, set()).add(name.lstrip("*."))
        san_counts[key] = len(san)

    result: List[Dict[str, Any]] = []
    for key, hosts in groups.items():
        if len(hosts) < 2:
            continue
        result.append(
            {
                "certificate_key": key[:160],
                "hosts": sorted(hosts),
                "san_count": san_counts.get(key, 0),
            }
        )
    result.sort(key=lambda item: len(item["hosts"]), reverse=True)
    return result[:20]


def build_correlation_summary(
    subdomains: List[str],
    dns_info: Optional[DNSInfo],
    ssl_info: Optional[SslInfo] = None,
    root_domain: str = "",
) -> Dict[str, Any]:
    """Build correlation summary with IP grouping and reverse DNS."""
    ips: Set[str] = set()
    if dns_info:
        ips.update(dns_info.a_records or [])
        ips.update(dns_info.aaaa_records or [])

    ip_to_subs = group_subdomains_by_ip(
        subdomains, dns_info, root_domain or (dns_info.domain if dns_info else ""), True
    )
    ips.update(ip_to_subs.keys())

    ptr_records = reverse_dns_neighbors(list(ips))

    return {
        "subdomain_count": len(subdomains),
        "unique_ips": len(ips),
        "ip_to_subdomains": ip_to_subs,
        "ptr_records": ptr_records,
        "shared_certificate_hosts": shared_certificate_hosts(ssl_info),
    }
