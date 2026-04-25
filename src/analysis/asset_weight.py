"""
Asset criticality weights for composite risk scoring.
"""

import ipaddress
from urllib.parse import urlparse


CRITICAL_PREFIXES = {"api", "auth", "login", "sso", "vpn", "admin", "portal"}
AUXILIARY_PREFIXES = {"www", "mail", "mx", "smtp", "imap", "pop"}
LOWER_CRITICALITY_PREFIXES = {"dev", "test", "staging", "stage", "demo", "qa", "sandbox"}


def normalize_asset_host(value: str) -> str:
    """Extract a stable host value from URL/IP/domain-like alert targets."""
    if not value:
        return ""

    candidate = str(value).strip().lower()
    if "://" in candidate:
        parsed = urlparse(candidate)
        candidate = parsed.hostname or candidate
    else:
        candidate = candidate.split("/")[0]
        candidate = candidate.split(":")[0]

    return candidate.strip().strip(".")


def classify_asset(host: str, apex_domain: str) -> str:
    """Classify an asset by its role relative to the scanned apex domain."""
    host = normalize_asset_host(host)
    apex = normalize_asset_host(apex_domain)

    if not host:
        return "unknown"

    try:
        ipaddress.ip_address(host)
        return "ip"
    except ValueError:
        pass

    if apex and host == apex:
        return "apex"

    labels = host.split(".")
    prefix = labels[0] if labels else ""

    if prefix in CRITICAL_PREFIXES:
        return "critical_service"
    if prefix in AUXILIARY_PREFIXES:
        return "auxiliary_service"
    if prefix in LOWER_CRITICALITY_PREFIXES:
        return "lower_criticality"
    if apex and host.endswith(f".{apex}"):
        return "subdomain"

    return "external_or_unknown"


def asset_weight(host: str, apex_domain: str) -> float:
    """
    Return asset criticality coefficient w_i for composite risk scoring.

    Values intentionally stay small and explainable: production-facing assets
    receive more weight than testing/demo names, while IP-only alerts remain
    important because they usually represent reachable network services.
    """
    asset_class = classify_asset(host, apex_domain)
    weights = {
        "apex": 1.0,
        "critical_service": 1.2,
        "auxiliary_service": 0.9,
        "subdomain": 0.8,
        "ip": 0.85,
        "lower_criticality": 0.5,
        "external_or_unknown": 0.7,
        "unknown": 0.7,
    }
    return weights.get(asset_class, 0.7)
