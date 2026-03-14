"""
Port Scanner Enricher — scans top ports on discovered IPs.
"""

import socket
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional, Set

from src.config.settings import PORT_SCAN_TIMEOUT
from src.enrichers.base import AbstractEnricher
from src.core.models import PortScanResult, OpenPort

# Top 20 ports for web/infra
TOP_PORTS = [
    80, 443, 22, 21, 8080, 8443, 3306, 5432, 27017, 6379,
    25, 110, 143, 993, 995, 389, 636, 3389, 5900, 5985,
]

PORT_SERVICES = {
    80: "http",
    443: "https",
    22: "ssh",
    21: "ftp",
    8080: "http-alt",
    8443: "https-alt",
    3306: "mysql",
    5432: "postgresql",
    27017: "mongodb",
    6379: "redis",
    25: "smtp",
    110: "pop3",
    143: "imap",
    993: "imaps",
    995: "pop3s",
    389: "ldap",
    636: "ldaps",
    3389: "rdp",
    5900: "vnc",
    5985: "winrm",
}


def _scan_ip_ports(ip: str, ports: List[int], timeout: float = None) -> PortScanResult:
    """Scan all ports for one IP in parallel."""
    timeout = timeout or PORT_SCAN_TIMEOUT
    open_ports: List[OpenPort] = []
    with ThreadPoolExecutor(max_workers=min(20, len(ports))) as executor:
        futures = {executor.submit(_scan_port, ip, p, timeout): p for p in ports}
        for future in as_completed(futures):
            op = future.result()
            if op:
                open_ports.append(op)
    return PortScanResult(ip=ip, open_ports=sorted(open_ports, key=lambda x: x.port))


def _scan_port(ip: str, port: int, timeout: float = None) -> Optional[OpenPort]:
    """Check if port is open, optionally grab banner."""
    timeout = timeout or PORT_SCAN_TIMEOUT
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((ip, port))
        if result != 0:
            sock.close()
            return None

        service = PORT_SERVICES.get(port)
        banner: Optional[str] = None

        try:
            sock.settimeout(2)
            data = sock.recv(1024)
            if data:
                for enc in ("utf-8", "latin-1"):
                    try:
                        raw = data.decode(enc).strip()
                        banner = raw[:200] if raw else None
                        break
                    except UnicodeDecodeError:
                        continue
        except (socket.timeout, OSError):
            pass
        finally:
            sock.close()

        return OpenPort(port=port, protocol="tcp", service=service, banner=banner)
    except Exception:
        pass
    return None


class PortEnricher(AbstractEnricher):
    """Enricher for port scanning. Uses IPs from DNS context."""

    name = "port"

    def __init__(self, ports: Optional[List[int]] = None):
        self.ports = ports or TOP_PORTS

    def enrich(self, domain: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        ips: Set[str] = set()
        if context and context.get("dns_info"):
            dns = context["dns_info"]
            if isinstance(dns, dict):
                ips.update(dns.get("a_records") or [])
                ips.update(dns.get("aaaa_records") or [])
            else:
                if hasattr(dns, "a_records") and dns.a_records:
                    ips.update(dns.a_records)
                if hasattr(dns, "aaaa_records") and dns.aaaa_records:
                    ips.update(dns.aaaa_records)

        if not ips:
            return {"port_scan": []}

        ips_list = list(ips)
        results: List[PortScanResult] = []
        with ThreadPoolExecutor(max_workers=min(10, len(ips_list))) as executor:
            futures = {executor.submit(_scan_ip_ports, ip, self.ports): ip for ip in ips_list}
            for future in as_completed(futures):
                try:
                    results.append(future.result())
                except Exception:
                    pass

        return {"port_scan": sorted(results, key=lambda r: r.ip)}
