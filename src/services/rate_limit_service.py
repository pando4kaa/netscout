"""
Rate limiting for external APIs using Redis sliding window.
VirusTotal: 4 req/min.
"""

import logging
import time
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
        logger.debug("Redis not available for rate limit: %s", e)
        return None


def acquire(provider: str, max_requests: int = 4, window_seconds: int = 60) -> bool:
    """
    Sliding window rate limit. Returns True if allowed, False if rate limited.
    Key: ratelimit:{provider}
    """
    r = _get_redis()
    if not r:
        return True  # No Redis = no rate limit
    key = f"ratelimit:{provider}"
    now = time.time()
    window_start = now - window_seconds
    try:
        pipe = r.pipeline()
        pipe.zremrangebyscore(key, 0, window_start)
        pipe.zcard(key)
        pipe.zadd(key, {str(now): now})
        pipe.expire(key, window_seconds + 10)
        results = pipe.execute()
        count = results[1]
        if count >= max_requests:
            return False
        return True
    except Exception as e:
        logger.warning("Rate limit check failed for %s: %s", provider, e)
        return True  # Fail open
