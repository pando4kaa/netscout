"""
WHOIS Enricher - retrieves registration information for a domain.

Strategy:
  1. Try `python-whois` (fast, but fragile on .ua / non-standard registries).
  2. On any failure or when essential fields are missing, fall back to
     a raw whois query (via `subprocess` then a socket connection).
  3. Cache the final WhoisInfo for `TTL_WHOIS` seconds.
"""

import logging
import re
import shutil
import socket
import subprocess
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional

import whois
from dateutil import parser as date_parser

from src.core.models import WhoisInfo
from src.enrichers.base import AbstractEnricher

logger = logging.getLogger(__name__)

_PYTHON_WHOIS_TIMEOUT_SECONDS = 12
_RAW_WHOIS_TIMEOUT_DEFAULT = 20
_RAW_WHOIS_TIMEOUT_UA = 25
_DATE_KEY_HINTS_CREATION = ("creation", "created", "registered")
_DATE_KEY_HINTS_EXPIRATION = ("expir", "paid-till", "renew")
_NS_KEY_HINTS = ("nserver", "name server", "nameserver")
_TLD_WHOIS_SERVERS = {
    "ua": "whois.ua",
    "com": "whois.verisign-grs.com",
    "org": "whois.pir.org",
}


def _parse_compact_date(raw: str) -> Optional[str]:
    """Parse compact formats like `20090716153419` (YYYYMMDDHHMMSS) or `2009-07-16`."""
    text = str(raw).strip()
    match = re.search(r"(\d{4})[-.]?(\d{2})[-.]?(\d{2})(?:[-.\s]?\d{2}[-.]?\d{2}[-.]?\d{2})?", text)
    if match:
        return f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
    return None


def _normalize_date(value: Any) -> Optional[str]:
    """Normalize various WHOIS date formats to YYYY-MM-DD."""
    if value is None:
        return None

    candidates: Iterable[Any] = value if isinstance(value, (list, tuple, set)) else [value]

    for candidate in candidates:
        if candidate is None or isinstance(candidate, (int, float)):
            continue
        if isinstance(candidate, datetime):
            return candidate.strftime("%Y-%m-%d")

        text = str(candidate).strip()
        if not text or text.lower() in ("none", "null", "0"):
            continue

        if (compact := _parse_compact_date(text)) is not None:
            return compact

        try:
            parsed = date_parser.parse(text, fuzzy=True, ignoretz=True)
            return parsed.strftime("%Y-%m-%d")
        except (ValueError, OverflowError, date_parser.ParserError):
            continue

    return None


def _coerce_str_list(value: Any, *, lower: bool = False) -> List[str]:
    if not value:
        return []
    items = value if isinstance(value, (list, tuple, set)) else [value]
    out: List[str] = []
    for item in items:
        if not item:
            continue
        text = str(item)
        out.append(text.lower() if lower else text)
    return out


def _coerce_status(value: Any) -> Optional[str]:
    if isinstance(value, (list, tuple, set)):
        return ", ".join(str(s) for s in value if s) or None
    return str(value) if value else None


def _whois_socket(domain: str, server: str = "whois.iana.org", timeout: int = 20) -> Optional[str]:
    """Query a WHOIS server directly over TCP/43 (fallback when `whois` cmd is absent)."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        try:
            sock.connect((server, 43))
            sock.sendall(f"{domain}\r\n".encode())
            chunks = []
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                chunks.append(chunk)
            return b"".join(chunks).decode("utf-8", errors="ignore")
        finally:
            sock.close()
    except OSError as exc:
        logger.debug("WHOIS socket %s for %s failed: %s", server, domain, exc)
        return None


def _parse_whois_raw(raw: Optional[str], domain: str) -> Optional[WhoisInfo]:
    """Parse raw WHOIS text into WhoisInfo (best-effort, multiple TLDs)."""
    if not raw or len(raw) < 10:
        return None
    info = WhoisInfo(domain=domain)
    for line in raw.lower().split("\n"):
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        key, val = key.strip(), val.strip()
        if not val:
            continue
        if any(hint in key for hint in _DATE_KEY_HINTS_CREATION):
            info.creation_date = _parse_compact_date(val) or _normalize_date(val)
        elif any(hint in key for hint in _DATE_KEY_HINTS_EXPIRATION):
            info.expiration_date = _parse_compact_date(val) or _normalize_date(val)
        elif "registrar" in key and not info.registrar:
            info.registrar = val
        elif any(hint in key for hint in _NS_KEY_HINTS):
            ns = val.rstrip(".").strip()
            if ns and ns not in info.name_servers:
                info.name_servers.append(ns)
        elif "status" in key and not info.status:
            info.status = val
            if "ok-until" in val and not info.expiration_date:
                info.expiration_date = _parse_compact_date(val)
    return info


def _whois_raw_fallback(domain: str) -> Optional[WhoisInfo]:
    """Try OS `whois` first, then fall back to direct socket queries."""
    raw: Optional[str] = None
    whois_cmd = shutil.which("whois")
    if whois_cmd:
        try:
            result = subprocess.run(
                [whois_cmd, domain],
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
            raw = (result.stdout or "") + (result.stderr or "")
        except (subprocess.TimeoutExpired, OSError) as exc:
            logger.debug("whois subprocess for %s failed: %s", domain, exc)

    if not raw or len(raw) < 50:
        tld = domain.rsplit(".", 1)[-1] if "." in domain else ""
        server = _TLD_WHOIS_SERVERS.get(tld, "whois.iana.org")
        timeout = _RAW_WHOIS_TIMEOUT_UA if tld == "ua" else _RAW_WHOIS_TIMEOUT_DEFAULT
        raw = _whois_socket(domain, server, timeout)
        if not raw and server != "whois.iana.org":
            raw = _whois_socket(domain, "whois.iana.org", timeout)

    return _parse_whois_raw(raw, domain) if raw else None


def _cache_get(cache_key: str) -> Optional[Dict[str, Any]]:
    try:
        from src.services.cache_service import get  # local import: cache is optional

        cached = get(cache_key)
        if isinstance(cached, dict):
            return cached
    except Exception as exc:
        logger.debug("WHOIS cache read failed: %s", exc)
    return None


def _cache_set(cache_key: str, info: WhoisInfo) -> None:
    try:
        from src.services.cache_service import TTL_WHOIS, set as cache_set

        cache_set(cache_key, info.model_dump(), TTL_WHOIS)
    except Exception as exc:
        logger.debug("WHOIS cache write failed: %s", exc)


def _build_info_from_python_whois(record: Any, domain: str) -> WhoisInfo:
    registrar = getattr(record, "registrar", None)
    return WhoisInfo(
        domain=domain,
        registrar=str(registrar) if registrar else None,
        creation_date=_normalize_date(getattr(record, "creation_date", None)),
        expiration_date=_normalize_date(getattr(record, "expiration_date", None)),
        name_servers=_coerce_str_list(getattr(record, "name_servers", None), lower=True),
        emails=_coerce_str_list(getattr(record, "emails", None)),
        status=_coerce_status(getattr(record, "status", None)),
    )


class WhoisEnricher(AbstractEnricher):
    """Enricher for WHOIS registration data."""

    name = "whois"

    def enrich(self, domain: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        cache_key = f"whois:{domain}"
        if (cached := _cache_get(cache_key)) is not None:
            return {"whois_info": WhoisInfo(**cached)}

        record = self._lookup_python_whois(domain)
        if record is None:
            return self._fallback_or_error(domain, cache_key, last_error="WHOIS lookup failed")

        try:
            info = _build_info_from_python_whois(record, domain)
        except Exception as exc:
            return self._fallback_or_error(domain, cache_key, last_error=str(exc))

        _cache_set(cache_key, info)
        return {"whois_info": info}

    def _lookup_python_whois(self, domain: str) -> Optional[Any]:
        old_timeout = socket.getdefaulttimeout()
        socket.setdefaulttimeout(_PYTHON_WHOIS_TIMEOUT_SECONDS)
        try:
            return whois.whois(domain)
        except Exception as exc:
            logger.debug("python-whois failed for %s: %s", domain, exc)
            return None
        finally:
            socket.setdefaulttimeout(old_timeout)

    def _fallback_or_error(
        self,
        domain: str,
        cache_key: str,
        *,
        last_error: str,
    ) -> Dict[str, Any]:
        fallback = _whois_raw_fallback(domain)
        if fallback and (fallback.creation_date or fallback.expiration_date or fallback.name_servers):
            _cache_set(cache_key, fallback)
            return {"whois_info": fallback}
        return {
            "whois_info": WhoisInfo(domain=domain, error=f"WHOIS lookup failed: {last_error}"),
        }
