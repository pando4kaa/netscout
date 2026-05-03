"""
Optional FIRST EPSS client for CVE exploitability enrichment.
"""

import json
from typing import Any, Dict, Iterable, List

import requests

from src.config.settings import HTTP_TIMEOUT, REDIS_URL, USER_AGENT


EPSS_API_URL = "https://api.first.org/data/v1/epss"
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


def get_epss_scores(cve_ids: Iterable[str]) -> Dict[str, Dict[str, Any]]:
    """
    Return EPSS data keyed by CVE ID.

    EPSS is a probability signal, not a severity score. Failures return an empty
    mapping so scans can continue without external threat intelligence.
    """
    ids: List[str] = sorted({str(cve).upper() for cve in cve_ids if cve})
    if not ids:
        return {}

    cache_key = f"epss:v1:{','.join(ids)}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    try:
        response = requests.get(
            EPSS_API_URL,
            params={"cve": ",".join(ids)},
            headers={"User-Agent": USER_AGENT},
            timeout=HTTP_TIMEOUT,
        )
        if response.status_code != 200:
            return {}

        result: Dict[str, Dict[str, Any]] = {}
        for item in response.json().get("data") or []:
            cve = str(item.get("cve") or "").upper()
            if not cve:
                continue
            try:
                epss = float(item.get("epss"))
            except (TypeError, ValueError):
                epss = None
            try:
                percentile = float(item.get("percentile"))
            except (TypeError, ValueError):
                percentile = None
            result[cve] = {
                "epss": epss,
                "percentile": percentile,
                "date": item.get("date"),
            }

        _cache_set(cache_key, result)
        return result
    except Exception:
        return {}
