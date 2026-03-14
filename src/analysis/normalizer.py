"""
Normalizer — lowercase, deduplication, validation.
"""

import re
from typing import List, Optional, Set

from src.core.models import DNSInfo, EmailSecurityInfo, WhoisInfo

# Labels that look like TLD concatenation from crt.sh noise (e.g. comjmce, orgxyz)
_NOISE_LABEL_PATTERN = re.compile(r"^(com|org|net|io)[a-z0-9]{2,}$", re.I)


def _is_noise_subdomain(name: str) -> bool:
    """Filter crt.sh noise: concatenated domains like chasingdownhunger.comjmce.ukma.edu.ua."""
    parts = name.lower().split(".")
    for part in parts[:-1]:  # exclude TLD (ua)
        if _NOISE_LABEL_PATTERN.match(part):
            return True
    return False


def normalize_domains(domains: List[str], filter_noise: bool = True) -> List[str]:
    """Normalize and deduplicate domain list. Optionally filter crt.sh concatenation noise."""
    seen: Set[str] = set()
    result: List[str] = []
    for d in domains:
        n = d.lower().strip().rstrip(".")
        if not n or n in seen:
            continue
        if filter_noise and _is_noise_subdomain(n):
            continue
        seen.add(n)
        result.append(n)
    return sorted(result)


def normalize_ips(ips: List[str]) -> List[str]:
    """Deduplicate IP list."""
    seen: Set[str] = set()
    result: List[str] = []
    for ip in ips:
        ip = ip.strip()
        if ip and ip not in seen:
            seen.add(ip)
            result.append(ip)
    return sorted(result)


def _parse_email_security(txt_records: List[str]) -> Optional[EmailSecurityInfo]:
    """Parse SPF, DKIM, DMARC from TXT records."""
    if not txt_records:
        return None
    spf_record: Optional[str] = None
    dmarc_record: Optional[str] = None
    dmarc_policy: Optional[str] = None
    dkim_hints: List[str] = []
    for txt in txt_records:
        t = str(txt).strip().strip('"')
        if t.startswith("v=spf1 "):
            spf_record = t
        elif t.startswith("v=DMARC1") or "v=DMARC1" in t[:20]:
            dmarc_record = t
            # Extract p= policy: p=none, p=quarantine, p=reject
            m = re.search(r"\bp=(\w+)\b", t, re.I)
            if m:
                dmarc_policy = m.group(1).lower()
        elif "v=DKIM1" in t or "DKIM1" in t:
            dkim_hints.append(t[:200])
    if not (spf_record or dmarc_record or dkim_hints):
        return None
    return EmailSecurityInfo(
        spf_present=bool(spf_record),
        spf_record=spf_record,
        dmarc_present=bool(dmarc_record),
        dmarc_record=dmarc_record,
        dmarc_policy=dmarc_policy,
        dkim_hints=dkim_hints[:5],
    )


def normalize_dns_info(dns: DNSInfo) -> DNSInfo:
    """Normalize DNS info (dedupe records, parse email security)."""
    dns.a_records = normalize_ips(dns.a_records)
    dns.aaaa_records = normalize_ips(dns.aaaa_records)
    dns.txt_records = list(dict.fromkeys(dns.txt_records))
    dns.ns_records = normalize_domains(dns.ns_records)
    dns.cname_records = normalize_domains(dns.cname_records)
    dns.email_security = _parse_email_security(dns.txt_records or [])
    return dns
