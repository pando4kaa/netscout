"""
DNS Enricher - resolves DNS records (A/AAAA/MX/TXT/NS/CNAME/SOA + reverse PTR).
"""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Dict, List, Optional, Tuple

import dns.exception
import dns.query
import dns.resolver
import dns.zone

from src.core.models import DNSInfo, MXRecord
from src.enrichers.base import AbstractEnricher

logger = logging.getLogger(__name__)

_DNS_ERRORS = (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.exception.DNSException)


def _str_records(answers) -> List[str]:
    return [str(rdata) for rdata in answers]


def _str_records_unquoted(answers) -> List[str]:
    return [str(rdata).strip('"') for rdata in answers]


def _mx_records(answers) -> List[MXRecord]:
    return [MXRecord(priority=rdata.preference, host=str(rdata.exchange)) for rdata in answers]


# (model field, dns rdtype, mapper fn)
_RESOLUTION_PLAN: List[Tuple[str, str, Callable[[Any], Any]]] = [
    ("a_records", "A", _str_records),
    ("aaaa_records", "AAAA", _str_records),
    ("mx_records", "MX", _mx_records),
    ("txt_records", "TXT", _str_records_unquoted),
    ("ns_records", "NS", _str_records),
    ("cname_records", "CNAME", _str_records),
    ("soa_records", "SOA", _str_records),
]


def _resolve_record(domain: str, field: str, rdtype: str, mapper: Callable[[Any], Any]) -> Tuple[str, Optional[Any]]:
    try:
        return field, mapper(dns.resolver.resolve(domain, rdtype))
    except _DNS_ERRORS:
        return field, None


def _resolve_ptr(ip: str) -> Tuple[str, Optional[str]]:
    try:
        ptr_answers = dns.resolver.resolve_address(ip)
        if ptr_answers:
            return ip, str(ptr_answers[0])
    except _DNS_ERRORS:
        pass
    return ip, None


class DnsEnricher(AbstractEnricher):
    """Enricher for DNS records (A, AAAA, MX, TXT, NS, CNAME, SOA + PTR)."""

    name = "dns"

    def _try_zone_transfer(self, domain: str, ns_records: list) -> Tuple[bool, Optional[str]]:
        """Attempt AXFR zone transfer for the first three NSes (informational only)."""
        try:
            for ns in (ns_records or [])[:3]:
                ns_clean = str(ns).rstrip(".")
                try:
                    zone = dns.zone.from_xfr(dns.query.xfr(ns_clean, domain, lifetime=5))
                    if zone:
                        return True, None
                except Exception:
                    # Per-NS failure is expected and silent: AXFR is rarely allowed.
                    continue
        except Exception as exc:
            return False, str(exc)
        return False, None

    def _resolve_records(self, domain: str, result: DNSInfo) -> None:
        with ThreadPoolExecutor(max_workers=len(_RESOLUTION_PLAN)) as executor:
            futures = [
                executor.submit(_resolve_record, domain, field, rdtype, mapper)
                for field, rdtype, mapper in _RESOLUTION_PLAN
            ]
            for future in as_completed(futures):
                try:
                    field, value = future.result()
                    if value is not None:
                        setattr(result, field, value)
                except Exception as exc:
                    logger.debug("DNS resolve failed for %s: %s", domain, exc)

    def _resolve_ptr_records(self, ips: List[str], result: DNSInfo) -> None:
        if not ips:
            return
        with ThreadPoolExecutor(max_workers=min(10, len(ips))) as executor:
            futures = {executor.submit(_resolve_ptr, ip): ip for ip in ips}
            for future in as_completed(futures):
                try:
                    ip, ptr = future.result()
                    if ptr:
                        result.ptr_records[ip] = ptr
                except Exception as exc:
                    logger.debug("PTR resolve failed for %s: %s", futures[future], exc)

    def enrich(self, domain: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        result = DNSInfo(domain=domain)

        try:
            self._resolve_records(domain, result)

            if result.ns_records:
                result.zone_transfer_attempted = True
                available, err = self._try_zone_transfer(domain, result.ns_records)
                result.zone_transfer_available = available
                result.zone_transfer_error = err

            ips = (result.a_records or []) + (result.aaaa_records or [])
            self._resolve_ptr_records(ips, result)
        except Exception as exc:
            result.error = str(exc)

        return {"dns_info": result}
