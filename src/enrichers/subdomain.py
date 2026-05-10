"""
Subdomain Enricher - discovers subdomains via passive (crt.sh, Crobat, etc.)
and active (DNS brute-force) methods. Uses aiohttp for parallel HTTP fetches.
"""

import asyncio
import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set

import aiohttp

from src.config.settings import (
    CERTSPOTTER_API_TOKEN,
    CRTSH_TIMEOUT,
    HTTP_RETRIES,
    HTTP_TIMEOUT,
    SECURITYTRAILS_API_KEY,
    USER_AGENT,
)
from src.enrichers._http import make_aiohttp_session
from src.enrichers.base import AbstractEnricher
from src.utils.validators import is_valid_domain

logger = logging.getLogger(__name__)

_CRTSH_RETRYABLE_STATUS = {429, 500, 502, 503, 504}
_BRUTE_FORCE_WORDLIST_SIZE = 500
_BRUTE_FORCE_CONCURRENCY = 50
_DEFAULT_FALLBACK_WORDLIST = (
    "www mail ftp admin api dev test staging blog shop cdn static assets app web"
).split()


def _normalize_subdomain_canonical(hostname: str) -> str:
    """
    Canonical form for subdomain deduplication.
    Drops redundant 'www' labels (e.g. www.events.www.example.com -> events.example.com).
    """
    if not hostname:
        return ""
    parts = hostname.lower().strip().rstrip(".").split(".")
    canonical = [p for p in parts if p and p != "www"]
    return ".".join(canonical) if canonical else ""


def _extract_subdomains_from_crt(domain: str, data: Iterable[dict]) -> Set[str]:
    subdomains: Set[str] = set()
    domain = domain.lower().strip()
    suffix = f".{domain}"

    for entry in data:
        name_value = entry.get("name_value", "")
        for raw in str(name_value).replace("\n", ",").split(","):
            cleaned = raw.strip().lower().rstrip(".")
            if not cleaned:
                continue
            if cleaned.startswith("*."):
                cleaned = cleaned[2:]
            if " " in cleaned or "@" in cleaned:
                continue
            if not cleaned.endswith(suffix):
                continue
            if is_valid_domain(cleaned):
                subdomains.add(cleaned)

    subdomains.discard(domain)
    return subdomains


async def _fetch_crtsh_json_async(
    session: aiohttp.ClientSession, url: str, timeout: int, retries: int
) -> Optional[list]:
    """GET `url` and parse JSON, with backoff on transient failures."""
    last_error: Optional[str] = None
    effective_timeout = aiohttp.ClientTimeout(total=timeout or CRTSH_TIMEOUT)

    for attempt in range(1, retries + 1):
        try:
            async with session.get(url, timeout=effective_timeout) as resp:
                if resp.status == 200:
                    try:
                        return await resp.json()
                    except (json.JSONDecodeError, aiohttp.ContentTypeError):
                        last_error = "Invalid JSON response from crt.sh"
                elif resp.status in _CRTSH_RETRYABLE_STATUS:
                    last_error = f"crt.sh HTTP {resp.status}"
                else:
                    return None
        except asyncio.TimeoutError:
            last_error = "crt.sh request timed out"
        except aiohttp.ClientError as exc:
            last_error = str(exc)

        if attempt < retries:
            await asyncio.sleep(min(1.0 * (2 ** (attempt - 1)), 8.0))

    if last_error:
        logger.debug("crt.sh failed: %s", last_error)
    return None


async def _fetch_crobat_async(session: aiohttp.ClientSession, domain: str) -> Set[str]:
    """Fetch subdomains from Crobat API (sonar.omnisint.io)."""
    subdomains: Set[str] = set()
    url = f"https://sonar.omnisint.io/subdomains/{domain}"
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=HTTP_TIMEOUT)) as resp:
            if resp.status == 200:
                data = await resp.json()
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, str) and is_valid_domain(item):
                            subdomains.add(item.lower())
    except Exception as exc:
        logger.debug("Crobat fetch failed for %s: %s", domain, exc)
    return subdomains


async def _fetch_anubis_async(session: aiohttp.ClientSession, domain: str) -> Set[str]:
    """Fetch subdomains from Anubis API (jonlu.ca) - 2000 req/15 min, no auth."""
    subdomains: Set[str] = set()
    url = f"https://jonlu.ca/anubis/subdomains/{domain}"
    suffix = f".{domain}"
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=HTTP_TIMEOUT)) as resp:
            if resp.status != 200:
                return subdomains
            data = await resp.json()
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, str) and is_valid_domain(item) and item.lower().endswith(suffix):
                        subdomains.add(item.lower())
            elif isinstance(data, dict):
                subs = data.get("subdomains") or data.get("subdomain") or data.get("results") or []
                for item in subs:
                    candidate = item if isinstance(item, str) else (item.get("name") or item.get("domain") or "")
                    if candidate and is_valid_domain(candidate) and candidate.lower().endswith(suffix):
                        subdomains.add(candidate.lower())
    except Exception as exc:
        logger.debug("Anubis fetch failed for %s: %s", domain, exc)
    return subdomains


async def _fetch_certspotter_async(
    session: aiohttp.ClientSession, domain: str, token: Optional[str] = None
) -> Set[str]:
    """Fetch subdomains from CertSpotter CT API (100 req/host/h, stable alternative to crt.sh)."""
    subdomains: Set[str] = set()
    url = "https://api.certspotter.com/v1/issuances"
    params = {"domain": domain, "expand": "dns_names"}
    headers = {"User-Agent": USER_AGENT}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        async with session.get(
            url, params=params, headers=headers, timeout=aiohttp.ClientTimeout(total=HTTP_TIMEOUT)
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                if isinstance(data, list):
                    for entry in data:
                        for name in entry.get("dns_names") or []:
                            cleaned = str(name).strip().lower().lstrip("*.").lstrip(".")
                            if cleaned and is_valid_domain(cleaned) and (cleaned == domain or cleaned.endswith(f".{domain}")):
                                subdomains.add(cleaned)
            elif resp.status == 429:
                retry = resp.headers.get("Retry-After")
                if retry and retry.isdigit():
                    await asyncio.sleep(min(int(retry), 60))
    except Exception as exc:
        logger.debug("CertSpotter fetch failed for %s: %s", domain, exc)
    return subdomains


async def _fetch_securitytrails_async(
    session: aiohttp.ClientSession, domain: str, api_key: str
) -> Set[str]:
    """Fetch subdomains from SecurityTrails API (50/mo free, 2500/mo OSINT Toolkit)."""
    if not api_key:
        return set()
    subdomains: Set[str] = set()
    url = f"https://api.securitytrails.com/v1/domain/{domain}/subdomains"
    headers = {"User-Agent": USER_AGENT, "apikey": api_key}
    try:
        async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=HTTP_TIMEOUT)) as resp:
            if resp.status == 200:
                data = await resp.json()
                for sub in data.get("subdomains") or []:
                    if isinstance(sub, str) and sub:
                        full = f"{sub}.{domain}".lower()
                        if is_valid_domain(full):
                            subdomains.add(full)
    except Exception as exc:
        logger.debug("SecurityTrails fetch failed for %s: %s", domain, exc)
    return subdomains


async def _fetch_hackertarget_async(session: aiohttp.ClientSession, domain: str) -> Set[str]:
    """Fetch subdomains from HackerTarget hostsearch API (CSV: hostname,ip)."""
    subdomains: Set[str] = set()
    url = f"https://api.hackertarget.com/hostsearch/?q={domain}"
    suffix = f".{domain}"
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=HTTP_TIMEOUT)) as resp:
            if resp.status != 200:
                return subdomains
            text = (await resp.text()).strip()
            for line in text.splitlines():
                if "," in line:
                    hostname = line.split(",", 1)[0].strip().lower()
                    if hostname and is_valid_domain(hostname) and hostname.endswith(suffix):
                        subdomains.add(hostname)
                elif line and is_valid_domain(line):
                    subdomains.add(line.lower())
    except Exception as exc:
        logger.debug("HackerTarget fetch failed for %s: %s", domain, exc)
    return subdomains


async def _fetch_crtsh_async(session: aiohttp.ClientSession, domain: str) -> Set[str]:
    """Fetch subdomains from crt.sh (both URL patterns in parallel). Cached."""
    cache_key = f"crtsh:{domain}"
    cached = _cache_get_list(cache_key)
    if cached is not None:
        return set(cached)

    subdomains: Set[str] = set()
    urls = [
        f"https://crt.sh/?q=%25.{domain}&output=json",
        f"https://crt.sh/?q={domain}&output=json",
    ]
    tasks = [_fetch_crtsh_json_async(session, url, CRTSH_TIMEOUT, HTTP_RETRIES) for url in urls]
    for data in await asyncio.gather(*tasks, return_exceptions=True):
        if isinstance(data, list):
            subdomains |= _extract_subdomains_from_crt(domain, data)

    _cache_set_list(cache_key, sorted(subdomains))
    return subdomains


def _cache_get_list(key: str) -> Optional[list]:
    try:
        from src.services.cache_service import get  # local import: cache is optional

        cached = get(key)
        if isinstance(cached, list):
            return cached
    except Exception as exc:
        logger.debug("crt.sh cache read failed: %s", exc)
    return None


def _cache_set_list(key: str, value: list) -> None:
    try:
        from src.services.cache_service import TTL_CRTSH, set as cache_set

        cache_set(key, value, TTL_CRTSH)
    except Exception as exc:
        logger.debug("crt.sh cache write failed: %s", exc)


def _fetch_dnsdumpster(domain: str) -> Set[str]:
    """Fetch subdomains from DNSDumpster (sync; uses requests internally)."""
    subdomains: Set[str] = set()
    suffix = f".{domain}"
    try:
        from dnsdumpster.DNSDumpsterAPI import DNSDumpsterAPI  # local: optional dep

        results = DNSDumpsterAPI().search(domain)
        if results and isinstance(results, dict):
            dns_rec = results.get("dns_records") or {}
            for rec in dns_rec.get("dns", []) or []:
                host = (rec.get("host") or rec.get("domain") or "").strip().rstrip(".").lower()
                if host and is_valid_domain(host) and (host == domain or host.endswith(suffix)):
                    subdomains.add(host)
            for rec in dns_rec.get("mx", []) or []:
                host = (rec.get("domain") or rec.get("host") or "").strip().rstrip(".").lower()
                if host and is_valid_domain(host) and host.endswith(suffix):
                    subdomains.add(host)
        subdomains.discard(domain.lower())
    except Exception as exc:
        logger.debug("DNSDumpster fetch failed for %s: %s", domain, exc)
    return subdomains


def _load_wordlist() -> List[str]:
    """Load subdomain wordlist for brute-force, with a built-in fallback."""
    paths = [
        Path("data/wordlists/subdomains-small.txt"),
        Path("data/wordlists/subdomains-top1mil.txt"),
    ]
    for path in paths:
        if path.exists():
            try:
                return [
                    line.strip()
                    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines()
                    if line.strip()
                ]
            except OSError as exc:
                logger.debug("Wordlist read failed %s: %s", path, exc)
    return list(_DEFAULT_FALLBACK_WORDLIST)


async def _fetch_passive_async(domain: str) -> Set[str]:
    """Run all passive sources in parallel (crt.sh, Crobat, HackerTarget, Anubis, CertSpotter, SecurityTrails)."""
    all_subs: Set[str] = set()
    headers = {"User-Agent": USER_AGENT}

    async with make_aiohttp_session(headers) as session:
        tasks = [
            _fetch_crtsh_async(session, domain),
            _fetch_crobat_async(session, domain),
            _fetch_hackertarget_async(session, domain),
            _fetch_anubis_async(session, domain),
            _fetch_certspotter_async(session, domain, CERTSPOTTER_API_TOKEN or None),
        ]
        if SECURITYTRAILS_API_KEY:
            tasks.append(_fetch_securitytrails_async(session, domain, SECURITYTRAILS_API_KEY))
        for result in await asyncio.gather(*tasks, return_exceptions=True):
            if isinstance(result, set):
                all_subs |= result
    return all_subs


class SubdomainEnricher(AbstractEnricher):
    """Enricher for subdomain discovery (passive + optional brute-force)."""

    name = "subdomain"

    def __init__(self, enable_bruteforce: bool = False):
        self.enable_bruteforce = enable_bruteforce

    def _active_bruteforce(self, domain: str) -> Set[str]:
        """Active DNS brute-force (async via aiodns when available, else sync)."""
        if not self.enable_bruteforce:
            return set()

        wordlist = _load_wordlist()[:_BRUTE_FORCE_WORDLIST_SIZE]
        if not wordlist:
            return set()

        try:
            return self._bruteforce_async(domain, wordlist)
        except ImportError:
            return self._bruteforce_sync(domain, wordlist)

    @staticmethod
    def _bruteforce_async(domain: str, wordlist: List[str]) -> Set[str]:
        import aiodns  # local import: optional dep

        resolver = aiodns.DNSResolver()

        async def _resolve_one(candidate: str) -> Optional[str]:
            try:
                await resolver.query(candidate, "A")
                return candidate
            except Exception:
                return None

        async def _run() -> Set[str]:
            sem = asyncio.Semaphore(_BRUTE_FORCE_CONCURRENCY)

            async def _limited(candidate: str) -> Optional[str]:
                async with sem:
                    return await _resolve_one(candidate)

            tasks = [_limited(f"{sub}.{domain}") for sub in wordlist]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            return {r for r in results if isinstance(r, str)}

        return asyncio.run(_run())

    @staticmethod
    def _bruteforce_sync(domain: str, wordlist: List[str]) -> Set[str]:
        import dns.resolver  # local import (heavy module already loaded elsewhere)

        found: Set[str] = set()
        for sub in wordlist:
            candidate = f"{sub}.{domain}"
            try:
                dns.resolver.resolve(candidate, "A")
                found.add(candidate)
            except Exception:
                continue
        return found

    def enrich(self, domain: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        domain = domain.lower().strip()
        all_subs: Set[str] = set()

        with ThreadPoolExecutor(max_workers=2) as executor:
            async_future = executor.submit(asyncio.run, _fetch_passive_async(domain))
            dnsdumpster_future = executor.submit(_fetch_dnsdumpster, domain)
            for future in as_completed((async_future, dnsdumpster_future)):
                try:
                    all_subs |= future.result(timeout=CRTSH_TIMEOUT + 15)
                except Exception as exc:
                    logger.debug("Passive subdomain task failed: %s", exc)

        all_subs |= self._active_bruteforce(domain)

        # Deduplicate by canonical form so e.g. www.events.example.com -> events.example.com.
        seen_canonical: Set[str] = set()
        deduped: Set[str] = set()
        root_canonical = _normalize_subdomain_canonical(domain)
        for sub in all_subs:
            canon = _normalize_subdomain_canonical(sub)
            if not canon or canon == root_canonical:
                continue
            if canon not in seen_canonical:
                seen_canonical.add(canon)
                deduped.add(canon)

        return {"subdomains": sorted(deduped)}
