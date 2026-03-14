"""
Risk detection — Subdomain Takeover, open ports, expired SSL, outdated tech, etc.
"""

import re
import requests
from typing import Any, Dict, List, Optional, Tuple

from src.core.models import Alert, RiskLevel, DNSInfo, SslInfo, PortScanResult, OpenPort
from src.config.settings import HTTP_TIMEOUT, USER_AGENT

# Known vulnerable versions: (software, version) -> CVE or description
OUTDATED_VERSIONS: List[Tuple[str, str, str]] = [
    ("nginx", "1.18.0", "CVE-2022-41741, CVE-2022-41742"),
    ("nginx", "1.16.1", "Multiple CVEs"),
    ("apache", "2.4.49", "CVE-2021-41773 path traversal"),
    ("apache", "2.4.50", "CVE-2021-42013"),
    ("openssh", "8.0", "CVE-2020-15778"),
    ("openssh", "7.4", "Multiple CVEs"),
]

# CNAME targets that are common Subdomain Takeover candidates
TAKEOVER_TARGETS = [
    "github.io",
    "herokuapp.com",
    "azurewebsites.net",
    "cloudapp.net",
    "s3.amazonaws.com",
    "s3-website",
    "elasticbeanstalk.com",
    "fastly.net",
    "ghost.io",
    "surge.sh",
    "pantheon.io",
    "zendesk.com",
    "cargo.site",
    "feedpress.me",
    "helpjuice.com",
    "helpscoutdocs.com",
    "myjetbrains.com",
    "readme.io",
    "bitbucket.io",
]

# Ports that may indicate higher risk when exposed
RISKY_PORTS = {
    21: ("FTP", RiskLevel.MEDIUM),
    22: ("SSH", RiskLevel.LOW),
    3306: ("MySQL", RiskLevel.HIGH),
    5432: ("PostgreSQL", RiskLevel.HIGH),
    27017: ("MongoDB", RiskLevel.HIGH),
    6379: ("Redis", RiskLevel.HIGH),
    3389: ("RDP", RiskLevel.HIGH),
}


def _check_takeover(subdomain: str, cname: str) -> bool:
    """Check if subdomain might be vulnerable to takeover."""
    cname_lower = cname.lower()
    for target in TAKEOVER_TARGETS:
        if target in cname_lower:
            try:
                resp = requests.get(
                    f"https://{subdomain}",
                    headers={"User-Agent": USER_AGENT},
                    timeout=HTTP_TIMEOUT,
                    allow_redirects=False,
                )
                if resp.status_code == 404:
                    return True
            except Exception:
                pass
            try:
                resp = requests.get(
                    f"http://{subdomain}",
                    headers={"User-Agent": USER_AGENT},
                    timeout=HTTP_TIMEOUT,
                    allow_redirects=False,
                )
                if resp.status_code == 404:
                    return True
            except Exception:
                pass
    return False


def detect_subdomain_takeover(
    subdomains: List[str],
    dns_info: Optional[DNSInfo],
) -> List[Alert]:
    """Check for potential Subdomain Takeover."""
    alerts: List[Alert] = []
    if not dns_info or not dns_info.cname_records:
        return alerts

    # Simplified: check root domain CNAME
    for cname in dns_info.cname_records:
        for target in TAKEOVER_TARGETS:
            if target in cname.lower():
                alerts.append(
                    Alert(
                        type="subdomain_takeover",
                        level=RiskLevel.MEDIUM,
                        message=f"CNAME points to {target} — verify service is configured",
                        target=dns_info.domain,
                        details={"cname": cname},
                    )
                )
                break

    return alerts


def detect_dmarc_risks(dns_info: Optional[DNSInfo]) -> List[Alert]:
    """Alert when DMARC is absent (domain can be spoofed for phishing)."""
    alerts: List[Alert] = []
    if not dns_info or not dns_info.mx_records:
        return alerts
    email_sec = getattr(dns_info, "email_security", None)
    if email_sec and getattr(email_sec, "dmarc_present", False) is True:
        return alerts
    alerts.append(
        Alert(
            type="missing_dmarc",
            level=RiskLevel.MEDIUM,
            message="DMARC record absent — domain can be spoofed for phishing",
            target=dns_info.domain,
            details={"mx_count": len(dns_info.mx_records)},
        )
    )
    return alerts


def detect_ssl_risks(ssl_info: Optional[SslInfo]) -> List[Alert]:
    """Detect expired or expiring SSL certificates."""
    alerts: List[Alert] = []
    if not ssl_info or not ssl_info.certificates:
        return alerts

    for cert in ssl_info.certificates:
        if cert.is_expired:
            alerts.append(
                Alert(
                    type="expired_ssl",
                    level=RiskLevel.MEDIUM,
                    message=f"Expired certificate for {cert.host}",
                    target=cert.host,
                )
            )

    return alerts


def _parse_server_version(server: str) -> Optional[Tuple[str, str]]:
    """Parse Server header to extract software and version. E.g. 'nginx/1.18.0' -> ('nginx', '1.18.0')."""
    if not server or not isinstance(server, str):
        return None
    m = re.search(r"([a-zA-Z0-9_-]+)/([\d.]+)", server, re.I)
    if m:
        return (m.group(1).lower(), m.group(2))
    return None


def detect_outdated_tech(tech_stack: Optional[Dict[str, Any]]) -> List[Alert]:
    """Detect outdated/vulnerable technology versions from Server headers."""
    alerts: List[Alert] = []
    if not tech_stack:
        return alerts

    for url, data in tech_stack.items():
        if not isinstance(data, dict):
            continue
        server = data.get("server") or data.get("Server")
        if not server:
            continue
        parsed = _parse_server_version(str(server))
        if not parsed:
            continue
        software, version = parsed
        for out_soft, out_ver, desc in OUTDATED_VERSIONS:
            if out_soft in software and version.strip() == out_ver:
                alerts.append(
                    Alert(
                        type="outdated_tech",
                        level=RiskLevel.MEDIUM,
                        message=f"Outdated {software} {version} on {url}: {desc}",
                        target=url,
                        details={"server": server, "software": software, "version": version},
                    )
                )
                break

    return alerts


def detect_abuseipdb_risks(external_apis: Optional[Dict[str, Any]]) -> List[Alert]:
    """Alert on IPs with high AbuseIPDB abuse confidence score."""
    alerts: List[Alert] = []
    abuse = (external_apis or {}).get("abuseipdb", {}) or {}
    ips_data = abuse.get("ips") or {}
    for ip, info in ips_data.items():
        if not isinstance(info, dict):
            continue
        score = info.get("abuse_score")
        if score is not None and score >= 50:
            level = RiskLevel.HIGH if score >= 75 else RiskLevel.MEDIUM
            reports = info.get("total_reports") or 0
            alerts.append(
                Alert(
                    type="abuseipdb",
                    level=level,
                    message=f"IP {ip} has AbuseIPDB score {score}% ({reports} reports)",
                    target=ip,
                    details={"abuse_score": score, "total_reports": reports},
                )
            )
    return alerts


def detect_security_headers_risks(tech_stack: Optional[Dict[str, Any]]) -> List[Alert]:
    """Alert when key security headers (HSTS, X-Frame-Options) are absent."""
    alerts: List[Alert] = []
    if not tech_stack:
        return alerts
    for _url, data in tech_stack.items():
        if not isinstance(data, dict):
            continue
        sec = data.get("security_headers")
        if not sec:
            continue
        missing: List[str] = []
        if not sec.get("strict_transport_security"):
            missing.append("HSTS")
        if not sec.get("x_frame_options"):
            missing.append("X-Frame-Options")
        if missing:
            alerts.append(
                Alert(
                    type="missing_security_headers",
                    level=RiskLevel.LOW,
                    message=f"Missing security headers: {', '.join(missing)} — risk of downgrade/clickjacking",
                    target=_url,
                    details={"missing": missing},
                )
            )
        break  # check main URL only
    return alerts


def detect_ssllabs_risks(external_apis: Optional[Dict[str, Any]]) -> List[Alert]:
    """Alert when SSL Labs reports weak TLS protocols (TLS 1.0, TLS 1.1, SSLv3)."""
    alerts: List[Alert] = []
    ssllabs = (external_apis or {}).get("ssllabs") or {}
    if not ssllabs.get("has_weak_protocols"):
        return alerts
    weak = ssllabs.get("weak_protocols") or []
    alerts.append(
        Alert(
            type="weak_tls",
            level=RiskLevel.MEDIUM,
            message=f"Weak TLS protocols: {', '.join(weak)} — vulnerable to downgrade attacks",
            target=ssllabs.get("domain"),
            details={"weak_protocols": weak},
        )
    )
    return alerts


def detect_phishtank_risks(external_apis: Optional[Dict[str, Any]]) -> List[Alert]:
    """Alert if domain is in PhishTank phishing database."""
    alerts: List[Alert] = []
    pt = (external_apis or {}).get("phishtank") or {}
    if pt.get("in_database"):
        url = pt.get("url", "domain")
        alerts.append(
            Alert(
                type="phishtank",
                level=RiskLevel.HIGH,
                message=f"Domain/URL {url} is in PhishTank phishing database",
                target=url,
                details={"phish_id": pt.get("phish_id"), "phish_detail_page": pt.get("phish_detail_page")},
            )
        )
    return alerts


def detect_pulsedive_risks(external_apis: Optional[Dict[str, Any]]) -> List[Alert]:
    """Alert if Pulsedive reports high/critical risk."""
    alerts: List[Alert] = []
    pd = (external_apis or {}).get("pulsedive") or {}
    risk = (pd.get("risk") or "").lower()
    if risk in ("high", "critical"):
        domain = pd.get("domain", "domain")
        alerts.append(
            Alert(
                type="pulsedive",
                level=RiskLevel.HIGH if risk == "critical" else RiskLevel.MEDIUM,
                message=f"Pulsedive risk '{risk}' for {domain}: {pd.get('risk_recommendation', 'Review recommended')}",
                target=domain,
                details={"risk": risk, "threats": pd.get("threats", [])},
            )
        )
    return alerts


def detect_criminalip_risks(external_apis: Optional[Dict[str, Any]]) -> List[Alert]:
    """Alert if Criminal IP reports domain as unsafe or high risk."""
    alerts: List[Alert] = []
    ci = (external_apis or {}).get("criminalip") or {}
    domain = ci.get("domain", "domain")
    if ci.get("is_safe") is False:
        alerts.append(
            Alert(
                type="criminalip",
                level=RiskLevel.MEDIUM,
                message=f"Criminal IP marks {domain} as unsafe",
                target=domain,
                details={"risk_score": ci.get("risk_score")},
            )
        )
    elif isinstance(ci.get("risk_score"), (int, float)) and ci["risk_score"] >= 70:
        alerts.append(
            Alert(
                type="criminalip",
                level=RiskLevel.HIGH,
                message=f"Criminal IP risk score {ci['risk_score']} for {domain}",
                target=domain,
                details={"risk_score": ci["risk_score"]},
            )
        )
    return alerts


def detect_port_risks(port_scan: List[PortScanResult]) -> List[Alert]:
    """Detect risky open ports."""
    alerts: List[Alert] = []
    for result in port_scan:
        for port_info in result.open_ports:
            if port_info.port in RISKY_PORTS:
                service, level = RISKY_PORTS[port_info.port]
                alerts.append(
                    Alert(
                        type="open_port",
                        level=level,
                        message=f"Open {service} port {port_info.port} on {result.ip}",
                        target=result.ip,
                        details={"port": port_info.port, "service": service},
                    )
                )

    return alerts


# Risk score weights: HIGH=10, MEDIUM=5, LOW=1
RISK_WEIGHTS = {RiskLevel.HIGH: 10, RiskLevel.MEDIUM: 5, RiskLevel.LOW: 1}


def compute_risk_score(alerts: List[Alert]) -> int:
    """Compute total risk score from alerts (sum of weights)."""
    return sum(RISK_WEIGHTS.get(a.level, 1) for a in alerts)


def run_risk_analysis(
    dns_info: Optional[DNSInfo],
    ssl_info: Optional[SslInfo],
    port_scan: List[PortScanResult],
    subdomains: List[str],
    tech_stack: Optional[Dict[str, Any]] = None,
    external_apis: Optional[Dict[str, Any]] = None,
) -> Tuple[List[Alert], int]:
    """Run all risk checks and return (alerts, risk_score)."""
    alerts: List[Alert] = []
    alerts.extend(detect_subdomain_takeover(subdomains, dns_info))
    alerts.extend(detect_dmarc_risks(dns_info))
    alerts.extend(detect_ssl_risks(ssl_info))
    alerts.extend(detect_port_risks(port_scan))
    alerts.extend(detect_outdated_tech(tech_stack))
    alerts.extend(detect_security_headers_risks(tech_stack))
    alerts.extend(detect_abuseipdb_risks(external_apis))
    alerts.extend(detect_ssllabs_risks(external_apis))
    alerts.extend(detect_phishtank_risks(external_apis))
    alerts.extend(detect_pulsedive_risks(external_apis))
    alerts.extend(detect_criminalip_risks(external_apis))
    score = compute_risk_score(alerts)
    return alerts, score
