#!/usr/bin/env python3
"""
Probe passive subdomain sources individually (same HTTP clients as SubdomainEnricher).

Usage (from repo root):
  python scripts/probe_subdomain_sources.py example.com
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.config.settings import CERTSPOTTER_API_TOKEN, SECURITYTRAILS_API_KEY, USER_AGENT
from src.enrichers._http import make_aiohttp_session
from src.enrichers.subdomain import (
    _fetch_anubis_async,
    _fetch_certspotter_async,
    _fetch_crobat_async,
    _fetch_crtsh_async,
    _fetch_hackertarget_async,
    _fetch_securitytrails_async,
    _fetch_dnsdumpster,
)


async def _run(domain: str) -> dict:
    headers = {"User-Agent": USER_AGENT}
    rows: dict[str, int | str] = {}

    async with make_aiohttp_session(headers) as session:
        pairs = [
            ("crt.sh", _fetch_crtsh_async(session, domain)),
            ("Crobat (sonar.omnisint.io)", _fetch_crobat_async(session, domain)),
            ("HackerTarget hostsearch", _fetch_hackertarget_async(session, domain)),
            ("Anubis (jonlu.ca)", _fetch_anubis_async(session, domain)),
            (
                "CertSpotter",
                _fetch_certspotter_async(session, domain, CERTSPOTTER_API_TOKEN or None),
            ),
        ]
        if SECURITYTRAILS_API_KEY:
            pairs.append(
                (
                    "SecurityTrails",
                    _fetch_securitytrails_async(session, domain, SECURITYTRAILS_API_KEY),
                )
            )
        else:
            rows["SecurityTrails"] = "skipped (no SECURITYTRAILS_API_KEY)"

        for label, coro in pairs:
            try:
                result = await coro
            except Exception as exc:
                rows[label] = f"error: {exc}"
                continue
            if isinstance(result, set):
                rows[label] = len(result)
            else:
                rows[label] = 0

    # DNSDumpster is sync (ThreadPool in enricher); run in executor
    loop = asyncio.get_running_loop()
    try:
        dd = await loop.run_in_executor(None, _fetch_dnsdumpster, domain)
        rows["DNSDumpster"] = len(dd) if isinstance(dd, set) else str(dd)
    except Exception as exc:
        rows["DNSDumpster"] = f"error: {exc}"

    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("domain", nargs="?", default="example.com")
    args = ap.parse_args()
    out = asyncio.run(_run(args.domain.lower().strip()))
    print(json.dumps({"domain": args.domain, "unique_counts_by_source": out}, indent=2))


if __name__ == "__main__":
    main()
