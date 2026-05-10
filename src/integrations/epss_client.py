"""
Optional FIRST EPSS client for CVE exploitability enrichment.
"""

import logging
from typing import Any, Dict, Iterable, List, Optional

import requests

from src.config.settings import HTTP_TIMEOUT, USER_AGENT
from src.integrations._redis_cache import cache_get, cache_set

logger = logging.getLogger(__name__)

EPSS_API_URL = "https://api.first.org/data/v1/epss"


def _coerce_float(value: Any) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def get_epss_scores(cve_ids: Iterable[str]) -> Dict[str, Dict[str, Any]]:
    """
    Return EPSS data keyed by CVE ID.

    EPSS is a probability signal, not a severity score. Failures return an
    empty mapping so scans can continue without external threat intelligence.
    """
    ids: List[str] = sorted({str(cve).upper() for cve in cve_ids if cve})
    if not ids:
        return {}

    cache_key = f"epss:v1:{','.join(ids)}"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    try:
        response = requests.get(
            EPSS_API_URL,
            params={"cve": ",".join(ids)},
            headers={"User-Agent": USER_AGENT},
            timeout=HTTP_TIMEOUT,
        )
    except requests.RequestException as exc:
        logger.debug("EPSS fetch failed: %s", exc)
        return {}
    if response.status_code != 200:
        return {}

    try:
        payload = response.json()
    except ValueError as exc:
        logger.debug("EPSS JSON parse failed: %s", exc)
        return {}

    result: Dict[str, Dict[str, Any]] = {}
    for item in payload.get("data") or []:
        cve = str(item.get("cve") or "").upper()
        if not cve:
            continue
        result[cve] = {
            "epss": _coerce_float(item.get("epss")),
            "percentile": _coerce_float(item.get("percentile")),
            "date": item.get("date"),
        }

    cache_set(cache_key, result)
    return result
