"""
Threat-intelligence external API clients.

Each client returns a normalised ``dict`` (provider-specific shape) or ``None``
when the API has no data, the key is missing, or the request fails. All HTTP
calls use timeouts and never raise to the caller; failures are logged.

Providers covered here:
    * VirusTotal       - reputation lookup (cached + rate-limited)
    * AlienVault OTX   - pulse / threat indicators
    * AbuseIPDB        - IP abuse score
    * ThreatCrowd      - free domain threat intel
    * PhishTank        - phishing URL lookup
    * Pulsedive        - aggregated threat intel
    * Criminal IP      - domain risk score
"""

import asyncio
import json
import logging
from typing import Any, Dict, Optional

import aiohttp

from src.config.settings import (
    ALIENVAULT_OTX_API_KEY,
    HTTP_TIMEOUT,
    USER_AGENT,
    VIRUSTOTAL_API_KEY,
)

from ._common import PHISHTANK_PLACEHOLDER_KEY

logger = logging.getLogger(__name__)


async def fetch_virustotal_domain(
    session: aiohttp.ClientSession, domain: str
) -> Optional[Dict[str, Any]]:
    """Query VirusTotal v3 domain API. Uses Redis cache and a sliding rate limit."""
    if not VIRUSTOTAL_API_KEY:
        return None
    try:
        from src.services.cache_service import TTL_VIRUSTOTAL, get, set
        from src.services.rate_limit_service import acquire

        cache_key = f"vt:domain:{domain}"
        cached = get(cache_key)
        if cached is not None:
            return cached

        if not acquire("virustotal", max_requests=4, window_seconds=60):
            logger.warning("VirusTotal rate limited, skipping")
            return None

        from tenacity import (
            retry,
            retry_if_exception_type,
            stop_after_attempt,
            wait_exponential,
        )

        class RateLimitedError(Exception):
            pass

        @retry(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=4, max=60),
            retry=retry_if_exception_type(RateLimitedError),
            reraise=True,
        )
        async def _fetch() -> Optional[Dict[str, Any]]:
            url = f"https://www.virustotal.com/api/v3/domains/{domain}"
            headers = {"User-Agent": USER_AGENT, "x-apikey": VIRUSTOTAL_API_KEY}
            async with session.get(
                url, headers=headers, timeout=aiohttp.ClientTimeout(total=HTTP_TIMEOUT)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    set(cache_key, data, TTL_VIRUSTOTAL)
                    return data
                if resp.status == 429:
                    retry_after = resp.headers.get("Retry-After")
                    wait = int(retry_after) if retry_after and retry_after.isdigit() else 60
                    await asyncio.sleep(min(wait, 120))
                    raise RateLimitedError("VirusTotal rate limited")
                return None

        return await _fetch()
    except Exception as exc:
        logger.warning("VirusTotal request failed: domain=%s error=%s", domain, exc)
        return None


async def fetch_alienvault_otx_domain(
    session: aiohttp.ClientSession, domain: str
) -> Optional[Dict[str, Any]]:
    """Query AlienVault OTX for domain indicators (free key required)."""
    if not ALIENVAULT_OTX_API_KEY:
        return None
    try:
        url = f"https://otx.alienvault.com/api/v1/indicators/domain/{domain}/general"
        headers = {"User-Agent": USER_AGENT, "X-OTX-API-KEY": ALIENVAULT_OTX_API_KEY}
        async with session.get(
            url, headers=headers, timeout=aiohttp.ClientTimeout(total=HTTP_TIMEOUT)
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                alexa = data.get("alexa", "")
                whois = data.get("whois", "")
                return {
                    "pulse_count": data.get("pulse_info", {}).get("count", 0),
                    "validation": data.get("validation", []),
                    "alexa_url": alexa if isinstance(alexa, str) and alexa.startswith("http") else None,
                    "whois_url": whois if isinstance(whois, str) and whois.startswith("http") else None,
                }
            if resp.status == 429:
                await asyncio.sleep(5)
    except Exception as exc:
        logger.debug("AlienVault OTX request failed: domain=%s error=%s", domain, exc)
    return None


async def fetch_abuseipdb_check(
    session: aiohttp.ClientSession, ip: str, api_key: str
) -> Optional[Dict[str, Any]]:
    """Query AbuseIPDB for IP reputation - 1000 checks/day."""
    if not api_key:
        return None
    try:
        url = "https://api.abuseipdb.com/api/v2/check"
        params = {"ipAddress": ip, "maxAgeInDays": 90}
        headers = {"User-Agent": USER_AGENT, "Key": api_key, "Accept": "application/json"}
        async with session.get(
            url, params=params, headers=headers,
            timeout=aiohttp.ClientTimeout(total=HTTP_TIMEOUT),
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                payload = data.get("data") or {}
                return {
                    "ip": ip,
                    "abuse_score": payload.get("abuseConfidenceScore"),
                    "total_reports": payload.get("totalReports"),
                    "num_users": payload.get("numDistinctUsers"),
                    "isp": payload.get("isp"),
                    "country_code": payload.get("countryCode"),
                    "usage_type": payload.get("usageType"),
                }
            if resp.status == 429:
                await asyncio.sleep(5)
    except Exception as exc:
        logger.debug("AbuseIPDB request failed: ip=%s error=%s", ip, exc)
    return None


async def fetch_threatcrowd_domain(
    session: aiohttp.ClientSession, domain: str
) -> Optional[Dict[str, Any]]:
    """Query ThreatCrowd for domain threat intel (free, no API key)."""
    try:
        url = "https://www.threatcrowd.org/searchApi/v2/domain/report/"
        params = {"domain": domain}
        async with session.get(
            url, params=params, timeout=aiohttp.ClientTimeout(total=HTTP_TIMEOUT)
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                return {
                    "votes": data.get("votes"),
                    "references": (data.get("references") or [])[:5],
                    "subdomains": (data.get("subdomains") or [])[:10],
                    "resolutions": (data.get("resolutions") or [])[:10],
                }
    except Exception as exc:
        logger.debug("ThreatCrowd request failed: domain=%s error=%s", domain, exc)
    return None


async def fetch_phishtank_check(
    session: aiohttp.ClientSession, url: str, app_key: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Check URL against the PhishTank phishing database (app_key optional)."""
    try:
        post_url = "https://checkurl.phishtank.com/checkurl/"
        body: Dict[str, str] = {"url": url, "format": "json"}
        if app_key and app_key != PHISHTANK_PLACEHOLDER_KEY:
            body["app_key"] = app_key
        headers = {
            "User-Agent": USER_AGENT,
            "Content-Type": "application/x-www-form-urlencoded",
        }
        async with session.post(
            post_url, data=body, headers=headers,
            timeout=aiohttp.ClientTimeout(total=HTTP_TIMEOUT),
        ) as resp:
            if resp.status == 200:
                result = await resp.json()
                results = result.get("results", {}) if isinstance(result, dict) else {}
                return {
                    "url": url,
                    "in_database": results.get("in_database", False),
                    "valid": results.get("valid"),
                    "verified": results.get("verified"),
                    "phish_id": results.get("phish_id"),
                    "phish_detail_page": results.get("phish_detail_page"),
                }
            text = await resp.text()
            hint = (
                "Cloudflare block"
                if resp.status == 403 and "cf_chl" in text[:500]
                else (text[:150] + "..." if len(text) > 150 else text)
            )
            logger.warning("PhishTank API error: url=%s status=%s (%s)", url, resp.status, hint)
    except Exception as exc:
        logger.warning("PhishTank request failed: url=%s error=%s", url, exc)
    return None


async def fetch_pulsedive_info(
    session: aiohttp.ClientSession, domain: str, api_key: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Query Pulsedive for domain threat intel - 50/day, 500/month."""
    try:
        url = "https://pulsedive.com/api/info.php"
        params: Dict[str, str] = {"indicator": domain, "pretty": "1"}
        if api_key:
            params["key"] = api_key
        headers = {"User-Agent": USER_AGENT}
        async with session.get(
            url, params=params, headers=headers,
            timeout=aiohttp.ClientTimeout(total=HTTP_TIMEOUT),
        ) as resp:
            text = await resp.text()
            if resp.status == 200:
                data = json.loads(text) if text else {}
                summary = {
                    "domain": domain,
                    "risk": data.get("risk"),
                    "risk_recommendation": data.get("risk_recommendation"),
                    "threats": data.get("threats", [])[:5],
                    "feeds": data.get("feeds", [])[:5],
                    "properties": data.get("properties", {}),
                }
                logger.info(
                    "Pulsedive: domain=%s risk=%s threats=%s",
                    domain, summary.get("risk"), len(summary.get("threats") or []),
                )
                return summary
            if resp.status == 404 and "Indicator not found" in (text or ""):
                logger.info("Pulsedive: domain=%s not in threat database (clean)", domain)
                return {
                    "domain": domain,
                    "risk": "none",
                    "risk_recommendation": "Domain not in threat database",
                    "threats": [],
                    "feeds": [],
                }
            logger.warning(
                "Pulsedive API error: domain=%s status=%s body=%s",
                domain, resp.status, text[:200] if text else "",
            )
    except Exception as exc:
        logger.warning("Pulsedive request failed: domain=%s error=%s", domain, exc)
    return None


async def fetch_criminalip_domain(
    session: aiohttp.ClientSession, domain: str, api_key: str
) -> Optional[Dict[str, Any]]:
    """Query Criminal IP domain quick view."""
    if not api_key:
        return None
    try:
        url = "https://api.criminalip.io/v1/domain/quick/malicious/view"
        params = {"domain": domain}
        headers = {"User-Agent": USER_AGENT, "x-api-key": api_key}
        async with session.get(
            url, params=params, headers=headers,
            timeout=aiohttp.ClientTimeout(total=HTTP_TIMEOUT),
        ) as resp:
            text = await resp.text()
            if resp.status == 200:
                data = json.loads(text) if text else {}
                return {
                    "domain": domain,
                    "risk_score": data.get("risk_score"),
                    "is_safe": data.get("is_safe"),
                    "data": data,
                }
            logger.warning(
                "Criminal IP API error: domain=%s status=%s body=%s",
                domain, resp.status, text[:200] if text else "",
            )
    except Exception as exc:
        logger.warning("Criminal IP request failed: domain=%s error=%s", domain, exc)
    return None
