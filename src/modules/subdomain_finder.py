"""
Subdomain Finder Module

This module provides functionality to discover subdomains using passive methods
(Certificate Transparency logs).
"""

import requests
import json
from typing import List, Set, Optional, Iterable
import time

from src.config.settings import HTTP_TIMEOUT, HTTP_RETRIES, USER_AGENT
from src.utils.validators import is_valid_domain


def _fetch_crtsh_json(url: str, timeout: int, retries: int) -> Optional[list]:
    """
    Fetch JSON from crt.sh with retries/backoff.
    Returns parsed JSON list or None if failed.
    """
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json,text/plain,*/*",
    }

    last_error: Optional[str] = None

    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(url, headers=headers, timeout=timeout)

            # Retry on transient errors / rate limiting
            if resp.status_code in (429, 500, 502, 503, 504):
                last_error = f"crt.sh HTTP {resp.status_code}"
            elif resp.status_code != 200:
                print(f"Warning: crt.sh returned status code {resp.status_code}")
                return None
            else:
                try:
                    return resp.json()
                except json.JSONDecodeError:
                    # crt.sh sometimes returns HTML or invalid JSON
                    last_error = "Invalid JSON response from crt.sh"

        except requests.Timeout:
            last_error = "crt.sh request timed out"
        except requests.RequestException as e:
            last_error = f"Error querying crt.sh: {e}"

        # Backoff before retrying
        if attempt < retries:
            sleep_s = min(1.0 * (2 ** (attempt - 1)), 8.0)
            time.sleep(sleep_s)

    if last_error:
        print(f"Warning: {last_error}")
    return None


def _extract_subdomains_from_crt_entries(domain: str, data: Iterable[dict]) -> Set[str]:
    subdomains: Set[str] = set()
    domain = domain.lower().strip()
    suffix = f".{domain}"

    for entry in data:
        name_value = entry.get("name_value", "")

        # Some entries contain multiple domains separated by newlines
        for name in str(name_value).replace("\n", ",").split(","):
            name = name.strip().lower()
            if not name:
                continue

            # Remove trailing dot if present
            if name.endswith("."):
                name = name[:-1]

            # Filter out wildcards
            if name.startswith("*."):
                name = name[2:]

            # Drop obviously invalid entries (emails / descriptive strings)
            if " " in name or "@" in name:
                continue

            # Keep only real subdomains like foo.example.com (not example.com itself)
            if not name.endswith(suffix):
                continue

            if is_valid_domain(name):
                subdomains.add(name)

    # Remove the base domain itself
    subdomains.discard(domain.lower())
    return subdomains


def find_subdomains_passive(domain: str) -> List[str]:
    """
    Finds subdomains using Certificate Transparency logs (crt.sh).
    
    Args:
        domain: Base domain to search for (e.g., 'example.com')
    
    Returns:
        List of unique subdomains:
        ['www.example.com', 'api.example.com', ...]
    """
    try:
        # crt.sh works more reliably for subdomains with the pattern %.domain
        # NOTE: we URL-encode % as %25
        urls = [
            f"https://crt.sh/?q=%25.{domain}&output=json",
            f"https://crt.sh/?q={domain}&output=json",
        ]

        subdomains: Set[str] = set()

        for url in urls:
            data = _fetch_crtsh_json(url, timeout=HTTP_TIMEOUT, retries=HTTP_RETRIES)
            if not data:
                continue
            subdomains |= _extract_subdomains_from_crt_entries(domain, data)

        return sorted(list(subdomains))
    except Exception as e:
        print(f"Warning: Unexpected error: {e}")

    return []
