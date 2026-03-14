"""
DNS Enricher — resolves DNS records for a domain.
"""

import dns.resolver
import dns.exception
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional, Tuple

from src.enrichers.base import AbstractEnricher
from src.core.models import DNSInfo, MXRecord


def _resolve_a(domain: str) -> Tuple[str, Optional[List[str]]]:
    try:
        answers = dns.resolver.resolve(domain, "A")
        return ("a_records", [str(rdata) for rdata in answers])
    except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.exception.DNSException):
        return ("a_records", None)


def _resolve_aaaa(domain: str) -> Tuple[str, Optional[List[str]]]:
    try:
        answers = dns.resolver.resolve(domain, "AAAA")
        return ("aaaa_records", [str(rdata) for rdata in answers])
    except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.exception.DNSException):
        return ("aaaa_records", None)


def _resolve_mx(domain: str) -> Tuple[str, Optional[List[MXRecord]]]:
    try:
        answers = dns.resolver.resolve(domain, "MX")
        return ("mx_records", [MXRecord(priority=rdata.preference, host=str(rdata.exchange)) for rdata in answers])
    except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.exception.DNSException):
        return ("mx_records", None)


def _resolve_txt(domain: str) -> Tuple[str, Optional[List[str]]]:
    try:
        answers = dns.resolver.resolve(domain, "TXT")
        return ("txt_records", [str(rdata).strip('"') for rdata in answers])
    except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.exception.DNSException):
        return ("txt_records", None)


def _resolve_ns(domain: str) -> Tuple[str, Optional[List[str]]]:
    try:
        answers = dns.resolver.resolve(domain, "NS")
        return ("ns_records", [str(rdata) for rdata in answers])
    except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.exception.DNSException):
        return ("ns_records", None)


def _resolve_cname(domain: str) -> Tuple[str, Optional[List[str]]]:
    try:
        answers = dns.resolver.resolve(domain, "CNAME")
        return ("cname_records", [str(rdata) for rdata in answers])
    except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.exception.DNSException):
        return ("cname_records", None)


def _resolve_soa(domain: str) -> Tuple[str, Optional[List[str]]]:
    try:
        answers = dns.resolver.resolve(domain, "SOA")
        return ("soa_records", [str(rdata) for rdata in answers])
    except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.exception.DNSException):
        return ("soa_records", None)


def _resolve_ptr(ip: str) -> Tuple[str, Optional[str]]:
    try:
        ptr_answers = dns.resolver.resolve_address(ip)
        if ptr_answers:
            return (ip, str(ptr_answers[0]))
    except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.exception.DNSException):
        pass
    return (ip, None)


class DnsEnricher(AbstractEnricher):
    """Enricher for DNS records (A, AAAA, MX, TXT, NS, CNAME)."""

    name = "dns"

    def _try_zone_transfer(self, domain: str, ns_records: list) -> tuple[bool, Optional[str]]:
        """Attempt AXFR zone transfer (informational only, logs result)."""
        try:
            import dns.zone
            import dns.query
            for ns in (ns_records or [])[:3]:
                ns_clean = str(ns).rstrip(".")
                try:
                    zone = dns.zone.from_xfr(
                        dns.query.xfr(ns_clean, domain, lifetime=5)
                    )
                    if zone:
                        return True, None
                except Exception:
                    pass
        except Exception as e:
            return False, str(e)
        return False, None

    def enrich(self, domain: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        result = DNSInfo(domain=domain)

        try:
            # Resolve all record types in parallel
            resolvers = [
                _resolve_a,
                _resolve_aaaa,
                _resolve_mx,
                _resolve_txt,
                _resolve_ns,
                _resolve_cname,
                _resolve_soa,
            ]
            with ThreadPoolExecutor(max_workers=len(resolvers)) as executor:
                futures = {executor.submit(fn, domain): fn.__name__ for fn in resolvers}
                for future in as_completed(futures):
                    try:
                        key, value = future.result()
                        if value is not None:
                            setattr(result, key, value)
                    except Exception:
                        pass

            # Zone transfer attempt (informational)
            if result.ns_records:
                result.zone_transfer_attempted = True
                available, err = self._try_zone_transfer(domain, result.ns_records)
                result.zone_transfer_available = available
                result.zone_transfer_error = err

            # PTR records (reverse DNS for IPs) — parallel
            ips = (result.a_records or []) + (result.aaaa_records or [])
            if ips:
                with ThreadPoolExecutor(max_workers=min(10, len(ips))) as executor:
                    ptr_futures = {executor.submit(_resolve_ptr, ip): ip for ip in ips}
                    for future in as_completed(ptr_futures):
                        try:
                            ip, ptr = future.result()
                            if ptr:
                                result.ptr_records[ip] = ptr
                        except Exception:
                            pass

        except Exception as e:
            result.error = str(e)

        return {"dns_info": result}
