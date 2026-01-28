"""
WHOIS Lookup Module

This module provides functionality to retrieve WHOIS information for a domain.
"""

import whois
from typing import Dict, Optional, Any, Iterable
from datetime import datetime
from dateutil import parser as date_parser


def _normalize_date(value: Any) -> Optional[str]:
    """
    Normalize various WHOIS date formats to YYYY-MM-DD.
    python-whois can return datetime, strings, lists, or other weird values.
    We never raise here: if we cannot parse, return None.
    """
    if value is None:
        return None

    candidates: Iterable[Any]
    if isinstance(value, list) or isinstance(value, tuple) or isinstance(value, set):
        candidates = value
    else:
        candidates = [value]

    for v in candidates:
        if v is None:
            continue
        if isinstance(v, datetime):
            return v.strftime("%Y-%m-%d")
        if isinstance(v, (int, float)):
            continue

        s = str(v).strip()
        if not s or s.lower() in ("none", "null", "0"):
            continue

        try:
            dt = date_parser.parse(s, fuzzy=True, ignoretz=True)
            return dt.strftime("%Y-%m-%d")
        except Exception:
            continue

    return None


def get_whois_info(domain: str) -> Dict:
    """
    Retrieves WHOIS information for a domain.
    
    Args:
        domain: Domain name to query
    
    Returns:
        Dictionary with WHOIS data:
        {
            'registrar': '...',
            'creation_date': '2020-01-15',
            'expiration_date': '2025-01-15',
            'name_servers': [...],
            'emails': [...],
            'status': 'active'
        }
    
    Notes:
        Some registries/TLDs return non-standard WHOIS formats, and `python-whois`
        may raise during parsing (e.g. "Unknown date format ...").
        This function must NOT crash the full scan: if WHOIS fails, it returns
        a dict with an `error` field instead of raising.
    """
    try:
        try:
            w = whois.whois(domain)
        except Exception as e:
            return {
                "domain": domain,
                "registrar": None,
                "creation_date": None,
                "expiration_date": None,
                "name_servers": [],
                "emails": [],
                "status": None,
                "error": f"WHOIS lookup failed: {str(e)}",
            }

        creation_date = _normalize_date(getattr(w, "creation_date", None))
        expiration_date = _normalize_date(getattr(w, "expiration_date", None))
        
        # Extract emails
        emails = []
        w_emails = getattr(w, "emails", None)
        if w_emails:
            if isinstance(w_emails, (list, tuple, set)):
                emails = [str(email) for email in w_emails if email]
            else:
                emails = [str(w_emails)]
        
        # Extract name servers
        name_servers = []
        w_name_servers = getattr(w, "name_servers", None)
        if w_name_servers:
            if isinstance(w_name_servers, (list, tuple, set)):
                name_servers = [str(ns).lower() for ns in w_name_servers]
            else:
                name_servers = [str(w_name_servers).lower()]

        # Status can be list depending on TLD/registry
        w_status = getattr(w, "status", None)
        if isinstance(w_status, (list, tuple, set)):
            status: Optional[str] = ", ".join([str(s) for s in w_status if s])
        else:
            status = str(w_status) if w_status else None
        
        return {
            "domain": domain,
            "registrar": str(getattr(w, "registrar", None)) if getattr(w, "registrar", None) else None,
            "creation_date": creation_date,
            "expiration_date": expiration_date,
            "name_servers": name_servers,
            "emails": emails,
            "status": status,
        }
    except Exception as e:
        return {
            "domain": domain,
            "registrar": None,
            "creation_date": None,
            "expiration_date": None,
            "name_servers": [],
            "emails": [],
            "status": None,
            "error": f"WHOIS lookup failed: {str(e)}",
        }
