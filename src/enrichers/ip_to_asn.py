"""
IP to ASN Enricher - find ASN for an IP via BGPView API.
"""

from typing import Any, Callable, Dict

from src.enrichers.base import AbstractEnricher
from src.enrichers.external_apis import ExternalApiEnricher


class IpToAsnEnricher(AbstractEnricher):
    """Enricher for IP -> ASN (BGPView)."""

    name = "ip_to_asn"

    def enrich(self, domain: str, context: Any = None) -> Dict[str, Any]:
        """Pipeline mode is unused; investigations call `enrich_for_investigation` directly."""
        return {}

    def enrich_for_investigation(
        self,
        ip: str,
        progress: Callable[[str, int, str], None],
    ) -> tuple:
        """Resolve ASN for `ip` via BGPView and return (new_nodes, new_edges)."""
        enricher = ExternalApiEnricher()
        result = enricher.enrich("", {"dns_info": {"a_records": [ip]}})
        bgp_ips = (result.get("external_apis") or {}).get("bgpview", {}).get("ips") or {}
        ip_data = bgp_ips.get(ip) or {}
        asn_num = ip_data.get("asn")

        nodes = []
        edges = []
        source_id = f"ip_{ip}"
        if asn_num:
            nodes.append({
                "type": "asn",
                "value": str(asn_num),
                "metadata": {"org": ip_data.get("asn_name")},
            })
            edges.append({"source": source_id, "target": f"asn_{asn_num}", "rel": "BELONGS_TO_ASN"})
        progress("ip_to_asn", 100, "IP to ASN complete")
        return (nodes, edges)
