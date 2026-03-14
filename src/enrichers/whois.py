"""
WHOIS Enricher — retrieves registration information for a domain.
"""

import re
import subprocess
import whois
from datetime import datetime
from dateutil import parser as date_parser
from typing import Any, Dict, Iterable, Optional

from src.enrichers.base import AbstractEnricher
from src.core.models import WhoisInfo


def _parse_compact_date(s: str) -> Optional[str]:
    """Parse compact formats like 20090716153419 (YYYYMMDDHHMMSS) or 2009-07-16."""
    s = str(s).strip()
    # YYYYMMDDHHMMSS or YYYYMMDD
    m = re.search(r"(\d{4})[-.]?(\d{2})[-.]?(\d{2})(?:[-.\s]?\d{2}[-.]?\d{2}[-.]?\d{2})?", s)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    return None


def _normalize_date(value: Any) -> Optional[str]:
    """Normalize various WHOIS date formats to YYYY-MM-DD."""
    if value is None:
        return None

    candidates: Iterable[Any]
    if isinstance(value, (list, tuple, set)):
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

        # Try compact format first (e.g. 0-UANIC 20090716153419)
        compact = _parse_compact_date(s)
        if compact:
            return compact

        try:
            dt = date_parser.parse(s, fuzzy=True, ignoretz=True)
            return dt.strftime("%Y-%m-%d")
        except Exception:
            continue

    return None


def _whois_socket(domain: str, server: str = "whois.iana.org", timeout: int = 20) -> Optional[str]:
    """Query WHOIS via socket (fallback when subprocess whois unavailable)."""
    try:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((server, 43))
        sock.sendall(f"{domain}\r\n".encode())
        data = b""
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            data += chunk
        sock.close()
        return data.decode("utf-8", errors="ignore")
    except Exception:
        return None


def _parse_whois_raw(raw: str, domain: str) -> Optional[WhoisInfo]:
    """Parse raw WHOIS text into WhoisInfo."""
    if not raw or len(raw) < 10:
        return None
    info = WhoisInfo(domain=domain)
    lines = raw.lower().split("\n")
    for line in lines:
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        key, val = key.strip(), val.strip()
        if not val:
            continue
        if "creation" in key or "created" in key or "registered" in key:
            info.creation_date = _parse_compact_date(val) or _normalize_date(val)
        elif "expir" in key or "paid-till" in key or "renew" in key:
            info.expiration_date = _parse_compact_date(val) or _normalize_date(val)
        elif "registrar" in key and not info.registrar:
            info.registrar = val
        elif "nserver" in key or "name server" in key or "nameserver" in key:
            ns = val.rstrip(".").strip()
            if ns and ns not in info.name_servers:
                info.name_servers.append(ns)
        elif "status" in key and not info.status:
            info.status = val
            # Parse ok-until 20260716153413 as expiration
            if "ok-until" in val and not info.expiration_date:
                info.expiration_date = _parse_compact_date(val)
    return info


def _whois_raw_fallback(domain: str) -> Optional[WhoisInfo]:
    """Fallback when python-whois fails on date parsing."""
    raw = None
    # Try subprocess whois first (Linux/Mac)
    try:
        import shutil
        whois_cmd = shutil.which("whois") or "whois"
        result = subprocess.run(
            [whois_cmd, domain],
            capture_output=True,
            text=True,
            timeout=15,
        )
        raw = (result.stdout or "") + (result.stderr or "")
    except Exception:
        pass

    # Fallback: socket to whois server (Windows, no whois cmd)
    if not raw or len(raw) < 50:
        tld = domain.split(".")[-1] if "." in domain else ""
        servers = {"ua": "whois.ua", "com": "whois.verisign-grs.com", "org": "whois.pir.org"}
        server = servers.get(tld, "whois.iana.org")
        # whois.ua is often slow; use longer timeout for .ua
        timeout = 25 if tld == "ua" else 20
        raw = _whois_socket(domain, server, timeout)
        if not raw and server != "whois.iana.org":
            raw = _whois_socket(domain, "whois.iana.org", timeout)

    return _parse_whois_raw(raw, domain) if raw else None


class WhoisEnricher(AbstractEnricher):
    """Enricher for WHOIS registration data."""

    name = "whois"

    def enrich(self, domain: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        try:
            from src.services.cache_service import get, set, TTL_WHOIS

            cache_key = f"whois:{domain}"
            cached = get(cache_key)
            if cached is not None and isinstance(cached, dict):
                return {"whois_info": WhoisInfo(**cached)}
        except Exception:
            pass

        try:
            try:
                # Set socket timeout so whois.whois() fails fast; fallback will retry with our socket
                import socket
                old_timeout = socket.getdefaulttimeout()
                socket.setdefaulttimeout(12)
                try:
                    w = whois.whois(domain)
                finally:
                    socket.setdefaulttimeout(old_timeout)
            except Exception as e:
                # Fallback for domains with non-standard date formats (e.g. .ua, 0-UANIC)
                fallback = _whois_raw_fallback(domain)
                if fallback and (fallback.creation_date or fallback.expiration_date or fallback.name_servers):
                    try:
                        from src.services.cache_service import set, TTL_WHOIS

                        set(f"whois:{domain}", fallback.model_dump(), TTL_WHOIS)
                    except Exception:
                        pass
                    return {"whois_info": fallback}
                return {
                    "whois_info": WhoisInfo(
                        domain=domain,
                        error=f"WHOIS lookup failed: {str(e)}",
                    )
                }

            creation_date = _normalize_date(getattr(w, "creation_date", None))
            expiration_date = _normalize_date(getattr(w, "expiration_date", None))

            emails = []
            w_emails = getattr(w, "emails", None)
            if w_emails:
                if isinstance(w_emails, (list, tuple, set)):
                    emails = [str(email) for email in w_emails if email]
                else:
                    emails = [str(w_emails)]

            name_servers = []
            w_name_servers = getattr(w, "name_servers", None)
            if w_name_servers:
                if isinstance(w_name_servers, (list, tuple, set)):
                    name_servers = [str(ns).lower() for ns in w_name_servers]
                else:
                    name_servers = [str(w_name_servers).lower()]

            w_status = getattr(w, "status", None)
            if isinstance(w_status, (list, tuple, set)):
                status = ", ".join([str(s) for s in w_status if s]) if w_status else None
            else:
                status = str(w_status) if w_status else None

            registrar = getattr(w, "registrar", None)
            info = WhoisInfo(
                domain=domain,
                registrar=str(registrar) if registrar else None,
                creation_date=creation_date,
                expiration_date=expiration_date,
                name_servers=name_servers,
                emails=emails,
                status=status,
            )
            try:
                from src.services.cache_service import set, TTL_WHOIS

                set(f"whois:{domain}", info.model_dump(), TTL_WHOIS)
            except Exception:
                pass
            return {"whois_info": info}
        except Exception as e:
            # Fallback for parse errors (e.g. Unknown date format: 0-UANIC)
            fallback = _whois_raw_fallback(domain)
            if fallback and (fallback.creation_date or fallback.expiration_date or fallback.name_servers):
                try:
                    from src.services.cache_service import set, TTL_WHOIS

                    set(f"whois:{domain}", fallback.model_dump(), TTL_WHOIS)
                except Exception:
                    pass
                return {"whois_info": fallback}
            return {
                "whois_info": WhoisInfo(
                    domain=domain,
                    error=f"WHOIS lookup failed: {str(e)}",
                )
            }
