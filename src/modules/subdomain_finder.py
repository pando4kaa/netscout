"""
Subdomain Finder - passive subdomain discovery via Certificate Transparency (crt.sh).
"""

import json
import logging
import time
from typing import Iterable, List, Optional, Set

import requests

from src.config.settings import HTTP_RETRIES, HTTP_TIMEOUT, USER_AGENT
from src.utils.validators import is_valid_domain

logger = logging.getLogger(__name__)

_RETRYABLE_STATUS = {429, 500, 502, 503, 504}
_MAX_BACKOFF_SECONDS = 8.0


def _fetch_crtsh_json(url: str, timeout: int, retries: int) -> Optional[list]:
    """GET `url` and return parsed JSON. Retries with exponential backoff on transient errors."""
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json,text/plain,*/*",
    }
    last_error: Optional[str] = None

    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(url, headers=headers, timeout=timeout)
            if resp.status_code == 200:
                try:
                    return resp.json()
                except json.JSONDecodeError:
                    last_error = "Invalid JSON response from crt.sh"
            elif resp.status_code in _RETRYABLE_STATUS:
                last_error = f"crt.sh HTTP {resp.status_code}"
            else:
                logger.warning("crt.sh returned status %s for %s", resp.status_code, url)
                return None
        except requests.Timeout:
            last_error = "crt.sh request timed out"
        except requests.RequestException as exc:
            last_error = f"crt.sh request error: {exc}"

        if attempt < retries:
            backoff = min(1.0 * (2 ** (attempt - 1)), _MAX_BACKOFF_SECONDS)
            time.sleep(backoff)

    if last_error:
        logger.warning("crt.sh failed after %d attempts: %s", retries, last_error)
    return None


def _extract_subdomains_from_crt_entries(domain: str, data: Iterable[dict]) -> Set[str]:
    """Pull valid subdomains of `domain` out of crt.sh response rows."""
    subdomains: Set[str] = set()
    domain = domain.lower().strip()
    suffix = f".{domain}"

    for entry in data:
        name_value = entry.get("name_value", "")
        # crt.sh sometimes puts multiple SANs in one row separated by newlines.
        for raw_name in str(name_value).replace("\n", ",").split(","):
            cleaned = raw_name.strip().lower().rstrip(".")
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


def find_subdomains_passive(domain: str) -> List[str]:
    """
    Discover subdomains of `domain` via Certificate Transparency logs (crt.sh).

    Returns a sorted list. Returns an empty list on any failure (does not raise);
    errors are logged at WARNING level.
    """
    try:
        # crt.sh returns more results when querying with the wildcard prefix `%.`
        # (URL-encoded as `%25.`).
        urls = [
            f"https://crt.sh/?q=%25.{domain}&output=json",
            f"https://crt.sh/?q={domain}&output=json",
        ]

        subdomains: Set[str] = set()
        for url in urls:
            data = _fetch_crtsh_json(url, timeout=HTTP_TIMEOUT, retries=HTTP_RETRIES)
            if data:
                subdomains |= _extract_subdomains_from_crt_entries(domain, data)
        return sorted(subdomains)
    except Exception as exc:
        logger.warning("Unexpected error in find_subdomains_passive(%s): %s", domain, exc)
        return []
