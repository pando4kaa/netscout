"""
WHOIS Lookup - retrieves WHOIS information for a domain.

`python-whois` is fragile across TLDs (it can both raise during parsing and
return wildly different shapes). This module never lets WHOIS failures crash
the broader scan; on error it returns a result dict with an `error` field.
"""

import logging
from datetime import datetime
from typing import Any, Dict, Iterable, Optional

import whois
from dateutil import parser as date_parser

logger = logging.getLogger(__name__)


def _empty_whois_result(domain: str, error: Optional[str] = None) -> Dict[str, Any]:
    return {
        "domain": domain,
        "registrar": None,
        "creation_date": None,
        "expiration_date": None,
        "name_servers": [],
        "emails": [],
        "status": None,
        **({"error": error} if error else {}),
    }


def _normalize_date(value: Any) -> Optional[str]:
    """Normalize WHOIS date values (datetime, str, list, None) to YYYY-MM-DD or None."""
    if value is None:
        return None

    candidates: Iterable[Any] = value if isinstance(value, (list, tuple, set)) else [value]

    for candidate in candidates:
        if candidate is None or isinstance(candidate, (int, float)):
            continue
        if isinstance(candidate, datetime):
            return candidate.strftime("%Y-%m-%d")

        text_value = str(candidate).strip()
        if not text_value or text_value.lower() in ("none", "null", "0"):
            continue

        try:
            parsed = date_parser.parse(text_value, fuzzy=True, ignoretz=True)
            return parsed.strftime("%Y-%m-%d")
        except (ValueError, OverflowError, date_parser.ParserError):
            continue

    return None


def _coerce_str_list(value: Any, *, lower: bool = False) -> list:
    """Coerce WHOIS attribute (str | iterable | None) into a clean list[str]."""
    if not value:
        return []
    items = value if isinstance(value, (list, tuple, set)) else [value]
    result = []
    for item in items:
        if not item:
            continue
        text = str(item)
        result.append(text.lower() if lower else text)
    return result


def get_whois_info(domain: str) -> Dict[str, Any]:
    """
    Retrieve WHOIS information for `domain`.

    Returns a dict with keys: registrar, creation_date, expiration_date,
    name_servers, emails, status. On failure returns the same shape with
    an additional `error` key (does not raise).
    """
    try:
        record = whois.whois(domain)
    except Exception as exc:
        return _empty_whois_result(domain, error=f"WHOIS lookup failed: {exc}")

    try:
        emails = _coerce_str_list(getattr(record, "emails", None))
        name_servers = _coerce_str_list(getattr(record, "name_servers", None), lower=True)

        status_value = getattr(record, "status", None)
        if isinstance(status_value, (list, tuple, set)):
            status: Optional[str] = ", ".join(str(s) for s in status_value if s) or None
        else:
            status = str(status_value) if status_value else None

        registrar_value = getattr(record, "registrar", None)
        registrar = str(registrar_value) if registrar_value else None

        return {
            "domain": domain,
            "registrar": registrar,
            "creation_date": _normalize_date(getattr(record, "creation_date", None)),
            "expiration_date": _normalize_date(getattr(record, "expiration_date", None)),
            "name_servers": name_servers,
            "emails": emails,
            "status": status,
        }
    except Exception as exc:
        logger.warning("WHOIS post-parse failed for %s: %s", domain, exc)
        return _empty_whois_result(domain, error=f"WHOIS lookup failed: {exc}")
