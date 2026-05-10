"""
Process-wide Redis client used by cache and rate-limit services.

Best-effort: when ``REDIS_URL`` is empty or Redis is unreachable the helper
returns ``None`` and callers are expected to degrade gracefully.
"""

import logging
from typing import Any, Optional

from src.config.settings import REDIS_URL

logger = logging.getLogger(__name__)

_redis_client: Optional[Any] = None
_init_failed: bool = False


def get_shared_redis() -> Optional[Any]:
    """Return the lazily-initialised Redis client, or ``None`` if unavailable."""
    global _redis_client, _init_failed
    if _redis_client is not None:
        return _redis_client
    if _init_failed or not REDIS_URL:
        return None
    try:
        import redis  # local: optional dep

        client = redis.from_url(REDIS_URL, decode_responses=True)
        client.ping()
        _redis_client = client
        return _redis_client
    except Exception as exc:
        logger.debug("Redis not available: %s", exc)
        _init_failed = True
        return None
