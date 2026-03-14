"""
Abstract Enricher — base protocol for OSINT modules.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Protocol, runtime_checkable

from src.core.models import DNSInfo, WhoisInfo, SubdomainInfo


@runtime_checkable
class ScanContext(Protocol):
    """Protocol for scan context — accumulated data passed between enrichers."""

    domain: str
    dns_info: Optional[DNSInfo]
    whois_info: Optional[WhoisInfo]
    subdomains: list
    ssl_info: Optional[Any]
    port_scan: list
    tech_stack: Optional[Dict[str, Any]]


class AbstractEnricher(ABC):
    """Base class for enrichers. Each enricher enriches scan context with new data."""

    name: str = "base"

    @abstractmethod
    def enrich(self, domain: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Enrich scan with data.

        Args:
            domain: Target domain
            context: Accumulated scan data from previous enrichers

        Returns:
            Dict with enrichment result (will be merged into context)
        """
        pass
