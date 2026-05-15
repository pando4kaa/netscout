"""
External-API clients for OSINT enrichment.

Each function is an ``async`` aiohttp call against a third-party service. They
share a uniform contract: return a normalised ``dict`` on success, or ``None``
when the API has no data, the key is missing, or the request fails. Errors are
logged but never raised to the orchestrator.

Submodules group providers by purpose:
    * :mod:`threat_intel` - reputation / phishing / threat-feed lookups
    * :mod:`discovery`    - passive recon, certificates, archives
    * :mod:`network`      - ASN / BGP routing data
"""

from .threat_intel import (
    fetch_abuseipdb_check,
    fetch_alienvault_otx_domain,
    fetch_criminalip_domain,
    fetch_openphish_check,
    fetch_pulsedive_info,
    fetch_threatcrowd_domain,
    fetch_virustotal_domain,
)
from .discovery import (
    fetch_securitytrails_domain,
    fetch_ssllabs_analyze,
    fetch_urlscan_search,
    fetch_wayback_first_snapshot,
    fetch_zoomeye_search,
)
from .network import fetch_ripestat_ip

__all__ = [
    "fetch_abuseipdb_check",
    "fetch_alienvault_otx_domain",
    "fetch_criminalip_domain",
    "fetch_openphish_check",
    "fetch_pulsedive_info",
    "fetch_ripestat_ip",
    "fetch_securitytrails_domain",
    "fetch_ssllabs_analyze",
    "fetch_threatcrowd_domain",
    "fetch_urlscan_search",
    "fetch_virustotal_domain",
    "fetch_wayback_first_snapshot",
    "fetch_zoomeye_search",
]
