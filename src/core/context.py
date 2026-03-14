"""
Scan context — accumulated data passed between enrichers.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from src.core.models import DNSInfo, WhoisInfo, SslInfo, PortScanResult, CertificateInfo


@dataclass
class ScanContextData:
    """Mutable context holding scan results as they are enriched."""

    domain: str
    dns_info: Optional[DNSInfo] = None
    whois_info: Optional[WhoisInfo] = None
    subdomains: List[str] = field(default_factory=list)
    ssl_info: Optional[SslInfo] = None
    port_scan: List[PortScanResult] = field(default_factory=list)
    tech_stack: Optional[Dict[str, Any]] = None
    external_apis: Optional[Dict[str, Any]] = None
    geoip_info: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for passing to enrichers."""
        return {
            "domain": self.domain,
            "dns_info": self.dns_info,
            "whois_info": self.whois_info,
            "subdomains": self.subdomains,
            "ssl_info": self.ssl_info,
            "port_scan": self.port_scan,
            "tech_stack": self.tech_stack,
            "external_apis": self.external_apis,
            "geoip_info": self.geoip_info,
        }

    def merge(self, data: Dict[str, Any]) -> None:
        """Merge enrichment result into context."""
        if "dns_info" in data:
            self.dns_info = data["dns_info"]
        if "whois_info" in data:
            self.whois_info = data["whois_info"]
        if "subdomains" in data:
            self.subdomains = data["subdomains"]
        if "ssl_info" in data:
            self.ssl_info = data["ssl_info"]
        if "port_scan" in data:
            self.port_scan = data["port_scan"]
        if "tech_stack" in data:
            self.tech_stack = data["tech_stack"]
        if "external_apis" in data:
            self.external_apis = data["external_apis"]
        if "geoip_info" in data:
            self.geoip_info = data["geoip_info"]
