"""
Scan Orchestrator - coordinates the enricher pipeline and produces a ScanResult.
"""

from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional

from src.analysis.correlation import build_correlation_summary
from src.analysis.normalizer import normalize_dns_info, normalize_domains
from src.analysis.risk import run_risk_analysis
from src.analysis.risk_scoring_v3 import compute_risk_v3
from src.core.models import ScanResult, ScanSummary
from src.core.pipeline import EnricherPipeline, ProgressCallback
from src.enrichers.dns import DnsEnricher
from src.enrichers.external_apis import ExternalApiEnricher
from src.enrichers.geoip import GeoipEnricher
from src.enrichers.port import PortEnricher
from src.enrichers.ssl import SslEnricher
from src.enrichers.subdomain import SubdomainEnricher
from src.enrichers.tech import TechEnricher
from src.enrichers.whois import WhoisEnricher
from src.utils.validators import is_valid_domain, normalize_domain

# DNS record-list attributes summed into total_dns_records.
_DNS_RECORD_FIELDS = (
    "a_records",
    "aaaa_records",
    "mx_records",
    "txt_records",
    "ns_records",
    "cname_records",
)


def _build_pipeline(on_progress: Optional[ProgressCallback] = None) -> EnricherPipeline:
    """Build the default enrichment pipeline with all stock enrichers."""
    return (
        EnricherPipeline(on_progress=on_progress)
        .add_enricher(DnsEnricher())
        .add_enricher(WhoisEnricher())
        .add_enricher(SubdomainEnricher(enable_bruteforce=False))
        .add_enricher(SslEnricher())
        .add_enricher(PortEnricher())
        .add_enricher(TechEnricher())
        .add_enricher(ExternalApiEnricher())
        .add_enricher(GeoipEnricher())
    )


def _count_dns_records(dns_info: Any) -> int:
    """Sum the lengths of all DNS record-list attributes on dns_info."""
    if not dns_info:
        return 0
    return sum(len(getattr(dns_info, name, []) or []) for name in _DNS_RECORD_FIELDS)


def _resolve_total_ips(correlation: Optional[Dict[str, Any]], dns_info: Any) -> int:
    """Prefer correlation's unique IP count; fall back to A-record count."""
    total = correlation.get("unique_ips", 0) if correlation else 0
    if total == 0 and dns_info and hasattr(dns_info, "a_records"):
        total = len(dns_info.a_records)
    return total


def _build_summary(
    *,
    subdomains: Iterable[str],
    dns_info: Any,
    correlation: Optional[Dict[str, Any]],
    alerts: List[Any],
    risk_score: int,
    risk_composite: Optional[float],
    risk_breakdown: List[Any],
    risk_v3: Dict[str, Any],
) -> ScanSummary:
    subdomain_list = list(subdomains)
    return ScanSummary(
        total_subdomains=len(subdomain_list),
        total_ip_addresses=_resolve_total_ips(correlation, dns_info),
        total_dns_records=_count_dns_records(dns_info),
        total_alerts=len(alerts),
        risk_score=risk_score,
        risk_composite=risk_composite,
        risk_breakdown=risk_breakdown,
        risk_overall=risk_v3.get("risk_overall"),
        risk_level=risk_v3.get("risk_level"),
        risk_method=risk_v3.get("risk_method"),
        max_severity=risk_v3.get("max_severity"),
        exposure_score=risk_v3.get("exposure_score"),
        confidence=risk_v3.get("confidence"),
        risk_groups=risk_v3.get("risk_groups") or [],
    )


def scan_domain(
    domain: str,
    on_progress: Optional[ProgressCallback] = None,
    pipeline: Optional[EnricherPipeline] = None,
) -> ScanResult:
    """
    Perform a full domain scan via the enricher pipeline and risk analysis.

    Args:
        domain: Domain to scan (will be normalized and validated).
        on_progress: Optional callback `(stage, percent, message)`.
        pipeline: Custom pipeline; if None, the default is used.

    Returns:
        Fully populated ScanResult.
    """
    domain = normalize_domain(domain)
    if not is_valid_domain(domain):
        raise ValueError(f"Invalid domain: {domain}")

    pipe = pipeline or _build_pipeline(on_progress)
    data = pipe.run(domain)

    if on_progress:
        on_progress("analysis", 92, "Analyzing risks and correlations...")

    dns_info = data.get("dns_info")
    whois_info = data.get("whois_info")
    subdomains = normalize_domains(data.get("subdomains") or [])

    if dns_info:
        dns_info = normalize_dns_info(dns_info)

    alerts, risk_score, risk_composite, risk_breakdown = run_risk_analysis(
        dns_info=dns_info,
        ssl_info=data.get("ssl_info"),
        port_scan=data.get("port_scan") or [],
        subdomains=subdomains,
        tech_stack=data.get("tech_stack"),
        external_apis=data.get("external_apis"),
        apex_domain=domain,
    )
    risk_v3 = compute_risk_v3(alerts, domain)
    correlation = build_correlation_summary(subdomains, dns_info, data.get("ssl_info"), domain)

    if on_progress:
        on_progress("analysis", 97, "Building scan summary...")

    summary = _build_summary(
        subdomains=subdomains,
        dns_info=dns_info,
        correlation=correlation,
        alerts=alerts,
        risk_score=risk_score,
        risk_composite=risk_composite,
        risk_breakdown=risk_breakdown,
        risk_v3=risk_v3,
    )

    return ScanResult(
        target_domain=domain,
        scan_date=datetime.utcnow(),
        dns_info=dns_info,
        whois_info=whois_info,
        subdomains=subdomains,
        ssl_info=data.get("ssl_info"),
        port_scan=data.get("port_scan") or [],
        tech_stack=data.get("tech_stack"),
        external_apis=data.get("external_apis"),
        geoip_info=data.get("geoip_info"),
        correlation=correlation,
        alerts=alerts,
        summary=summary,
    )
