"""
SSL Certificate Enricher - extracts certificate info (SAN, issuer, validity).
"""

import logging
import socket
import ssl
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.core.models import CertificateInfo, SslInfo
from src.enrichers.base import AbstractEnricher

logger = logging.getLogger(__name__)

_TLS_CONNECT_TIMEOUT_SECONDS = 5
_SSL_DATE_FORMAT = "%b %d %H:%M:%S %Y %Z"
_MAX_HOSTS_FROM_SUBDOMAINS = 20


def _parse_ssl_date(raw: Optional[str]) -> Optional[datetime]:
    if not raw:
        return None
    try:
        return datetime.strptime(raw, _SSL_DATE_FORMAT)
    except ValueError:
        return None


def _extract_common_name(name_tuples: list) -> Optional[str]:
    """X509 names are tuples-of-tuples-of-tuples; pull the CN if present."""
    for part in name_tuples or []:
        if part and part[0] == ("commonName",):
            return part[1]
    return None


def _get_cert_info(host: str, port: int = 443) -> Optional[CertificateInfo]:
    """Open a TLS connection to host:port and return the parsed certificate."""
    try:
        ssl_context = ssl.create_default_context()
        with socket.create_connection((host, port), timeout=_TLS_CONNECT_TIMEOUT_SECONDS) as sock:
            with ssl_context.wrap_socket(sock, server_hostname=host) as ssock:
                cert = ssock.getpeercert()
                if not cert:
                    return CertificateInfo(host=host, error="No certificate")

                san_list = [value for san_type, value in cert.get("subjectAltName", []) or [] if san_type == "DNS"]
                not_before = _parse_ssl_date(cert.get("notBefore"))
                not_after = _parse_ssl_date(cert.get("notAfter"))
                # `notBefore`/`notAfter` from getpeercert are naive UTC; compare as naive.
                is_expired = not_after is not None and datetime.utcnow() > not_after

                return CertificateInfo(
                    host=host,
                    subject_cn=_extract_common_name(cert.get("subject", [])),
                    issuer=_extract_common_name(cert.get("issuer", [])),
                    san=san_list,
                    not_before=not_before,
                    not_after=not_after,
                    is_expired=is_expired,
                )
    except Exception as exc:
        return CertificateInfo(host=host, error=str(exc))


class SslEnricher(AbstractEnricher):
    """Enricher for SSL certificate parsing. Uses subdomains from context."""

    name = "ssl"

    def enrich(self, domain: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        hosts_to_check: List[str] = [domain]
        if context and context.get("subdomains"):
            hosts_to_check.extend(context["subdomains"][:_MAX_HOSTS_FROM_SUBDOMAINS])

        hosts_to_check = list(dict.fromkeys(hosts_to_check))  # dedupe, preserve order
        certificates: List[CertificateInfo] = []

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(_get_cert_info, host): host for host in hosts_to_check}
            for future in as_completed(futures):
                try:
                    cert = future.result()
                except Exception as exc:
                    logger.debug("SSL fetch failed for %s: %s", futures[future], exc)
                    continue
                if cert and not cert.error:
                    certificates.append(cert)

        return {"ssl_info": SslInfo(certificates=certificates)}
