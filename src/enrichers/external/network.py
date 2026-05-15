"""
Network / ASN external API clients.

Uses RIPE NCC RIPEstat Data API (no API key, JSON). Replaces the former BGPView
integration which became unreliable.

Docs: https://stat.ripe.net/docs/data-api
"""

import logging
from typing import Any, Dict, Optional

import aiohttp

from src.config.settings import HTTP_TIMEOUT

logger = logging.getLogger(__name__)

RIPESTAT_BASE = "https://stat.ripe.net/data"


async def fetch_ripestat_ip(
    session: aiohttp.ClientSession, ip: str
) -> Optional[Dict[str, Any]]:
    """
    Resolve IP to originating ASN and covering prefix via RIPEstat.

    1. ``network-info`` — ASN list and longest-prefix match.
    2. ``as-overview`` — human-readable holder name (optional; skipped on failure).

    Returns the same shape as the legacy BGPView client for downstream code:
    ``ip``, ``asn`` (int), ``asn_name`` (str | None), ``prefix`` (str | None).
    """
    timeout = aiohttp.ClientTimeout(total=HTTP_TIMEOUT)
    try:
        net_url = f"{RIPESTAT_BASE}/network-info/data.json"
        async with session.get(
            net_url, params={"resource": ip}, timeout=timeout
        ) as resp:
            if resp.status != 200:
                return None
            body = await resp.json()
        if not isinstance(body, dict) or body.get("status") != "ok":
            return None
        data = body.get("data") or {}
        asns = data.get("asns") or []
        prefix = (data.get("prefix") or "").strip() or None
        if not asns:
            return None
        asn_raw = asns[0]
        try:
            asn = int(str(asn_raw).strip())
        except (TypeError, ValueError):
            return None

        holder: Optional[str] = None
        as_url = f"{RIPESTAT_BASE}/as-overview/data.json"
        try:
            async with session.get(
                as_url, params={"resource": str(asn)}, timeout=timeout
            ) as resp2:
                if resp2.status == 200:
                    overview = await resp2.json()
                    if isinstance(overview, dict) and overview.get("status") == "ok":
                        od = overview.get("data") or {}
                        holder = od.get("holder")
                        if holder is not None:
                            holder = str(holder).strip() or None
        except Exception as exc:
            logger.debug("RIPEstat as-overview failed: asn=%s error=%s", asn, exc)

        return {
            "ip": ip,
            "asn": asn,
            "asn_name": holder,
            "prefix": prefix,
        }
    except Exception as exc:
        logger.debug("RIPEstat network-info failed: ip=%s error=%s", ip, exc)
    return None
