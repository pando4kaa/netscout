"""
Minimal NVD API client for CVE/CVSS enrichment.

The integration is intentionally optional: without `NVD_API_KEY` the scan keeps
using local heuristics and never fails because of CVE enrichment.
"""

import logging
from typing import Any, Dict, List, Optional

import requests

from src.config.settings import HTTP_TIMEOUT, NVD_API_KEY, USER_AGENT
from src.integrations._redis_cache import cache_get, cache_set

logger = logging.getLogger(__name__)

NVD_API_URL = "https://services.nvd.nist.gov/rest/json/cves/2.0"
_MAX_CVES_PER_BATCH = 10
_CVSS_METRIC_PRIORITY = ("cvssMetricV31", "cvssMetricV30", "cvssMetricV2")


def _extract_cvss(metrics: Dict[str, Any]) -> Optional[float]:
    """Extract the highest-priority CVSS base score from NVD metrics."""
    for key in _CVSS_METRIC_PRIORITY:
        entries = metrics.get(key) or []
        if not entries:
            continue
        first = entries[0] or {}
        score = (first.get("cvssData") or {}).get("baseScore")
        if isinstance(score, (int, float)):
            return float(score)
    return None


def _parse_cves_from_payload(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Convert an NVD response payload into compact `{id, cvss}` entries."""
    cves: List[Dict[str, Any]] = []
    for item in payload.get("vulnerabilities") or []:
        cve = item.get("cve") or {}
        cve_id = cve.get("id")
        if not cve_id:
            continue
        cves.append({"id": cve_id, "cvss": _extract_cvss(cve.get("metrics") or {})})
    return cves


def _max_cvss(cves: List[Dict[str, Any]]) -> Optional[float]:
    scores = [cve["cvss"] for cve in cves if isinstance(cve.get("cvss"), (int, float))]
    return max(scores) if scores else None


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


def search_cves(
    product: str,
    version: str,
    limit: int = 5,
    cve_ids: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Search NVD for `product`/`version` and return compact CVE/CVSS data.

    Returns a non-error empty result when `NVD_API_KEY` is absent.
    """
    product = (product or "").strip().lower()
    version = (version or "").strip()
    cve_ids = list(dict.fromkeys([cve for cve in (cve_ids or []) if cve]))
    if not product or not version:
        return {"enabled": False, "cves": [], "cvss_max": None}
    if not NVD_API_KEY:
        return {"enabled": False, "cves": [], "cvss_max": None}

    cache_key = f"nvd:v3:{product}:{version}:{limit}:{','.join(cve_ids)}"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    try:
        if cve_ids:
            return _search_by_cve_ids(cache_key, cve_ids)
        return _search_by_keyword(cache_key, product, version, limit)
    except requests.RequestException as exc:
        logger.debug("NVD request failed: %s", exc)
        return {"enabled": True, "cves": [], "cvss_max": None, "error": str(exc)}
    except Exception as exc:
        logger.debug("NVD unexpected error: %s", exc)
        return {"enabled": True, "cves": [], "cvss_max": None, "error": str(exc)}


def _search_by_cve_ids(cache_key: str, cve_ids: List[str]) -> Dict[str, Any]:
    all_cves: List[Dict[str, Any]] = []
    errors: List[str] = []
    for cve_id in cve_ids[:_MAX_CVES_PER_BATCH]:
        item = _fetch_cve_by_id(cve_id)
        all_cves.extend(item.get("cves") or [])
        if item.get("error"):
            errors.append(f"{cve_id}: {item['error']}")

    result = {
        "enabled": True,
        "cves": all_cves,
        "cvss_max": _max_cvss(all_cves),
        "error": "; ".join(errors) if errors else None,
    }
    if all_cves or result["cvss_max"] is not None:
        cache_set(cache_key, result)
    return result


def _search_by_keyword(cache_key: str, product: str, version: str, limit: int) -> Dict[str, Any]:
    # NVD 2.0 expects `apiKey` in the HTTP header. Passing `apiKey` as a query
    # parameter produces "Invalid parameter: apiKey" responses.
    response = requests.get(
        NVD_API_URL,
        params={"keywordSearch": f"{product} {version}", "resultsPerPage": limit},
        headers={"apiKey": NVD_API_KEY, "User-Agent": USER_AGENT},
        timeout=HTTP_TIMEOUT,
    )
    if response.status_code != 200:
        return {"enabled": True, "cves": [], "cvss_max": None, "error": f"NVD HTTP {response.status_code}"}

    cves = _parse_cves_from_payload(response.json())
    result = {"enabled": True, "cves": cves, "cvss_max": _max_cvss(cves)}
    if cves or result["cvss_max"] is not None:
        cache_set(cache_key, result)
    return result
