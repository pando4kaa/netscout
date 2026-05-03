"""
Asset criticality weights for composite risk scoring.
"""

import ipaddress
import re
from typing import Any, Dict, List
from urllib.parse import urlparse


CRITICAL_PREFIXES = {
    "api",
    "auth",
    "login",
    "sso",
    "vpn",
    "admin",
    "portal",
    "account",
    "accounts",
    "storage",
    "files",
    "dashboard",
    "id",
    "identity",
    "saml",
    "oauth",
    "mfa",
    "payment",
    "payments",
}
AUXILIARY_PREFIXES = {"www", "mail", "mx", "smtp", "imap", "pop", "cdn"}
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


def _hostname_tokens(host: str) -> List[str]:
    """Split hostname labels into searchable role/environment tokens."""
    tokens: List[str] = []
    for label in normalize_asset_host(host).split("."):
        tokens.extend([part for part in re.split(r"[-_]", label) if part])
    return tokens


def asset_context(host: str, apex_domain: str) -> Dict[str, Any]:
    """Return explainable asset role and environment metadata."""
    normalized_host = normalize_asset_host(host)
    apex = normalize_asset_host(apex_domain)

    context: Dict[str, Any] = {
        "host": normalized_host,
        "asset_class": "unknown",
        "business_role": "unknown",
        "environment": "unknown",
        "reason": "Asset could not be classified",
    }

    if not normalized_host:
        return context

    try:
        ipaddress.ip_address(normalized_host)
        context.update(
            {
                "asset_class": "ip",
                "business_role": "network_service",
                "environment": "production",
                "reason": "Target is an IP address with a reachable network service",
            }
        )
        return context
    except ValueError:
        pass

    tokens = _hostname_tokens(normalized_host)
    prefix = tokens[0] if tokens else ""
    is_apex = bool(apex and normalized_host == apex)
    is_subdomain = bool(apex and normalized_host.endswith(f".{apex}"))
    critical_matches = [token for token in tokens if token in CRITICAL_PREFIXES]
    auxiliary_matches = [token for token in tokens if token in AUXILIARY_PREFIXES]
    lower_matches = [token for token in tokens if token in LOWER_CRITICALITY_PREFIXES]
    environment = "non_production" if lower_matches else "production"

    if is_apex:
        context.update(
            {
                "asset_class": "apex",
                "business_role": "main_domain",
                "environment": "production",
                "reason": "Target is the scanned apex domain",
            }
        )
    elif critical_matches:
        context.update(
            {
                "asset_class": "critical_service",
                "business_role": critical_matches[0],
                "environment": environment,
                "reason": f"Hostname contains critical service token '{critical_matches[0]}'",
            }
        )
    elif auxiliary_matches:
        context.update(
            {
                "asset_class": "auxiliary_service",
                "business_role": auxiliary_matches[0],
                "environment": environment,
                "reason": f"Hostname contains auxiliary service token '{auxiliary_matches[0]}'",
            }
        )
    elif lower_matches:
        context.update(
            {
                "asset_class": "lower_criticality",
                "business_role": prefix or "subdomain",
                "environment": "non_production",
                "reason": f"Hostname contains non-production token '{lower_matches[0]}'",
            }
        )
    elif is_subdomain:
        context.update(
            {
                "asset_class": "subdomain",
                "business_role": prefix or "subdomain",
                "environment": "production",
                "reason": "Target is a subdomain of the scanned domain",
            }
        )
    else:
        context.update(
            {
                "asset_class": "external_or_unknown",
                "business_role": prefix or "external",
                "environment": environment,
                "reason": "Target is outside the scanned domain or cannot be mapped confidently",
            }
        )

    return context


def classify_asset(host: str, apex_domain: str) -> str:
    """Classify an asset by its role relative to the scanned apex domain."""
    return asset_context(host, apex_domain)["asset_class"]


def asset_weight(host: str, apex_domain: str) -> float:
    """
    Return asset criticality coefficient w_i for composite risk scoring.

    Values intentionally stay small and explainable: production-facing assets
    receive more weight than testing/demo names, while IP-only alerts remain
    important because they usually represent reachable network services.
    """
    context = asset_context(host, apex_domain)
    asset_class = context["asset_class"]
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
    weight = weights.get(asset_class, 0.7)
    if context.get("environment") == "non_production" and asset_class != "lower_criticality":
        weight *= 0.7
    return round(weight, 2)
