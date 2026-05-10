"""
Reverse DNS Enricher - PTR records for an IP, finding domains pointing to it.
"""

import logging
from typing import Any, Callable, Dict

import dns.exception
import dns.resolver

from src.enrichers.base import AbstractEnricher

logger = logging.getLogger(__name__)


class ReverseDnsEnricher(AbstractEnricher):
    """Enricher for reverse DNS (IP -> domains via PTR)."""

    name = "reverse_dns"

    def enrich(self, domain: str, context: Any = None) -> Dict[str, Any]:
        """Pipeline mode is unused; investigations call `enrich_for_investigation` directly."""
        return {}

    def enrich_for_investigation(
        self,
        ip: str,
        progress: Callable[[str, int, str], None],
    ) -> tuple:
        """Resolve PTR records for `ip` and return (new_nodes, new_edges)."""
        nodes = []
        edges = []
        source_id = f"ip_{ip}"
        try:
            ptr_name = ".".join(reversed(ip.split("."))) + ".in-addr.arpa."
            for record in dns.resolver.resolve(ptr_name, "PTR"):
                hostname = str(record).rstrip(".") if record else ""
                if hostname:
                    nodes.append({"type": "domain", "value": hostname})
                    edges.append({"source": source_id, "target": f"domain_{hostname}", "rel": "POINTS_TO"})
        except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.exception.DNSException) as exc:
            logger.debug("PTR lookup failed for %s: %s", ip, exc)
        progress("reverse_dns", 100, "Reverse DNS complete")
        return (nodes, edges)
