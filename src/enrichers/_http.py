"""
Shared aiohttp helpers for enrichers.

Centralizes the aiohttp session factory so that DNS-resolver and SSL
behaviour stay consistent across DNS / subdomain / tech / external-APIs.
"""

import aiohttp


def make_aiohttp_session(
    headers: dict,
    *,
    verify_ssl: bool = True,
) -> aiohttp.ClientSession:
    """
    Build an aiohttp client session with a thread-pool DNS resolver.

    The threaded resolver avoids `aiodns` startup issues on Windows and on
    hosts where the default event loop policy isn't compatible with c-ares.
    """
    connector = aiohttp.TCPConnector(
        resolver=aiohttp.resolver.ThreadedResolver(),
        ssl=verify_ssl,
    )
    return aiohttp.ClientSession(headers=headers, connector=connector)
