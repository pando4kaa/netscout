"""
Redis cache for external API responses.

Public functions ``get(key)`` and ``set(key, value, ttl_seconds)`` are kept
with their historical names for backwards compatibility (callers already
import them as ``set as cache_set``). The shared Redis client lives in
``src.services._redis``.
"""

import json
import logging
from typing import Any, Optional

from src.services._redis import get_shared_redis

logger = logging.getLogger(__name__)

# TTLs (seconds) reused by enrichers and integrations.
TTL_VIRUSTOTAL = 30 * 60        # 30 min
TTL_CRTSH = 60 * 60             # 1 hour
TTL_WHOIS = 24 * 60 * 60        # 24 hours


def get(key: str) -> Optional[Any]:
    """Return the cached JSON value for ``key`` or ``None`` if absent."""
    client = get_shared_redis()
    if not client:
        return None
    try:
        raw = client.get(key)
        return json.loads(raw) if raw is not None else None
    except Exception as exc:
        logger.warning("Cache get failed for %s: %s", key, exc)
        return None


def set(key: str, value: Any, ttl_seconds: int) -> bool:  # noqa: A001 - public API kept for back-compat
    """Cache ``value`` under ``key`` with ``ttl_seconds`` TTL."""
    client = get_shared_redis()
    if not client:
        return False
    try:
        client.setex(key, ttl_seconds, json.dumps(value, default=str))
        return True
    except Exception as exc:
        logger.warning("Cache set failed for %s: %s", key, exc)
        return False
