"""
Minimal NVD API client for CVE/CVSS enrichment.

The integration is intentionally optional: without NVD_API_KEY the scan keeps
using local heuristics and never fails because of CVE enrichment.
"""

import json
from typing import Any, Dict, List, Optional

import requests

from src.config.settings import HTTP_TIMEOUT, NVD_API_KEY, REDIS_URL, USER_AGENT


NVD_API_URL = "https://services.nvd.nist.gov/rest/json/cves/2.0"
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


def _cache_get(key: str) -> Optional[Dict[str, Any]]:
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


def _extract_cvss(metrics: Dict[str, Any]) -> Optional[float]:
    """Extract the best available CVSS base score from NVD metrics."""
    for key in ("cvssMetricV31", "cvssMetricV30", "cvssMetricV2"):
        entries = metrics.get(key) or []
        if not entries:
            continue
        first = entries[0] or {}
        data = first.get("cvssData") or {}
        score = data.get("baseScore")
        if isinstance(score, (int, float)):
            return float(score)
    return None


def _parse_cves_from_payload(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Convert NVD response payload to compact CVE entries."""
    cves: List[Dict[str, Any]] = []
    for item in payload.get("vulnerabilities") or []:
        cve = item.get("cve") or {}
        cve_id = cve.get("id")
        if not cve_id:
            continue
        cves.append({"id": cve_id, "cvss": _extract_cvss(cve.get("metrics") or {})})
    return cves


def _fetch_cve_by_id(cve_id: str) -> Dict[str, Any]:
    """Fetch a single CVE by exact ID from NVD."""
    response = requests.get(
        NVD_API_URL,
        params={"cveId": cve_id},
        headers={"apiKey": NVD_API_KEY, "User-Agent": USER_AGENT},
        timeout=HTTP_TIMEOUT,
    )
    if response.status_code != 200:
        return {"cves": [], "error": f"NVD HTTP {response.status_code}"}
    return {"cves": _parse_cves_from_payload(response.json())}


def search_cves(product: str, version: str, limit: int = 5, cve_ids: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Search NVD for product/version and return compact CVE/CVSS data.

    Returns an empty, non-error result when NVD_API_KEY is absent.
    """
    product = (product or "").strip().lower()
    version = (version or "").strip()
    cve_ids = list(dict.fromkeys([cve for cve in (cve_ids or []) if cve]))
    if not product or not version:
        return {"enabled": False, "cves": [], "cvss_max": None}
    if not NVD_API_KEY:
        return {"enabled": False, "cves": [], "cvss_max": None}

    cache_key = f"nvd:v3:{product}:{version}:{limit}:{','.join(cve_ids)}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    try:
        if cve_ids:
            all_cves: List[Dict[str, Any]] = []
            errors: List[str] = []
            for cve_id in cve_ids[:10]:
                item = _fetch_cve_by_id(cve_id)
                all_cves.extend(item.get("cves") or [])
                if item.get("error"):
                    errors.append(f"{cve_id}: {item['error']}")

            cvss_values = [cve["cvss"] for cve in all_cves if isinstance(cve.get("cvss"), (int, float))]
            result = {
                "enabled": True,
                "cves": all_cves,
                "cvss_max": max(cvss_values) if cvss_values else None,
                "error": "; ".join(errors) if errors else None,
            }
            if all_cves or result["cvss_max"] is not None:
                _cache_set(cache_key, result)
            return result

        # NVD 2.0 expects apiKey in the HTTP header. Passing apiKey as a query
        # parameter produces "Invalid parameter: apiKey" responses.
        response = requests.get(
            NVD_API_URL,
            params={
                "keywordSearch": f"{product} {version}",
                "resultsPerPage": limit,
            },
            headers={"apiKey": NVD_API_KEY, "User-Agent": USER_AGENT},
            timeout=HTTP_TIMEOUT,
        )
        if response.status_code != 200:
            return {"enabled": True, "cves": [], "cvss_max": None, "error": f"NVD HTTP {response.status_code}"}

        cves = _parse_cves_from_payload(response.json())
        cvss_values = [cve["cvss"] for cve in cves if isinstance(cve.get("cvss"), (int, float))]

        result = {
            "enabled": True,
            "cves": cves,
            "cvss_max": max(cvss_values) if cvss_values else None,
        }
        if cves or result["cvss_max"] is not None:
            _cache_set(cache_key, result)
        return result
    except Exception as exc:
        return {"enabled": True, "cves": [], "cvss_max": None, "error": str(exc)}
