"""
Port Scanner Enricher - scans top ports on discovered IPs.
"""

import logging
import socket
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional, Set

from src.config.settings import PORT_SCAN_TIMEOUT
from src.core.models import OpenPort, PortScanResult
from src.enrichers.base import AbstractEnricher

logger = logging.getLogger(__name__)

# Top 20 ports for web/infra reconnaissance.
TOP_PORTS = [
    80, 443, 22, 21, 8080, 8443, 3306, 5432, 27017, 6379,
    25, 110, 143, 993, 995, 389, 636, 3389, 5900, 5985,
]

PORT_SERVICES = {
    80: "http", 443: "https", 22: "ssh", 21: "ftp",
    8080: "http-alt", 8443: "https-alt", 3306: "mysql", 5432: "postgresql",
    27017: "mongodb", 6379: "redis", 25: "smtp", 110: "pop3",
    143: "imap", 993: "imaps", 995: "pop3s", 389: "ldap",
    636: "ldaps", 3389: "rdp", 5900: "vnc", 5985: "winrm",
}

_BANNER_GRAB_TIMEOUT_SECONDS = 2
_BANNER_MAX_BYTES = 1024
_BANNER_MAX_TEXT_LENGTH = 200


def _decode_banner(raw: bytes) -> Optional[str]:
    for encoding in ("utf-8", "latin-1"):
        try:
            decoded = raw.decode(encoding).strip()
            return decoded[:_BANNER_MAX_TEXT_LENGTH] if decoded else None
        except UnicodeDecodeError:
            continue
    return None


def _scan_port(ip: str, port: int, timeout: Optional[float] = None) -> Optional[OpenPort]:
    """Check if `ip:port` is open and best-effort grab the service banner."""
    effective_timeout = timeout or PORT_SCAN_TIMEOUT
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(effective_timeout)
    try:
        if sock.connect_ex((ip, port)) != 0:
            return None

        banner: Optional[str] = None
        try:
            sock.settimeout(_BANNER_GRAB_TIMEOUT_SECONDS)
            data = sock.recv(_BANNER_MAX_BYTES)
            if data:
                banner = _decode_banner(data)
        except (socket.timeout, OSError):
            # Many services (HTTP/HTTPS) don't push a banner without a request.
            pass

        return OpenPort(port=port, protocol="tcp", service=PORT_SERVICES.get(port), banner=banner)
    except OSError as exc:
        logger.debug("Port scan error %s:%s -> %s", ip, port, exc)
        return None
    finally:
        sock.close()


def _scan_ip_ports(ip: str, ports: List[int], timeout: Optional[float] = None) -> PortScanResult:
    """Scan all `ports` on `ip` in parallel and return the open subset, sorted by port."""
    open_ports: List[OpenPort] = []
    with ThreadPoolExecutor(max_workers=min(20, len(ports))) as executor:
        futures = {executor.submit(_scan_port, ip, port, timeout): port for port in ports}
        for future in as_completed(futures):
            try:
                result = future.result()
            except Exception as exc:
                logger.debug("Port scan worker error %s:%s -> %s", ip, futures[future], exc)
                continue
            if result:
                open_ports.append(result)
    return PortScanResult(ip=ip, open_ports=sorted(open_ports, key=lambda x: x.port))


def _extract_ips_from_dns(dns_info: Any) -> Set[str]:
    if isinstance(dns_info, dict):
        return set((dns_info.get("a_records") or []) + (dns_info.get("aaaa_records") or []))
    a_records = getattr(dns_info, "a_records", None) or []
    aaaa_records = getattr(dns_info, "aaaa_records", None) or []
    return set(a_records) | set(aaaa_records)


class PortEnricher(AbstractEnricher):
    """Enricher for port scanning. Uses IPs from DNS context."""

    name = "port"

    def __init__(self, ports: Optional[List[int]] = None):
        self.ports = ports or TOP_PORTS

    def enrich(self, domain: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        ips: Set[str] = set()
        if context and context.get("dns_info"):
            ips = _extract_ips_from_dns(context["dns_info"])

        if not ips:
            return {"port_scan": []}

        ips_list = list(ips)
        results: List[PortScanResult] = []
        with ThreadPoolExecutor(max_workers=min(10, len(ips_list))) as executor:
            futures = {executor.submit(_scan_ip_ports, ip, self.ports): ip for ip in ips_list}
            for future in as_completed(futures):
                try:
                    results.append(future.result())
                except Exception as exc:
                    logger.debug("Port scan IP error %s -> %s", futures[future], exc)

        return {"port_scan": sorted(results, key=lambda r: r.ip)}
