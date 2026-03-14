"""
IP to ASN Enricher — find ASN for IP via BGPView API.
"""

from typing import Any, Callable, Dict

from src.enrichers.base import AbstractEnricher
from src.enrichers.external_apis import ExternalApiEnricher


class IpToAsnEnricher(AbstractEnricher):
    """Enricher for IP -> ASN (BGPView)."""

    name = "ip_to_asn"

    def enrich(self, domain: str, context: Any = None) -> Dict[str, Any]:
        """Not used for pipeline; use enrich_for_investigation for Investigation mode."""
        return {}

    def enrich_for_investigation(
        self,
        ip: str,
        progress: Callable[[str, int, str], None],
    ) -> tuple:
        """
        Get ASN for IP via BGPView. Returns (new_nodes, new_edges).
        """
        e = ExternalApiEnricher()
        ctx = e.enrich("", {"dns_info": {"a_records": [ip]}})
        ext = ctx.get("external_apis") or {}
        bgp = ext.get("bgpview") or {}
        ips_data = bgp.get("ips") or {}
        ip_data = ips_data.get(ip) or {}
        asn_num = ip_data.get("asn")
        nodes = []
        edges = []
        src = f"ip_{ip}"
        if asn_num:
            nodes.append({
                "type": "asn",
                "value": str(asn_num),
                "metadata": {"org": ip_data.get("asn_name")},
            })
            edges.append({"source": src, "target": f"asn_{asn_num}", "rel": "BELONGS_TO_ASN"})
        progress("ip_to_asn", 100, "IP to ASN complete")
        return (nodes, edges)
