"""
Reverse DNS Enricher — PTR records for IP, find domains pointing to IP.
"""

import dns.resolver
from typing import Any, Callable, Dict, List

from src.enrichers.base import AbstractEnricher


class ReverseDnsEnricher(AbstractEnricher):
    """Enricher for reverse DNS (IP -> domains via PTR)."""

    name = "reverse_dns"

    def enrich(self, domain: str, context: Any = None) -> Dict[str, Any]:
        """Not used for pipeline; use enrich_for_investigation for Investigation mode."""
        return {}

    def enrich_for_investigation(
        self,
        ip: str,
        progress: Callable[[str, int, str], None],
    ) -> tuple:
        """
        Resolve PTR records for IP. Returns (new_nodes, new_edges).
        """
        nodes = []
        edges = []
        src = f"ip_{ip}"
        try:
            ptr_name = ".".join(reversed(ip.split("."))) + ".in-addr.arpa."
            answers = dns.resolver.resolve(ptr_name, "PTR")
            for r in answers:
                name = str(r).rstrip(".") if r else ""
                if name:
                    nodes.append({"type": "domain", "value": name})
                    edges.append({"source": src, "target": f"domain_{name}", "rel": "POINTS_TO"})
        except Exception:
            pass
        progress("reverse_dns", 100, "Reverse DNS complete")
        return (nodes, edges)
