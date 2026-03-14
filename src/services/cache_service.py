"""
Redis cache for external API responses.
Keys: vt:domain:{domain}, crtsh:{domain}, whois:{domain}
TTL: VirusTotal 30 min, crt.sh 1 hour, WHOIS 24 hours.
"""

import json
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

_redis_client: Optional[Any] = None


def _get_redis():
    """Lazy init Redis client."""
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    try:
        from src.config.settings import REDIS_URL
        if not REDIS_URL:
            return None
        import redis
        _redis_client = redis.from_url(REDIS_URL, decode_responses=True)
        _redis_client.ping()
        return _redis_client
    except Exception as e:
        logger.debug("Redis not available: %s", e)
        return None


def get(key: str) -> Optional[Any]:
    """Get cached value. Returns None if not found or Redis unavailable."""
    r = _get_redis()
    if not r:
        return None
    try:
        raw = r.get(key)
        if raw is None:
            return None
        return json.loads(raw)
    except Exception as e:
        logger.warning("Cache get failed for %s: %s", key, e)
        return None


def set(key: str, value: Any, ttl_seconds: int) -> bool:
    """Set cached value with TTL. Returns False if Redis unavailable."""
    r = _get_redis()
    if not r:
        return False
    try:
        r.setex(key, ttl_seconds, json.dumps(value, default=str))
        return True
    except Exception as e:
        logger.warning("Cache set failed for %s: %s", key, e)
        return False


# TTL constants (seconds)
TTL_VIRUSTOTAL = 30 * 60   # 30 min
TTL_CRTSH = 60 * 60        # 1 hour
TTL_WHOIS = 24 * 60 * 60   # 24 hours
