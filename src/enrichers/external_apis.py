"""
External API Enricher — Shodan, VirusTotal, Censys, AlienVault OTX, URLScan, BGPView, ThreatCrowd.
Uses aiohttp for async HTTP requests.
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)

import aiohttp

from src.config.settings import (
    HTTP_TIMEOUT,
    USER_AGENT,
    SHODAN_API_KEY,
    VIRUSTOTAL_API_KEY,
    CENSYS_API_TOKEN,
    CENSYS_API_ID,
    CENSYS_API_SECRET,
    ALIENVAULT_OTX_API_KEY,
    ABUSEIPDB_API_KEY,
    SECURITYTRAILS_API_KEY,
    ZOOMEYE_API_KEY,
    PHISHTANK_APP_KEY,
    CRIMINALIP_API_KEY,
    PULSEDIVE_API_KEY,
)

logger = logging.getLogger(__name__)
from src.enrichers.base import AbstractEnricher


async def _urlscan_search_async(session: aiohttp.ClientSession, domain: str) -> Optional[Dict[str, Any]]:
    """Query URLScan.io for domain scans (free, no API key)."""
    try:
        url = "https://urlscan.io/api/v1/search/"
        params = {"q": f"domain:{domain}"}
        async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=HTTP_TIMEOUT)) as resp:
            if resp.status == 200:
                data = await resp.json()
                raw_results = data.get("results", [])[:50]
                url_counts: Dict[str, int] = {}
                for r in raw_results:
                    u = r.get("page", {}).get("url")
                    if u:
                        url_counts[u] = url_counts.get(u, 0) + 1
                unique_urls = sorted(url_counts.keys(), key=lambda u: (-url_counts[u], u))[:15]
                return {
                    "total": data.get("total", 0),
                    "unique_count": len(url_counts),
                    "urls": [{"url": u, "scan_count": url_counts[u]} for u in unique_urls],
                }
    except Exception:
        pass
    return None


async def _wayback_first_snapshot_async(session: aiohttp.ClientSession, domain: str) -> Optional[Dict[str, Any]]:
    """Get first available snapshot from Web Archive (Wayback Machine). Free, no API key."""
    # IA may block generic bot User-Agent; use browser-like for CDX
    wayback_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json",
    }
    try:
        url = "https://web.archive.org/cdx/search/cdx"
        for target in [f"https://{domain}/", f"http://{domain}/", f"https://www.{domain}/", domain]:
            params = {"url": target, "output": "json", "limit": 1}
            async with session.get(
                url, params=params, headers=wayback_headers, timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                if resp.status != 200:
                    continue
                data = await resp.json()
                if isinstance(data, list) and len(data) >= 2:
                    row = data[1]
                    if len(row) >= 3:
                        timestamp, original = row[1], row[2]
                        snapshot_url = f"https://web.archive.org/web/{timestamp}/{original}"
                        return {
                            "domain": domain,
                            "first_snapshot_timestamp": timestamp,
                            "first_snapshot_url": snapshot_url,
                            "original_url": original,
                        }
    except Exception as e:
        return {"domain": domain, "error": str(e)[:60]}
    return {"domain": domain, "error": "No snapshots found or access denied"}


async def _ssllabs_analyze_async(session: aiohttp.ClientSession, domain: str) -> Optional[Dict[str, Any]]:
    """Query SSL Labs API for TLS/cipher audit. Free, no API key. Polls until READY (max 2 min)."""
    try:
        api_url = "https://api.ssllabs.com/api/v3/analyze"
        headers = {"User-Agent": USER_AGENT}
        # First request: fromCache=off to get cached OR start new analysis (fromCache=on returns nothing for new domains)
        params: Dict[str, str] = {"host": domain, "all": "done", "fromCache": "off"}
        for attempt in range(13):  # 13 * 10s = ~2 min max
            async with session.get(api_url, params=params, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status != 200:
                    break
                data = await resp.json()
                status = data.get("status")
                if status == "READY":
                    weak_protocols: List[str] = []
                    grade = data.get("grade")
                    for ep in data.get("endpoints") or []:
                        details = ep.get("details") or {}
                        for p in details.get("protocols") or []:
                            name = p.get("name", "")
                            if name in ("SSL 3.0", "TLS 1.0", "TLS 1.1"):
                                weak_protocols.append(name)
                    weak_protocols = list(dict.fromkeys(weak_protocols))
                    return {
                        "domain": domain,
                        "grade": grade,
                        "weak_protocols": weak_protocols,
                        "has_weak_protocols": len(weak_protocols) > 0,
                    }
                if status == "ERROR":
                    return {"domain": domain, "error": data.get("statusMessage", "Analysis failed")}
                # After first request, don't restart; just poll
                params = {"host": domain, "all": "done"}
            await asyncio.sleep(10)
        return {"domain": domain, "error": "Analysis timed out (SSL Labs may take 2+ min for new domains)"}
    except Exception as e:
        return {"domain": domain, "error": str(e)[:80]}
    return None


async def _threatcrowd_domain_async(session: aiohttp.ClientSession, domain: str) -> Optional[Dict[str, Any]]:
    """Query ThreatCrowd for domain threat intel (free, no API key)."""
    try:
        url = "https://www.threatcrowd.org/searchApi/v2/domain/report/"
        params = {"domain": domain}
        async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=HTTP_TIMEOUT)) as resp:
            if resp.status == 200:
                data = await resp.json()
                return {
                    "votes": data.get("votes"),
                    "references": (data.get("references") or [])[:5],
                    "subdomains": (data.get("subdomains") or [])[:10],
                    "resolutions": (data.get("resolutions") or [])[:10],
                }
    except Exception:
        pass
    return None


async def _abuseipdb_check_async(session: aiohttp.ClientSession, ip: str, api_key: str) -> Optional[Dict[str, Any]]:
    """Query AbuseIPDB for IP reputation (spam, DDoS, etc.) — 1000 checks/day."""
    if not api_key:
        return None
    try:
        url = "https://api.abuseipdb.com/api/v2/check"
        params = {"ipAddress": ip, "maxAgeInDays": 90}
        headers = {"User-Agent": USER_AGENT, "Key": api_key, "Accept": "application/json"}
        async with session.get(url, params=params, headers=headers, timeout=aiohttp.ClientTimeout(total=HTTP_TIMEOUT)) as resp:
            if resp.status == 200:
                data = await resp.json()
                d = data.get("data") or {}
                return {
                    "ip": ip,
                    "abuse_score": d.get("abuseConfidenceScore"),
                    "total_reports": d.get("totalReports"),
                    "num_users": d.get("numDistinctUsers"),
                    "isp": d.get("isp"),
                    "country_code": d.get("countryCode"),
                    "usage_type": d.get("usageType"),
                }
            if resp.status == 429:
                await asyncio.sleep(5)
    except Exception:
        pass
    return None


async def _securitytrails_domain_async(session: aiohttp.ClientSession, domain: str, api_key: str) -> Optional[Dict[str, Any]]:
    """Query SecurityTrails for domain info (WHOIS, tags, etc.) — optional enrichment."""
    if not api_key:
        return None
    try:
        url = f"https://api.securitytrails.com/v1/domain/{domain}"
        headers = {"User-Agent": USER_AGENT, "apikey": api_key}
        async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=HTTP_TIMEOUT)) as resp:
            if resp.status == 200:
                data = await resp.json()
                return {
                    "domain": domain,
                    "subdomain_count": data.get("subdomain_count"),
                    "current_dns": data.get("current_dns"),
                    "tags": data.get("tags") or [],
                }
    except Exception:
        pass
    return None


async def _phishtank_check_async(session: aiohttp.ClientSession, url: str, app_key: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Check URL against PhishTank phishing database (free, app_key optional — registration disabled)."""
    try:
        post_url = "https://checkurl.phishtank.com/checkurl/"
        data = {"url": url, "format": "json"}
        if app_key and app_key != "your_ke":  # skip placeholder keys
            data["app_key"] = app_key
        headers = {"User-Agent": USER_AGENT, "Content-Type": "application/x-www-form-urlencoded"}
        async with session.post(post_url, data=data, headers=headers, timeout=aiohttp.ClientTimeout(total=HTTP_TIMEOUT)) as resp:
            if resp.status == 200:
                result = await resp.json()
                return {
                    "url": url,
                    "in_database": result.get("results", {}).get("in_database", False),
                    "valid": result.get("results", {}).get("valid"),
                    "verified": result.get("results", {}).get("verified"),
                    "phish_id": result.get("results", {}).get("phish_id"),
                    "phish_detail_page": result.get("results", {}).get("phish_detail_page"),
                }
            body = await resp.text()
            hint = "Cloudflare block" if resp.status == 403 and "cf_chl" in body[:500] else (body[:150] + "..." if len(body) > 150 else body)
            logger.warning("PhishTank API error: url=%s status=%s (%s)", url, resp.status, hint)
    except Exception as e:
        logger.warning("PhishTank request failed: url=%s error=%s", url, e)
    return None


async def _zoomeye_search_async(session: aiohttp.ClientSession, domain: str, api_key: str) -> Optional[Dict[str, Any]]:
    """Search ZoomEye for domain (host search) — ~10k points/month, SSL JARM, ASN."""
    if not api_key:
        return None
    try:
        query = f"domain:{domain}"
        url = "https://api.zoomeye.org/host/search"
        params = {"query": query, "page": 1, "facets": "app,os,country"}
        headers = {"User-Agent": USER_AGENT, "API-KEY": api_key}
        async with session.get(url, params=params, headers=headers, timeout=aiohttp.ClientTimeout(total=HTTP_TIMEOUT)) as resp:
            if resp.status == 200:
                data = await resp.json()
                total = data.get("total", 0)
                matches = data.get("matches", [])[:10]
                hosts = []
                for m in matches:
                    geoinfo = m.get("geoinfo") or {}
                    portinfo = m.get("portinfo") or {}
                    country_obj = geoinfo.get("country") if isinstance(geoinfo, dict) else {}
                    country = country_obj.get("names", {}).get("en") if isinstance(country_obj, dict) else None
                    hosts.append({
                        "ip": m.get("ip"),
                        "port": portinfo.get("port") if isinstance(portinfo, dict) else None,
                        "country": country,
                        "asn": str(geoinfo.get("asn")) if geoinfo.get("asn") is not None else None,
                        "app": portinfo.get("app") if isinstance(portinfo, dict) else None,
                    })
                return {"domain": domain, "total": total, "hosts": hosts}
    except Exception:
        pass
    return None


async def _criminalip_domain_async(session: aiohttp.ClientSession, domain: str, api_key: str) -> Optional[Dict[str, Any]]:
    """Query Criminal IP domain quick view — https://search.criminalip.io/developer/api/"""
    if not api_key:
        return None
    try:
        url = "https://api.criminalip.io/v1/domain/quick/malicious/view"
        params = {"domain": domain}
        headers = {"User-Agent": USER_AGENT, "x-api-key": api_key}
        async with session.get(url, params=params, headers=headers, timeout=aiohttp.ClientTimeout(total=HTTP_TIMEOUT)) as resp:
            body = await resp.text()
            if resp.status == 200:
                import json
                data = json.loads(body) if body else {}
                return {
                    "domain": domain,
                    "risk_score": data.get("risk_score"),
                    "is_safe": data.get("is_safe"),
                    "data": data,
                }
            logger.warning("Criminal IP API error: domain=%s status=%s body=%s", domain, resp.status, body[:200] if body else "")
    except Exception as e:
        logger.warning("Criminal IP request failed: domain=%s error=%s", domain, e)
    return None


async def _pulsedive_info_async(session: aiohttp.ClientSession, domain: str, api_key: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Query Pulsedive for domain threat intel — 50/day, 500/month."""
    try:
        url = "https://pulsedive.com/api/info.php"
        params = {"indicator": domain, "pretty": "1"}
        if api_key:
            params["key"] = api_key
        headers = {"User-Agent": USER_AGENT}
        async with session.get(url, params=params, headers=headers, timeout=aiohttp.ClientTimeout(total=HTTP_TIMEOUT)) as resp:
            body = await resp.text()
            if resp.status == 200:
                data = json.loads(body) if body else {}
                result = {
                    "domain": domain,
                    "risk": data.get("risk"),
                    "risk_recommendation": data.get("risk_recommendation"),
                    "threats": data.get("threats", [])[:5],
                    "feeds": data.get("feeds", [])[:5],
                    "properties": data.get("properties", {}),
                }
                logger.info("Pulsedive: domain=%s risk=%s threats=%s", domain, result.get("risk"), len(result.get("threats") or []))
                return result
            if resp.status == 404 and "Indicator not found" in (body or ""):
                logger.info("Pulsedive: domain=%s not in threat database (clean)", domain)
                return {"domain": domain, "risk": "none", "risk_recommendation": "Domain not in threat database", "threats": [], "feeds": []}
            logger.warning("Pulsedive API error: domain=%s status=%s body=%s", domain, resp.status, body[:200] if body else "")
    except Exception as e:
        logger.warning("Pulsedive request failed: domain=%s error=%s", domain, e)
    return None


async def _bgpview_ip_async(session: aiohttp.ClientSession, ip: str) -> Optional[Dict[str, Any]]:
    """Query BGPView for IP/ASN info (free, no API key)."""
    try:
        url = f"https://api.bgpview.io/ip/{ip}"
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=HTTP_TIMEOUT)) as resp:
            if resp.status == 200:
                data = await resp.json()
                d = data.get("data") if isinstance(data.get("data"), dict) else data
                rir = d.get("rir_allocation") if isinstance(d.get("rir_allocation"), dict) else {}
                return {
                    "ip": ip,
                    "asn": d.get("asn"),
                    "asn_name": rir.get("name") or d.get("name"),
                    "prefix": d.get("prefix"),
                }
    except Exception:
        pass
    return None


async def _alienvault_otx_domain_async(session: aiohttp.ClientSession, domain: str) -> Optional[Dict[str, Any]]:
    """Query AlienVault OTX for domain indicators (free API key required)."""
    if not ALIENVAULT_OTX_API_KEY:
        return None
    try:
        url = f"https://otx.alienvault.com/api/v1/indicators/domain/{domain}/general"
        headers = {"User-Agent": USER_AGENT, "X-OTX-API-KEY": ALIENVAULT_OTX_API_KEY}
        async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=HTTP_TIMEOUT)) as resp:
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
    except Exception:
        pass
    return None


async def _virustotal_domain_async(session: aiohttp.ClientSession, domain: str) -> Optional[Dict[str, Any]]:
    """Query VirusTotal domain API for reputation. Uses cache and rate limiting."""
    if not VIRUSTOTAL_API_KEY:
        return None
    try:
        from src.services.cache_service import get, set, TTL_VIRUSTOTAL
        from src.services.rate_limit_service import acquire

        cache_key = f"vt:domain:{domain}"
        cached = get(cache_key)
        if cached is not None:
            return cached

        if not acquire("virustotal", max_requests=4, window_seconds=60):
            logger.warning("VirusTotal rate limited, skipping")
            return None

        from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

        class RateLimitedError(Exception):
            pass

        @retry(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=4, max=60),
            retry=retry_if_exception_type(RateLimitedError),
            reraise=True,
        )
        async def _fetch():
            url = f"https://www.virustotal.com/api/v3/domains/{domain}"
            headers = {"User-Agent": USER_AGENT, "x-apikey": VIRUSTOTAL_API_KEY}
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=HTTP_TIMEOUT)) as resp:
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
    except Exception:
        pass
    return None


def fetch_single_external_api(
    api_name: str,
    domain: Optional[str] = None,
    ip: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Fetch a single external API by name. Used by investigations.
    Returns the raw API response or None.
    """
    headers = {"User-Agent": USER_AGENT}

    async def _run() -> Optional[Dict[str, Any]]:
        async with _make_aiohttp_session(headers) as session:
            if api_name == "virustotal" and domain:
                return await _virustotal_domain_async(session, domain)
            if api_name == "alienvault_otx" and domain:
                return await _alienvault_otx_domain_async(session, domain)
            if api_name == "urlscan" and domain:
                return await _urlscan_search_async(session, domain)
            if api_name == "threatcrowd" and domain:
                return await _threatcrowd_domain_async(session, domain)
            if api_name == "bgpview" and ip:
                return await _bgpview_ip_async(session, ip)
            if api_name == "abuseipdb" and ip:
                return await _abuseipdb_check_async(session, ip, ABUSEIPDB_API_KEY or "")
        return None

    return asyncio.run(_run())


def _make_aiohttp_session(headers: dict) -> aiohttp.ClientSession:
    """Create aiohttp session with ThreadedResolver (avoids aiodns DNS issues on some systems)."""
    connector = aiohttp.TCPConnector(resolver=aiohttp.resolver.ThreadedResolver())
    return aiohttp.ClientSession(headers=headers, connector=connector)


async def _fetch_external_apis_async(domain: str, ips: List[str]) -> Dict[str, Any]:
    """Fetch all external APIs in parallel using aiohttp."""
    result: Dict[str, Any] = {}
    headers = {"User-Agent": USER_AGENT}

    async with _make_aiohttp_session(headers) as session:
        tasks: List[Any] = []
        task_keys: List[str] = []

        if VIRUSTOTAL_API_KEY:
            tasks.append(_virustotal_domain_async(session, domain))
            task_keys.append("virustotal")
        if ALIENVAULT_OTX_API_KEY:
            tasks.append(_alienvault_otx_domain_async(session, domain))
            task_keys.append("alienvault_otx")
        if SECURITYTRAILS_API_KEY:
            tasks.append(_securitytrails_domain_async(session, domain, SECURITYTRAILS_API_KEY))
            task_keys.append("securitytrails")
        tasks.append(_urlscan_search_async(session, domain))
        task_keys.append("urlscan")
        tasks.append(_threatcrowd_domain_async(session, domain))
        task_keys.append("threatcrowd")
        tasks.append(_wayback_first_snapshot_async(session, domain))
        task_keys.append("wayback")
        tasks.append(_ssllabs_analyze_async(session, domain))
        task_keys.append("ssllabs")
        tasks.append(_phishtank_check_async(session, f"https://{domain}", PHISHTANK_APP_KEY))
        task_keys.append("phishtank")
        if ZOOMEYE_API_KEY:
            tasks.append(_zoomeye_search_async(session, domain, ZOOMEYE_API_KEY))
            task_keys.append("zoomeye")
        if CRIMINALIP_API_KEY:
            tasks.append(_criminalip_domain_async(session, domain, CRIMINALIP_API_KEY))
            task_keys.append("criminalip")
        tasks.append(_pulsedive_info_async(session, domain, PULSEDIVE_API_KEY))
        task_keys.append("pulsedive")
        for ip in ips:
            tasks.append(_bgpview_ip_async(session, ip))
            task_keys.append("bgpview")
        if ABUSEIPDB_API_KEY:
            for ip in ips:
                tasks.append(_abuseipdb_check_async(session, ip, ABUSEIPDB_API_KEY))
                task_keys.append("abuseipdb")

        if not tasks:
            return {}

        results = await asyncio.gather(*tasks, return_exceptions=True)
        bgp_data: Dict[str, Any] = {}
        abuseipdb_data: Dict[str, Any] = {}

        for key, data in zip(task_keys, results):
            if isinstance(data, Exception) or data is None:
                continue
            if key == "bgpview":
                bgp_data[data["ip"]] = data
            elif key == "abuseipdb":
                abuseipdb_data[data["ip"]] = data
            elif key == "virustotal":
                result["virustotal"] = {
                    "last_analysis_stats": data.get("data", {}).get("attributes", {}).get("last_analysis_stats"),
                    "reputation": data.get("data", {}).get("attributes", {}).get("reputation"),
                }
            elif key == "alienvault_otx":
                result["alienvault_otx"] = data
            elif key == "securitytrails":
                result["securitytrails"] = data
            elif key == "urlscan":
                result["urlscan"] = data
            elif key == "threatcrowd":
                result["threatcrowd"] = data
            elif key == "phishtank":
                result["phishtank"] = data
            elif key == "zoomeye":
                result["zoomeye"] = data
            elif key == "criminalip":
                result["criminalip"] = data
            elif key == "pulsedive":
                result["pulsedive"] = data
            elif key == "wayback":
                result["wayback"] = data
            elif key == "ssllabs":
                result["ssllabs"] = data

        if bgp_data:
            result["bgpview"] = {"ips": bgp_data}
        if abuseipdb_data:
            result["abuseipdb"] = {"ips": abuseipdb_data}

    return result


class ExternalApiEnricher(AbstractEnricher):
    """Enricher for Shodan, VirusTotal, Censys, AlienVault OTX, URLScan, BGPView, ThreatCrowd."""

    name = "external_apis"

    def enrich(self, domain: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        ips: List[str] = []
        seen: Set[str] = set()
        if context:
            dns = context.get("dns_info")
            if isinstance(dns, dict):
                for ip in (dns.get("a_records") or []) + (dns.get("aaaa_records") or []):
                    if ip and ip not in seen:
                        ips.append(ip)
                        seen.add(ip)
            elif dns and hasattr(dns, "a_records"):
                for ip in (getattr(dns, "a_records") or []) + (getattr(dns, "aaaa_records") or []):
                    if ip and ip not in seen:
                        ips.append(ip)
                        seen.add(ip)
            port_scan = context.get("port_scan") or []
            for entry in port_scan:
                if isinstance(entry, dict) and entry.get("ip") and entry["ip"] not in seen:
                    ips.append(entry["ip"])
                    seen.add(entry["ip"])
        ips = ips[:15]

        result = asyncio.run(_fetch_external_apis_async(domain, ips))
        return {"external_apis": result} if result else {}
