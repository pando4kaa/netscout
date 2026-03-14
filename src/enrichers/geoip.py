"""
GeoIP Enricher — geolocation for discovered IPs using GeoLite2 database.
Requires GeoLite2-City.mmdb (download from MaxMind, free signup).
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.enrichers.base import AbstractEnricher

# Resolve paths: backend runs from backend/, CLI from project root
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
GEOIP_DB_PATHS = [
    _PROJECT_ROOT / "data" / "GeoLite2-City.mmdb",
    Path("data/GeoLite2-City.mmdb"),
    Path("GeoLite2-City.mmdb"),
]


def _get_geoip_reader():
    """Return GeoIP2 reader if database exists."""
    for p in GEOIP_DB_PATHS:
        if p.exists():
            try:
                import geoip2.database
                return geoip2.database.Reader(str(p))
            except ImportError:
                return None
    return None


def _lookup_ip(reader, ip: str) -> Optional[Dict[str, Any]]:
    """Lookup IP in GeoIP database."""
    if not reader:
        return None
    try:
        resp = reader.city(ip)
        return {
            "country": resp.country.name,
            "country_code": resp.country.iso_code,
            "city": resp.city.name if resp.city else None,
            "latitude": resp.location.latitude if resp.location else None,
            "longitude": resp.location.longitude if resp.location else None,
        }
    except Exception:
        return None


class GeoipEnricher(AbstractEnricher):
    """Enricher for IP geolocation. Requires GeoLite2-City.mmdb."""

    name = "geoip"

    def enrich(self, domain: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        ips: List[str] = []
        if context and context.get("dns_info"):
            dns = context["dns_info"]
            a_records = getattr(dns, "a_records", None) or (dns.get("a_records") if isinstance(dns, dict) else [])
            ips.extend((a_records or [])[:20])
        if context and context.get("port_scan"):
            for ps in context["port_scan"]:
                ip = ps.ip if hasattr(ps, "ip") else (ps.get("ip") if isinstance(ps, dict) else None)
                if ip and ip not in ips:
                    ips.append(ip)
                if len(ips) >= 20:
                    break

        if not ips:
            return {}

        reader = _get_geoip_reader()
        if not reader:
            return {}

        geoip_info: Dict[str, Dict[str, Any]] = {}
        try:
            with ThreadPoolExecutor(max_workers=min(10, len(ips))) as executor:
                futures = {executor.submit(_lookup_ip, reader, ip): ip for ip in ips}
                for future in as_completed(futures):
                    ip = futures[future]
                    try:
                        info = future.result()
                        if info and (info.get("latitude") or info.get("country")):
                            geoip_info[ip] = info
                    except Exception:
                        pass
        finally:
            try:
                reader.close()
            except Exception:
                pass

        return {"geoip_info": geoip_info} if geoip_info else {}
