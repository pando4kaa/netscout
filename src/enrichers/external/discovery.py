"""
Passive-discovery external API clients.

Returns either a normalised ``dict`` payload or ``None`` on failure / missing
key. Failures are logged and never propagate.

Providers:
    * URLScan.io      - historical scan results for a domain
    * SecurityTrails  - WHOIS / tags / current DNS metadata
    * ZoomEye         - host search by domain
    * Wayback Machine - first archived snapshot
    * SSL Labs        - TLS / cipher audit (long-poll, up to ~2 min)
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

import aiohttp

from src.config.settings import HTTP_TIMEOUT, USER_AGENT

logger = logging.getLogger(__name__)

_WAYBACK_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
}
_SSLLABS_MAX_POLLS = 13
_SSLLABS_POLL_INTERVAL_SECONDS = 10
_SSLLABS_REQUEST_TIMEOUT_SECONDS = 30
_WEAK_TLS_PROTOCOLS = ("SSL 3.0", "TLS 1.0", "TLS 1.1")


async def fetch_urlscan_search(
    session: aiohttp.ClientSession, domain: str
) -> Optional[Dict[str, Any]]:
    """Query URLScan.io for historical scans of ``domain`` (free, no API key)."""
    try:
        url = "https://urlscan.io/api/v1/search/"
        params = {"q": f"domain:{domain}"}
        async with session.get(
            url, params=params, timeout=aiohttp.ClientTimeout(total=HTTP_TIMEOUT)
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                raw_results = data.get("results", [])[:50]
                url_counts: Dict[str, int] = {}
                for entry in raw_results:
                    page_url = entry.get("page", {}).get("url")
                    if page_url:
                        url_counts[page_url] = url_counts.get(page_url, 0) + 1
                top_urls = sorted(
                    url_counts.keys(), key=lambda u: (-url_counts[u], u)
                )[:15]
                return {
                    "total": data.get("total", 0),
                    "unique_count": len(url_counts),
                    "urls": [{"url": u, "scan_count": url_counts[u]} for u in top_urls],
                }
    except Exception as exc:
        logger.debug("URLScan request failed: domain=%s error=%s", domain, exc)
    return None


async def fetch_securitytrails_domain(
    session: aiohttp.ClientSession, domain: str, api_key: str
) -> Optional[Dict[str, Any]]:
    """Query SecurityTrails for domain metadata (subdomain count, current DNS, tags)."""
    if not api_key:
        return None
    try:
        url = f"https://api.securitytrails.com/v1/domain/{domain}"
        headers = {"User-Agent": USER_AGENT, "apikey": api_key}
        async with session.get(
            url, headers=headers, timeout=aiohttp.ClientTimeout(total=HTTP_TIMEOUT)
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                return {
                    "domain": domain,
                    "subdomain_count": data.get("subdomain_count"),
                    "current_dns": data.get("current_dns"),
                    "tags": data.get("tags") or [],
                }
    except Exception as exc:
        logger.debug("SecurityTrails request failed: domain=%s error=%s", domain, exc)
    return None


async def fetch_zoomeye_search(
    session: aiohttp.ClientSession, domain: str, api_key: str
) -> Optional[Dict[str, Any]]:
    """Search ZoomEye for hosts associated with ``domain``."""
    if not api_key:
        return None
    try:
        url = "https://api.zoomeye.ai/host/search"
        params = {
            "query": f"domain:{domain}",
            "page": 1,
            "facets": "app,os,country",
        }
        headers = {"User-Agent": USER_AGENT, "API-KEY": api_key}
        async with session.get(
            url, params=params, headers=headers,
            timeout=aiohttp.ClientTimeout(total=HTTP_TIMEOUT),
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                hosts: List[Dict[str, Any]] = []
                for match in data.get("matches", [])[:10]:
                    geoinfo = match.get("geoinfo") or {}
                    portinfo = match.get("portinfo") or {}
                    country_obj = (
                        geoinfo.get("country") if isinstance(geoinfo, dict) else {}
                    )
                    country = (
                        country_obj.get("names", {}).get("en")
                        if isinstance(country_obj, dict) else None
                    )
                    hosts.append({
                        "ip": match.get("ip"),
                        "port": portinfo.get("port") if isinstance(portinfo, dict) else None,
                        "country": country,
                        "asn": (
                            str(geoinfo.get("asn"))
                            if geoinfo.get("asn") is not None else None
                        ),
                        "app": portinfo.get("app") if isinstance(portinfo, dict) else None,
                    })
                return {"domain": domain, "total": data.get("total", 0), "hosts": hosts}
    except Exception as exc:
        logger.debug("ZoomEye request failed: domain=%s error=%s", domain, exc)
    return None


async def fetch_wayback_first_snapshot(
    session: aiohttp.ClientSession, domain: str
) -> Optional[Dict[str, Any]]:
    """Get the earliest archived snapshot from Internet Archive's CDX API."""
    try:
        url = "https://web.archive.org/cdx/search/cdx"
        candidates = [
            f"https://{domain}/",
            f"http://{domain}/",
            f"https://www.{domain}/",
            domain,
        ]
        for target in candidates:
            params = {"url": target, "output": "json", "limit": 1}
            async with session.get(
                url, params=params, headers=_WAYBACK_BROWSER_HEADERS,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status != 200:
                    continue
                data = await resp.json()
                if isinstance(data, list) and len(data) >= 2 and len(data[1]) >= 3:
                    timestamp, original = data[1][1], data[1][2]
                    return {
                        "domain": domain,
                        "first_snapshot_timestamp": timestamp,
                        "first_snapshot_url": (
                            f"https://web.archive.org/web/{timestamp}/{original}"
                        ),
                        "original_url": original,
                    }
    except Exception as exc:
        return {"domain": domain, "error": str(exc)[:60]}
    return {"domain": domain, "error": "No snapshots found or access denied"}


async def fetch_ssllabs_analyze(
    session: aiohttp.ClientSession, domain: str
) -> Optional[Dict[str, Any]]:
    """Query SSL Labs API for TLS / cipher audit. Polls until READY (~2 min cap)."""
    try:
        api_url = "https://api.ssllabs.com/api/v3/analyze"
        headers = {"User-Agent": USER_AGENT}
        # First call uses fromCache=off so a brand-new domain triggers a real
        # analysis instead of returning nothing; subsequent polls read the
        # in-progress run.
        params: Dict[str, str] = {"host": domain, "all": "done", "fromCache": "off"}
        for _ in range(_SSLLABS_MAX_POLLS):
            async with session.get(
                api_url, params=params, headers=headers,
                timeout=aiohttp.ClientTimeout(total=_SSLLABS_REQUEST_TIMEOUT_SECONDS),
            ) as resp:
                if resp.status != 200:
                    break
                data = await resp.json()
                status = data.get("status")
                if status == "READY":
                    weak_protocols: List[str] = []
                    for endpoint in data.get("endpoints") or []:
                        details = endpoint.get("details") or {}
                        for protocol in details.get("protocols") or []:
                            name = protocol.get("name", "")
                            if name in _WEAK_TLS_PROTOCOLS:
                                weak_protocols.append(name)
                    weak_protocols = list(dict.fromkeys(weak_protocols))
                    return {
                        "domain": domain,
                        "grade": data.get("grade"),
                        "weak_protocols": weak_protocols,
                        "has_weak_protocols": bool(weak_protocols),
                    }
                if status == "ERROR":
                    return {
                        "domain": domain,
                        "error": data.get("statusMessage", "Analysis failed"),
                    }
                params = {"host": domain, "all": "done"}
            await asyncio.sleep(_SSLLABS_POLL_INTERVAL_SECONDS)
        return {
            "domain": domain,
            "error": "Analysis timed out (SSL Labs may take 2+ min for new domains)",
        }
    except Exception as exc:
        return {"domain": domain, "error": str(exc)[:80]}
