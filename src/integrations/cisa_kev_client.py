"""
Optional CISA KEV client for known-exploited-vulnerability enrichment.
"""

import logging
from typing import Any, Dict, Iterable

import requests

from src.config.settings import HTTP_TIMEOUT, USER_AGENT
from src.integrations._redis_cache import cache_get, cache_set

logger = logging.getLogger(__name__)

CISA_KEV_URL = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
_CATALOG_CACHE_KEY = "cisa-kev:v1:catalog"
_CATALOG_TTL_SECONDS = 12 * 60 * 60


def get_kev_entries(cve_ids: Iterable[str]) -> Dict[str, Dict[str, Any]]:
    """
    Return CISA KEV entries keyed by CVE ID.

    Missing data or network failures return an empty mapping. KEV is used only
    as an exploitability signal in the risk model.
    """
    requested = {str(cve).upper() for cve in cve_ids if cve}
    if not requested:
        return {}

    catalog = cache_get(_CATALOG_CACHE_KEY)
    if catalog is None:
        try:
            response = requests.get(
                CISA_KEV_URL,
                headers={"User-Agent": USER_AGENT},
                timeout=HTTP_TIMEOUT,
            )
        except requests.RequestException as exc:
            logger.debug("CISA KEV fetch failed: %s", exc)
            return {}
        if response.status_code != 200:
            return {}
        try:
            catalog = response.json()
        except ValueError as exc:
            logger.debug("CISA KEV JSON parse failed: %s", exc)
            return {}
        cache_set(_CATALOG_CACHE_KEY, catalog, ttl_seconds=_CATALOG_TTL_SECONDS)

    result: Dict[str, Dict[str, Any]] = {}
    for item in catalog.get("vulnerabilities") or []:
        cve = str(item.get("cveID") or "").upper()
        if cve in requested:
            result[cve] = {
                "cve": cve,
                "vendor_project": item.get("vendorProject"),
                "product": item.get("product"),
                "vulnerability_name": item.get("vulnerabilityName"),
                "date_added": item.get("dateAdded"),
                "due_date": item.get("dueDate"),
                "known_ransomware_campaign_use": item.get("knownRansomwareCampaignUse"),
                "required_action": item.get("requiredAction"),
                "notes": item.get("notes"),
            }
    return result
