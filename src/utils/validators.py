"""
Domain validation utilities.
"""

import re

# RFC-1035-ish pattern: labels of [a-zA-Z0-9-] (no leading/trailing hyphen),
# at least one dot, alpha-only TLD of >=2 chars.
DOMAIN_PATTERN = re.compile(
    r"^([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$"
)

_PROTOCOL_RE = re.compile(r"^https?://", re.I)
_WWW_RE = re.compile(r"^www\.", re.I)


def is_valid_domain(domain: str) -> bool:
    """Return True iff `domain` parses as a syntactically valid hostname."""
    if not domain or len(domain) > 253:
        return False
    domain = normalize_domain(domain)
    if not DOMAIN_PATTERN.match(domain):
        return False
    if ".." in domain:
        return False
    return True


def normalize_domain(domain: str) -> str:
    """Strip scheme, ``www.``, trailing path, port, and lowercase the host."""
    if not domain:
        return ""
    domain = _PROTOCOL_RE.sub("", domain)
    domain = _WWW_RE.sub("", domain)
    domain = domain.split("/", 1)[0]
    domain = domain.split(":", 1)[0]
    return domain.lower().strip()
