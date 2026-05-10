"""
Lightweight Redis-backed JSON cache shared by integration clients.

Used by NVD, EPSS and CISA KEV clients to avoid hammering external APIs.
All operations are best-effort: if Redis is missing or misbehaves, calls
silently degrade to no-op so scans always continue.
"""

import json
import logging
from typing import Any, Dict, Optional

from src.services._redis import get_shared_redis

logger = logging.getLogger(__name__)

_DEFAULT_TTL_SECONDS = 24 * 60 * 60


def cache_get(key: str) -> Optional[Dict[str, Any]]:
    client = get_shared_redis()
    if not client:
        return None
    try:
        raw = client.get(key)
        return json.loads(raw) if raw else None
    except Exception as exc:
        logger.debug("Redis GET failed for %s: %s", key, exc)
        return None


def cache_set(key: str, value: Dict[str, Any], ttl_seconds: int = _DEFAULT_TTL_SECONDS) -> None:
    client = get_shared_redis()
    if not client:
        return
    try:
        client.setex(key, ttl_seconds, json.dumps(value))
    except Exception as exc:
        logger.debug("Redis SETEX failed for %s: %s", key, exc)
