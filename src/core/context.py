"""
Scan context - accumulated data passed between enrichers.
"""

from dataclasses import dataclass, field, fields
from typing import Any, Dict, List, Optional

from src.core.models import DNSInfo, PortScanResult, SslInfo, WhoisInfo

# Fields that can be merged from enricher results back into the context.
# Mirrors the dataclass field names below (excluding `domain`).
_MERGEABLE_FIELDS = (
    "dns_info",
    "whois_info",
    "subdomains",
    "ssl_info",
    "port_scan",
    "tech_stack",
    "external_apis",
    "geoip_info",
)


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
        """Snapshot of the context as a plain dict (consumed by enrichers)."""
        return {f.name: getattr(self, f.name) for f in fields(self)}

    def merge(self, data: Dict[str, Any]) -> None:
        """Apply enricher result back into the context (only known fields)."""
        for name in _MERGEABLE_FIELDS:
            if name in data:
                setattr(self, name, data[name])
