"""
Sliding-window rate limiting for external APIs (e.g. VirusTotal: 4 req/min).
"""

import logging
import time

from src.services._redis import get_shared_redis

logger = logging.getLogger(__name__)


def acquire(provider: str, max_requests: int = 4, window_seconds: int = 60) -> bool:
    """
    Sliding-window rate limit. Returns ``True`` when the call is allowed.

    Uses Redis sorted-sets keyed by ``ratelimit:{provider}``.
    Fails open (returns ``True``) if Redis is unavailable, on the assumption
    that scans should not block on infrastructure outages.
    """
    client = get_shared_redis()
    if not client:
        return True

    key = f"ratelimit:{provider}"
    now = time.time()
    window_start = now - window_seconds
    try:
        pipe = client.pipeline()
        pipe.zremrangebyscore(key, 0, window_start)
        pipe.zcard(key)
        pipe.zadd(key, {str(now): now})
        pipe.expire(key, window_seconds + 10)
        results = pipe.execute()
        return results[1] < max_requests
    except Exception as exc:
        logger.warning("Rate limit check failed for %s: %s", provider, exc)
        return True
