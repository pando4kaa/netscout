"""
Subdomain Enricher — discovers subdomains via passive (crt.sh, Crobat) and active methods.
Uses aiohttp for async HTTP requests.
"""

import asyncio
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set

import aiohttp

from src.config.settings import (
    HTTP_TIMEOUT,
    HTTP_RETRIES,
    CRTSH_TIMEOUT,
    USER_AGENT,
    CERTSPOTTER_API_TOKEN,
    SECURITYTRAILS_API_KEY,
)
from src.utils.validators import is_valid_domain
from src.enrichers.base import AbstractEnricher


def _normalize_subdomain_canonical(hostname: str) -> str:
    """
    Canonical form for subdomain deduplication.
    Removes redundant 'www' labels: www.events.www.example.com -> events.example.com.
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
        for name in str(name_value).replace("\n", ",").split(","):
            name = name.strip().lower()
            if not name:
                continue
            if name.endswith("."):
                name = name[:-1]
            if name.startswith("*."):
                name = name[2:]
            if " " in name or "@" in name:
                continue
            if not name.endswith(suffix):
                continue
            if is_valid_domain(name):
                subdomains.add(name)

    subdomains.discard(domain.lower())
    return subdomains


async def _fetch_crtsh_json_async(
    session: aiohttp.ClientSession, url: str, timeout: int, retries: int
) -> Optional[list]:
    """Fetch JSON from crt.sh with retries/backoff."""
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json,text/plain,*/*"}
    last_error: Optional[str] = None

    for attempt in range(1, retries + 1):
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout or CRTSH_TIMEOUT)) as resp:
                if resp.status in (429, 500, 502, 503, 504):
                    last_error = f"crt.sh HTTP {resp.status}"
                elif resp.status != 200:
                    return None
                else:
                    try:
                        return await resp.json()
                    except (json.JSONDecodeError, aiohttp.ContentTypeError):
                        last_error = "Invalid JSON response from crt.sh"
        except asyncio.TimeoutError:
            last_error = "crt.sh request timed out"
        except aiohttp.ClientError as e:
            last_error = str(e)

        if attempt < retries:
            await asyncio.sleep(min(1.0 * (2 ** (attempt - 1)), 8.0))

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
    except Exception:
        pass
    return subdomains


async def _fetch_anubis_async(session: aiohttp.ClientSession, domain: str) -> Set[str]:
    """Fetch subdomains from Anubis API (jonlu.ca) — 2000 req/15 min, no auth."""
    subdomains: Set[str] = set()
    try:
        url = f"https://jonlu.ca/anubis/subdomains/{domain}"
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=HTTP_TIMEOUT)) as resp:
            if resp.status == 200:
                data = await resp.json()
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, str) and is_valid_domain(item) and item.lower().endswith(f".{domain}"):
                            subdomains.add(item.lower())
                elif isinstance(data, dict):
                    subs = data.get("subdomains") or data.get("subdomain") or data.get("results") or []
                    for item in subs:
                        s = item if isinstance(item, str) else (item.get("name") or item.get("domain") or "")
                        if s and is_valid_domain(s) and s.lower().endswith(f".{domain}"):
                            subdomains.add(s.lower())
    except Exception:
        pass
    return subdomains


async def _fetch_certspotter_async(session: aiohttp.ClientSession, domain: str, token: Optional[str] = None) -> Set[str]:
    """Fetch subdomains from CertSpotter CT API — 100 req/host/h, stable alternative to crt.sh."""
    subdomains: Set[str] = set()
    try:
        url = f"https://api.certspotter.com/v1/issuances"
        params = {"domain": domain, "expand": "dns_names"}
        headers = {"User-Agent": USER_AGENT}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        async with session.get(url, params=params, headers=headers, timeout=aiohttp.ClientTimeout(total=HTTP_TIMEOUT)) as resp:
            if resp.status == 200:
                data = await resp.json()
                if isinstance(data, list):
                    for entry in data:
                        names = entry.get("dns_names") or []
                        for name in names:
                            name = str(name).strip().lower()
                            if name.startswith("*."):
                                name = name[2:]
                            if name and is_valid_domain(name) and (name == domain or name.endswith(f".{domain}")):
                                subdomains.add(name)
            elif resp.status == 429:
                retry = resp.headers.get("Retry-After")
                if retry:
                    await asyncio.sleep(min(int(retry), 60))
    except Exception:
        pass
    return subdomains


async def _fetch_securitytrails_async(session: aiohttp.ClientSession, domain: str, api_key: str) -> Set[str]:
    """Fetch subdomains from SecurityTrails API — 50/mo (2500 for OSINT Toolkit)."""
    if not api_key:
        return set()
    subdomains: Set[str] = set()
    try:
        url = f"https://api.securitytrails.com/v1/domain/{domain}/subdomains"
        headers = {"User-Agent": USER_AGENT, "apikey": api_key}
        async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=HTTP_TIMEOUT)) as resp:
            if resp.status == 200:
                data = await resp.json()
                subs = data.get("subdomains") or []
                for sub in subs:
                    if isinstance(sub, str) and sub:
                        full = f"{sub}.{domain}".lower()
                        if is_valid_domain(full):
                            subdomains.add(full)
    except Exception:
        pass
    return subdomains


async def _fetch_hackertarget_async(session: aiohttp.ClientSession, domain: str) -> Set[str]:
    """Fetch subdomains from HackerTarget hostsearch API (CSV: hostname,ip)."""
    subdomains: Set[str] = set()
    url = f"https://api.hackertarget.com/hostsearch/?q={domain}"
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=HTTP_TIMEOUT)) as resp:
            if resp.status == 200:
                text = await resp.text()
                if text:
                    for line in text.strip().splitlines():
                        if "," in line:
                            hostname = line.split(",")[0].strip().lower()
                            if hostname and is_valid_domain(hostname) and hostname.endswith(f".{domain}"):
                                subdomains.add(hostname)
                        elif line.strip() and is_valid_domain(line.strip()):
                            subdomains.add(line.strip().lower())
    except Exception:
        pass
    return subdomains


async def _fetch_crtsh_async(session: aiohttp.ClientSession, domain: str) -> Set[str]:
    """Fetch subdomains from crt.sh (both URL patterns in parallel). Uses cache."""
    try:
        from src.services.cache_service import get, set, TTL_CRTSH

        cache_key = f"crtsh:{domain}"
        cached = get(cache_key)
        if cached is not None and isinstance(cached, list):
            return set(cached)
    except Exception:
        pass

    subdomains: Set[str] = set()
    urls = [
        f"https://crt.sh/?q=%25.{domain}&output=json",
        f"https://crt.sh/?q={domain}&output=json",
    ]
    tasks = [_fetch_crtsh_json_async(session, url, CRTSH_TIMEOUT, HTTP_RETRIES) for url in urls]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    for data in results:
        if isinstance(data, list):
            subdomains |= _extract_subdomains_from_crt(domain, data)

    try:
        from src.services.cache_service import set, TTL_CRTSH

        set(f"crtsh:{domain}", list(subdomains), TTL_CRTSH)
    except Exception:
        pass

    return subdomains


def _fetch_dnsdumpster(domain: str) -> Set[str]:
    """Fetch subdomains from DNSDumpster via dnsdumpster package (sync, uses requests internally)."""
    subdomains: Set[str] = set()
    try:
        from dnsdumpster.DNSDumpsterAPI import DNSDumpsterAPI
        api = DNSDumpsterAPI()
        results = api.search(domain)
        if results and isinstance(results, dict):
            dns_rec = results.get("dns_records") or {}
            for rec in dns_rec.get("dns", []) or []:
                host = (rec.get("host") or rec.get("domain") or "").strip().rstrip(".").lower()
                if host and is_valid_domain(host) and (host == domain or host.endswith(f".{domain}")):
                    subdomains.add(host)
            for rec in dns_rec.get("mx", []) or []:
                host = (rec.get("domain") or rec.get("host") or "").strip().rstrip(".").lower()
                if host and is_valid_domain(host) and host.endswith(f".{domain}"):
                    subdomains.add(host)
        subdomains.discard(domain.lower())
    except Exception:
        pass
    return subdomains


def _load_wordlist() -> List[str]:
    """Load subdomain wordlist for brute-force."""
    paths = [
        Path("data/wordlists/subdomains-small.txt"),
        Path("data/wordlists/subdomains-top1mil.txt"),
    ]
    for p in paths:
        if p.exists():
            try:
                return [line.strip() for line in p.read_text(encoding="utf-8", errors="ignore").splitlines() if line.strip()]
            except Exception:
                pass
    return ["www", "mail", "ftp", "admin", "api", "dev", "test", "staging", "blog", "shop", "cdn", "static", "assets", "app", "web"]


def _make_aiohttp_session(headers: dict) -> aiohttp.ClientSession:
    """Create aiohttp session with ThreadedResolver (avoids aiodns DNS issues on some systems)."""
    connector = aiohttp.TCPConnector(resolver=aiohttp.resolver.ThreadedResolver())
    return aiohttp.ClientSession(headers=headers, connector=connector)


async def _fetch_passive_async(domain: str) -> Set[str]:
    """Fetch from crt.sh, Crobat, HackerTarget, Anubis, CertSpotter, SecurityTrails in parallel."""
    all_subs: Set[str] = set()
    headers = {"User-Agent": USER_AGENT}

    async with _make_aiohttp_session(headers) as session:
        tasks = [
            _fetch_crtsh_async(session, domain),
            _fetch_crobat_async(session, domain),
            _fetch_hackertarget_async(session, domain),
            _fetch_anubis_async(session, domain),
            _fetch_certspotter_async(session, domain, CERTSPOTTER_API_TOKEN or None),
        ]
        if SECURITYTRAILS_API_KEY:
            tasks.append(_fetch_securitytrails_async(session, domain, SECURITYTRAILS_API_KEY))
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for r in results:
            if isinstance(r, set):
                all_subs |= r
            elif isinstance(r, Exception):
                pass
    return all_subs


class SubdomainEnricher(AbstractEnricher):
    """Enricher for subdomain discovery (passive: crt.sh, Crobat; active: brute-force)."""

    name = "subdomain"

    def __init__(self, enable_bruteforce: bool = False):
        self.enable_bruteforce = enable_bruteforce

    def _active_bruteforce(self, domain: str) -> Set[str]:
        """Active DNS brute-force (async when aiodns available, else sync)."""
        if not self.enable_bruteforce:
            return set()

        wordlist = _load_wordlist()[:500]
        if not wordlist:
            return set()

        try:
            import aiodns
            resolver = aiodns.DNSResolver()

            async def _resolve_one(candidate: str) -> Optional[str]:
                try:
                    await resolver.query(candidate, "A")
                    return candidate
                except Exception:
                    return None

            async def _resolve():
                sem = asyncio.Semaphore(50)
                async def limited(c):
                    async with sem:
                        return await _resolve_one(c)
                tasks = [limited(f"{sub}.{domain}") for sub in wordlist]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                return {r for r in results if isinstance(r, str)}

            return asyncio.run(_resolve())
        except ImportError:
            import dns.resolver
            found: Set[str] = set()
            for sub in wordlist:
                candidate = f"{sub}.{domain}"
                try:
                    dns.resolver.resolve(candidate, "A")
                    found.add(candidate)
                except Exception:
                    pass
            return found

    def enrich(self, domain: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        domain = domain.lower().strip()
        all_subs: Set[str] = set()

        # Run aiohttp (crt.sh, Crobat, HackerTarget) + DNSDumpster (sync) in parallel
        with ThreadPoolExecutor(max_workers=2) as executor:
            async_future = executor.submit(asyncio.run, _fetch_passive_async(domain))
            dnsdumpster_future = executor.submit(_fetch_dnsdumpster, domain)
            for future in as_completed((async_future, dnsdumpster_future)):
                try:
                    all_subs |= future.result(timeout=CRTSH_TIMEOUT + 15)
                except Exception:
                    pass

        all_subs |= self._active_bruteforce(domain)

        # Deduplicate: www.events.example.com and events.example.com -> keep events.example.com
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

        subdomains = sorted(list(deduped))
        return {"subdomains": subdomains}
