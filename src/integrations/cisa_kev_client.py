"""
Optional CISA KEV client for known exploited vulnerability enrichment.
"""

import json
from typing import Any, Dict, Iterable

import requests

from src.config.settings import HTTP_TIMEOUT, REDIS_URL, USER_AGENT


CISA_KEV_URL = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
_redis_client = None


def _get_redis_client():
    """Return Redis client when configured; otherwise None."""
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    if not REDIS_URL:
        return None
    try:
        import redis

        _redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)
        _redis_client.ping()
        return _redis_client
    except Exception:
        _redis_client = None
        return None


def _cache_get(key: str) -> Dict[str, Any] | None:
    client = _get_redis_client()
    if not client:
        return None
    try:
        raw = client.get(key)
        return json.loads(raw) if raw else None
    except Exception:
        return None


def _cache_set(key: str, value: Dict[str, Any], ttl_seconds: int = 24 * 60 * 60) -> None:
    client = _get_redis_client()
    if not client:
        return
    try:
        client.setex(key, ttl_seconds, json.dumps(value))
    except Exception:
        pass


def get_kev_entries(cve_ids: Iterable[str]) -> Dict[str, Dict[str, Any]]:
    """
    Return CISA KEV entries keyed by CVE ID.

    Missing data or network failures return an empty mapping. KEV is used only as
    an exploitability signal in the risk model.
    """
    requested = {str(cve).upper() for cve in cve_ids if cve}
    if not requested:
        return {}

    cache_key = "cisa-kev:v1:catalog"
    catalog = _cache_get(cache_key)
    if catalog is None:
        try:
            response = requests.get(
                CISA_KEV_URL,
                headers={"User-Agent": USER_AGENT},
                timeout=HTTP_TIMEOUT,
            )
            if response.status_code != 200:
                return {}
            catalog = response.json()
            _cache_set(cache_key, catalog, ttl_seconds=12 * 60 * 60)
        except Exception:
            return {}

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
