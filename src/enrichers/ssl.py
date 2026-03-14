"""
SSL Certificate Enricher — extracts certificate info (SAN, issuer, validity).
"""

import ssl
import socket
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.enrichers.base import AbstractEnricher
from src.core.models import SslInfo, CertificateInfo


def _get_cert_info(host: str, port: int = 443) -> Optional[CertificateInfo]:
    """Fetch SSL certificate for host:port."""
    try:
        context = ssl.create_default_context()
        with socket.create_connection((host, port), timeout=5) as sock:
            with context.wrap_socket(sock, server_hostname=host) as ssock:
                cert = ssock.getpeercert()
                if not cert:
                    return CertificateInfo(host=host, error="No certificate")

                san_list: List[str] = []
                for san_type, san_value in cert.get("subjectAltName", []) or []:
                    if san_type == "DNS":
                        san_list.append(san_value)

                issuer = None
                for part in cert.get("issuer", []) or []:
                    if part[0] == ("commonName",):
                        issuer = part[1]
                        break

                subject_cn = None
                for part in cert.get("subject", []) or []:
                    if part[0] == ("commonName",):
                        subject_cn = part[1]
                        break

                not_before = None
                not_after = None
                if cert.get("notBefore"):
                    try:
                        not_before = datetime.strptime(cert["notBefore"], "%b %d %H:%M:%S %Y %Z")
                    except Exception:
                        pass
                if cert.get("notAfter"):
                    try:
                        not_after = datetime.strptime(cert["notAfter"], "%b %d %H:%M:%S %Y %Z")
                    except Exception:
                        pass

                is_expired = not_after is not None and datetime.utcnow() > not_after

                return CertificateInfo(
                    host=host,
                    subject_cn=subject_cn,
                    issuer=issuer,
                    san=san_list,
                    not_before=not_before,
                    not_after=not_after,
                    is_expired=is_expired,
                )
    except Exception as e:
        return CertificateInfo(host=host, error=str(e))


class SslEnricher(AbstractEnricher):
    """Enricher for SSL certificate parsing. Uses subdomains from context."""

    name = "ssl"

    def enrich(self, domain: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        hosts_to_check: List[str] = [domain]
        if context and context.get("subdomains"):
            hosts_to_check.extend(context["subdomains"][:20])  # Limit to avoid overload

        hosts_to_check = list(dict.fromkeys(hosts_to_check))  # Dedupe
        certificates: List[CertificateInfo] = []

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(_get_cert_info, h): h for h in hosts_to_check}
            for future in as_completed(futures):
                cert = future.result()
                if cert and not cert.error:
                    certificates.append(cert)

        return {"ssl_info": SslInfo(certificates=certificates)}
