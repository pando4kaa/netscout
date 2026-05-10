"""
External APIs orchestrator.

The actual provider clients live in :mod:`src.enrichers.external` (split by
domain). This module owns:

    * ``ExternalApiEnricher``     - the AbstractEnricher entry point used by
      the scan pipeline; gathers all clients in parallel and merges them into
      a single ``external_apis`` payload.
    * ``fetch_single_external_api`` - synchronous helper used by
      Investigation mode to fetch one provider on demand.

To add a new provider:
    1. Implement ``async def fetch_<provider>(...)`` in the appropriate
       submodule under ``src/enrichers/external/``.
    2. Export it from ``src/enrichers/external/__init__.py``.
    3. Append a ``_TaskSpec`` entry to ``_TASK_SPECS`` below if the provider
       should run during a normal scan; add a branch to
       ``fetch_single_external_api`` if the investigation UI should expose it.
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Dict, List, Optional, Set

import aiohttp

from src.config.settings import (
    ABUSEIPDB_API_KEY,
    ALIENVAULT_OTX_API_KEY,
    CRIMINALIP_API_KEY,
    PHISHTANK_APP_KEY,
    PULSEDIVE_API_KEY,
    SECURITYTRAILS_API_KEY,
    USER_AGENT,
    VIRUSTOTAL_API_KEY,
    ZOOMEYE_API_KEY,
)
from src.enrichers._http import make_aiohttp_session
from src.enrichers.base import AbstractEnricher
from src.enrichers.external import (
    fetch_abuseipdb_check,
    fetch_alienvault_otx_domain,
    fetch_bgpview_ip,
    fetch_criminalip_domain,
    fetch_phishtank_check,
    fetch_pulsedive_info,
    fetch_securitytrails_domain,
    fetch_ssllabs_analyze,
    fetch_threatcrowd_domain,
    fetch_urlscan_search,
    fetch_virustotal_domain,
    fetch_wayback_first_snapshot,
    fetch_zoomeye_search,
)

logger = logging.getLogger(__name__)

_MAX_IPS = 15

CoroutineFactory = Callable[[aiohttp.ClientSession, str], Awaitable[Optional[Dict[str, Any]]]]


@dataclass(frozen=True)
class _TaskSpec:
    """Declarative description of one provider invocation in a scan."""
    key: str
    coro_factory: CoroutineFactory
    enabled: bool = True


def _domain_task_specs(domain: str) -> List[_TaskSpec]:
    """Return per-domain provider tasks (skipped silently when key is absent)."""
    return [
        _TaskSpec(
            "virustotal",
            lambda session, _d=domain: fetch_virustotal_domain(session, _d),
            enabled=bool(VIRUSTOTAL_API_KEY),
        ),
        _TaskSpec(
            "alienvault_otx",
            lambda session, _d=domain: fetch_alienvault_otx_domain(session, _d),
            enabled=bool(ALIENVAULT_OTX_API_KEY),
        ),
        _TaskSpec(
            "securitytrails",
            lambda session, _d=domain: fetch_securitytrails_domain(
                session, _d, SECURITYTRAILS_API_KEY or ""
            ),
            enabled=bool(SECURITYTRAILS_API_KEY),
        ),
        _TaskSpec(
            "urlscan",
            lambda session, _d=domain: fetch_urlscan_search(session, _d),
        ),
        _TaskSpec(
            "threatcrowd",
            lambda session, _d=domain: fetch_threatcrowd_domain(session, _d),
        ),
        _TaskSpec(
            "wayback",
            lambda session, _d=domain: fetch_wayback_first_snapshot(session, _d),
        ),
        _TaskSpec(
            "ssllabs",
            lambda session, _d=domain: fetch_ssllabs_analyze(session, _d),
        ),
        _TaskSpec(
            "phishtank",
            lambda session, _d=domain: fetch_phishtank_check(
                session, f"https://{_d}", PHISHTANK_APP_KEY
            ),
        ),
        _TaskSpec(
            "zoomeye",
            lambda session, _d=domain: fetch_zoomeye_search(
                session, _d, ZOOMEYE_API_KEY or ""
            ),
            enabled=bool(ZOOMEYE_API_KEY),
        ),
        _TaskSpec(
            "criminalip",
            lambda session, _d=domain: fetch_criminalip_domain(
                session, _d, CRIMINALIP_API_KEY or ""
            ),
            enabled=bool(CRIMINALIP_API_KEY),
        ),
        _TaskSpec(
            "pulsedive",
            lambda session, _d=domain: fetch_pulsedive_info(
                session, _d, PULSEDIVE_API_KEY
            ),
        ),
    ]


def _ip_task_specs(ips: List[str]) -> List[_TaskSpec]:
    """Return per-IP provider tasks (BGPView always; AbuseIPDB if key set)."""
    specs: List[_TaskSpec] = []
    for ip in ips:
        specs.append(_TaskSpec(
            "bgpview",
            lambda session, _ip=ip: fetch_bgpview_ip(session, _ip),
        ))
    if ABUSEIPDB_API_KEY:
        for ip in ips:
            specs.append(_TaskSpec(
                "abuseipdb",
                lambda session, _ip=ip: fetch_abuseipdb_check(
                    session, _ip, ABUSEIPDB_API_KEY
                ),
            ))
    return specs


def _flatten_virustotal(data: Dict[str, Any]) -> Dict[str, Any]:
    attributes = data.get("data", {}).get("attributes", {})
    return {
        "last_analysis_stats": attributes.get("last_analysis_stats"),
        "reputation": attributes.get("reputation"),
    }


def _merge_results(
    pairs: List[tuple],
) -> Dict[str, Any]:
    """Combine ``(key, payload)`` tuples into the final ``external_apis`` dict."""
    merged: Dict[str, Any] = {}
    bgp_by_ip: Dict[str, Any] = {}
    abuseipdb_by_ip: Dict[str, Any] = {}

    for key, payload in pairs:
        if payload is None or isinstance(payload, Exception):
            continue
        if key == "bgpview":
            bgp_by_ip[payload["ip"]] = payload
        elif key == "abuseipdb":
            abuseipdb_by_ip[payload["ip"]] = payload
        elif key == "virustotal":
            merged["virustotal"] = _flatten_virustotal(payload)
        else:
            merged[key] = payload

    if bgp_by_ip:
        merged["bgpview"] = {"ips": bgp_by_ip}
    if abuseipdb_by_ip:
        merged["abuseipdb"] = {"ips": abuseipdb_by_ip}
    return merged


async def _fetch_external_apis_async(domain: str, ips: List[str]) -> Dict[str, Any]:
    """Run every applicable provider in parallel and aggregate the responses."""
    headers = {"User-Agent": USER_AGENT}
    async with make_aiohttp_session(headers) as session:
        active = [
            spec for spec in _domain_task_specs(domain) + _ip_task_specs(ips)
            if spec.enabled
        ]
        if not active:
            return {}
        results = await asyncio.gather(
            *[spec.coro_factory(session) for spec in active],
            return_exceptions=True,
        )
        return _merge_results(list(zip([spec.key for spec in active], results)))


def fetch_single_external_api(
    api_name: str,
    domain: Optional[str] = None,
    ip: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Fetch one external API by name; used by Investigation mode."""
    headers = {"User-Agent": USER_AGENT}

    async def _run() -> Optional[Dict[str, Any]]:
        async with make_aiohttp_session(headers) as session:
            if api_name == "virustotal" and domain:
                return await fetch_virustotal_domain(session, domain)
            if api_name == "alienvault_otx" and domain:
                return await fetch_alienvault_otx_domain(session, domain)
            if api_name == "urlscan" and domain:
                return await fetch_urlscan_search(session, domain)
            if api_name == "threatcrowd" and domain:
                return await fetch_threatcrowd_domain(session, domain)
            if api_name == "bgpview" and ip:
                return await fetch_bgpview_ip(session, ip)
            if api_name == "abuseipdb" and ip:
                return await fetch_abuseipdb_check(session, ip, ABUSEIPDB_API_KEY or "")
        return None

    return asyncio.run(_run())


def _collect_unique_ips(context: Optional[Dict[str, Any]]) -> List[str]:
    """Pull IPv4/IPv6 addresses from DNS + port-scan context, dedup'd and capped."""
    if not context:
        return []
    ips: List[str] = []
    seen: Set[str] = set()

    dns = context.get("dns_info")
    if isinstance(dns, dict):
        candidates = (dns.get("a_records") or []) + (dns.get("aaaa_records") or [])
    elif dns is not None and hasattr(dns, "a_records"):
        candidates = list(getattr(dns, "a_records") or []) + list(getattr(dns, "aaaa_records") or [])
    else:
        candidates = []
    for ip in candidates:
        if ip and ip not in seen:
            ips.append(ip)
            seen.add(ip)

    for entry in context.get("port_scan") or []:
        if isinstance(entry, dict):
            ip = entry.get("ip")
            if ip and ip not in seen:
                ips.append(ip)
                seen.add(ip)
    return ips[:_MAX_IPS]


class ExternalApiEnricher(AbstractEnricher):
    """Aggregate enricher that fans out to every configured external provider."""

    name = "external_apis"

    def enrich(self, domain: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        ips = _collect_unique_ips(context)
        result = asyncio.run(_fetch_external_apis_async(domain, ips))
        return {"external_apis": result} if result else {}
