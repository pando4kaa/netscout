"""
Technology Detector Enricher — detects technologies via HTTP headers, favicon, robots.txt, etc.
Uses aiohttp for async HTTP requests.
"""

import asyncio
import hashlib
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse

import aiohttp

from src.config.settings import HTTP_TIMEOUT, HTTP_VERIFY_SSL, USER_AGENT
from src.enrichers.base import AbstractEnricher
from src.core.models import TechStack, SecurityHeadersInfo


def _parse_meta_tags(html: str) -> tuple[Optional[str], Optional[str]]:
    """Extract meta generator and CMS hints from HTML."""
    generator = None
    cms = None
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html[:50000], "html.parser")
        meta_gen = soup.find("meta", attrs={"name": "generator"})
        if meta_gen and meta_gen.get("content"):
            generator = meta_gen["content"].strip()
        meta_cms = soup.find("meta", attrs={"name": re.compile(r"cms|generator", re.I)})
        if meta_cms and meta_cms.get("content"):
            cms = meta_cms["content"].strip()
        if not cms and "wp-content" in html:
            cms = "WordPress"
        elif not cms and "drupal" in html.lower():
            cms = "Drupal"
    except Exception:
        pass
    return generator, cms


async def _favicon_hash_async(session: aiohttp.ClientSession, url: str) -> Optional[int]:
    """Compute favicon hash (Wappalyzer-style)."""
    try:
        favicon_url = urljoin(url.rstrip("/") + "/", "/favicon.ico")
        async with session.get(favicon_url, timeout=aiohttp.ClientTimeout(total=HTTP_TIMEOUT)) as resp:
            if resp.status == 200:
                content = await resp.read()
                if content:
                    return int(hashlib.md5(content).hexdigest(), 16) & 0xFFFFFFFF
    except Exception:
        pass
    return None


async def _fetch_robots_txt_async(session: aiohttp.ClientSession, base_url: str) -> Optional[str]:
    """Fetch robots.txt content (first 2KB)."""
    try:
        url = f"{base_url}/robots.txt"
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=HTTP_TIMEOUT)) as resp:
            if resp.status == 200:
                text = await resp.text()
                return text[:2048] if text else None
    except Exception:
        pass
    return None


async def _fetch_security_txt_async(session: aiohttp.ClientSession, base_url: str) -> Optional[str]:
    """Fetch .well-known/security.txt or /security.txt."""
    try:
        for path in ["/.well-known/security.txt", "/security.txt"]:
            url = f"{base_url.rstrip('/')}{path}"
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=HTTP_TIMEOUT)) as resp:
                if resp.status == 200:
                    text = await resp.text()
                    return text[:2048] if text else None
    except Exception:
        pass
    return None


async def _detect_tech_async(session: aiohttp.ClientSession, url: str) -> TechStack:
    """Detect technologies for a URL using aiohttp."""
    try:
        async with session.get(
            url,
            timeout=aiohttp.ClientTimeout(total=HTTP_TIMEOUT),
            allow_redirects=True,
        ) as resp:
            text = await resp.text()
            headers = {k.lower(): v for k, v in resp.headers.items()}

            server = headers.get("server")
            x_powered = headers.get("x-powered-by")
            techs: List[str] = []

            if server:
                techs.append(f"Server: {server}")
            if x_powered:
                techs.append(f"X-Powered-By: {x_powered}")
            if "x-aspnet-version" in headers:
                techs.append("ASP.NET")
            if "x-drupal-cache" in headers:
                techs.append("Drupal")
            if "x-generator" in headers:
                techs.append(headers["x-generator"])
            if "wp-" in str(text[:5000]):
                techs.append("WordPress")

            parsed = urlparse(url)
            base = f"{parsed.scheme}://{parsed.netloc}"

            favicon_hash, robots_txt, security_txt = await asyncio.gather(
                _favicon_hash_async(session, url),
                _fetch_robots_txt_async(session, base),
                _fetch_security_txt_async(session, base),
            )
            if favicon_hash:
                techs.append(f"Favicon hash: {favicon_hash}")

            meta_generator, meta_cms = _parse_meta_tags(text)
            if meta_generator:
                techs.append(f"Generator: {meta_generator}")
            if meta_cms:
                techs.append(f"CMS: {meta_cms}")

            # Extract security headers (HSTS, X-Frame-Options, CSP, etc.)
            sec_headers = SecurityHeadersInfo(
                strict_transport_security=headers.get("strict-transport-security"),
                x_frame_options=headers.get("x-frame-options"),
                content_security_policy=headers.get("content-security-policy"),
                x_content_type_options=headers.get("x-content-type-options"),
                referrer_policy=headers.get("referrer-policy"),
            )

            return TechStack(
                url=url,
                technologies=techs,
                headers=dict(headers),
                security_headers=sec_headers,
                server=server,
                x_powered_by=x_powered,
                favicon_hash=favicon_hash,
                robots_txt=robots_txt,
                security_txt=security_txt,
                meta_generator=meta_generator,
                meta_cms=meta_cms,
            )
    except Exception as e:
        return TechStack(url=url, error=str(e) or "Connection failed")


def _make_aiohttp_session(headers: dict, verify_ssl: bool = True) -> aiohttp.ClientSession:
    """Create aiohttp session with ThreadedResolver (avoids aiodns DNS issues on some systems)."""
    connector = aiohttp.TCPConnector(
        resolver=aiohttp.resolver.ThreadedResolver(),
        ssl=verify_ssl,
    )
    return aiohttp.ClientSession(headers=headers, connector=connector)


def _is_mail_subdomain(url: str) -> bool:
    """Check if URL hostname suggests a mail server (mx, mail, smtp)."""
    try:
        host = urlparse(url).netloc.lower().split(":")[0]
        return any(host.startswith(p) for p in ("mx.", "mail.", "smtp."))
    except Exception:
        return False


async def _fetch_tech_stack_async(urls: List[str], verify_ssl: bool = True) -> Dict[str, Any]:
    """Fetch tech stack for multiple URLs in parallel."""
    tech_stack: Dict[str, Any] = {}
    headers = {"User-Agent": USER_AGENT}

    async with _make_aiohttp_session(headers, verify_ssl=verify_ssl) as session:
        tasks = [_detect_tech_async(session, url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for url, result in zip(urls, results):
            if isinstance(result, TechStack):
                tech_stack[result.url] = result.model_dump()
            elif isinstance(result, Exception):
                tech_stack[url] = TechStack(url=url, error=str(result) or "Connection failed").model_dump()

    return tech_stack


class TechEnricher(AbstractEnricher):
    """Enricher for technology fingerprinting. Uses subdomains from context."""

    name = "tech"

    def enrich(self, domain: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        urls_to_check: List[str] = []
        base = f"https://{domain}"
        urls_to_check.append(base)

        if context and context.get("subdomains"):
            for sub in context["subdomains"][:10]:
                url = f"https://{sub}"
                if not _is_mail_subdomain(url):
                    urls_to_check.append(url)

        urls_to_check = list(dict.fromkeys(urls_to_check))
        tech_stack = asyncio.run(_fetch_tech_stack_async(urls_to_check, verify_ssl=HTTP_VERIFY_SSL))
        return {"tech_stack": tech_stack if tech_stack else None}
