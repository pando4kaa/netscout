"""
Network/ASN external API clients.

Currently only BGPView. Returns a normalised ``dict`` or ``None`` on failure.
"""

import logging
from typing import Any, Dict, Optional

import aiohttp

from src.config.settings import HTTP_TIMEOUT

logger = logging.getLogger(__name__)


async def fetch_bgpview_ip(
    session: aiohttp.ClientSession, ip: str
) -> Optional[Dict[str, Any]]:
    """Query BGPView for IP/ASN info (free, no API key)."""
    try:
        url = f"https://api.bgpview.io/ip/{ip}"
        async with session.get(
            url, timeout=aiohttp.ClientTimeout(total=HTTP_TIMEOUT)
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                payload = (
                    data.get("data") if isinstance(data.get("data"), dict) else data
                )
                rir = (
                    payload.get("rir_allocation")
                    if isinstance(payload.get("rir_allocation"), dict) else {}
                )
                return {
                    "ip": ip,
                    "asn": payload.get("asn"),
                    "asn_name": rir.get("name") or payload.get("name"),
                    "prefix": payload.get("prefix"),
                }
    except Exception as exc:
        logger.debug("BGPView request failed: ip=%s error=%s", ip, exc)
    return None
