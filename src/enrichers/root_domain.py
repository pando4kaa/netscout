"""
Root Domain Enricher — extract root domain from domain/subdomain.
"""

from typing import Any, Callable, Dict

from src.enrichers.base import AbstractEnricher


def extract_root_domain(domain: str) -> str:
    """Extract root domain (e.g. sub.example.com -> example.com)."""
    domain = domain.lower().strip().rstrip(".")
    parts = domain.split(".")
    if len(parts) >= 2:
        return ".".join(parts[-2:])
    return domain


class RootDomainEnricher(AbstractEnricher):
    """Enricher for domain -> root domain."""

    name = "root_domain"

    def enrich(self, domain: str, context: Any = None) -> Dict[str, Any]:
        """Not used for pipeline; use enrich_for_investigation for Investigation mode."""
        return {}

    def enrich_for_investigation(
        self,
        domain: str,
        progress: Callable[[str, int, str], None],
    ) -> tuple:
        """
        Extract root domain. Returns (new_nodes, new_edges).
        """
        root = extract_root_domain(domain)
        src = f"subdomain_{domain}" if domain.count(".") >= 2 else f"domain_{domain}"
        nodes = [{"type": "domain", "value": root}]
        edges = [{"source": src, "target": f"domain_{root}", "rel": "ROOT_OF"}]
        progress("root_domain", 100, "Root domain complete")
        return (nodes, edges)
