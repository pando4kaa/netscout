"""
Scan Orchestrator — coordinates pipeline and produces ScanResult.
"""

from datetime import datetime
from typing import Callable, Optional

from src.core.models import (
    ScanResult,
    ScanSummary,
    DNSInfo,
    WhoisInfo,
)
from src.core.pipeline import EnricherPipeline, ProgressCallback
from src.config.settings import (
    SHODAN_API_KEY,
    VIRUSTOTAL_API_KEY,
    CENSYS_API_TOKEN,
    CENSYS_API_ID,
    CENSYS_API_SECRET,
    ALIENVAULT_OTX_API_KEY,
)
from src.enrichers.dns import DnsEnricher
from src.enrichers.whois import WhoisEnricher
from src.enrichers.subdomain import SubdomainEnricher
from src.enrichers.ssl import SslEnricher
from src.enrichers.port import PortEnricher
from src.enrichers.tech import TechEnricher
from src.enrichers.external_apis import ExternalApiEnricher
from src.enrichers.geoip import GeoipEnricher
from src.utils.validators import is_valid_domain, normalize_domain
from src.analysis.normalizer import normalize_domains
from src.analysis.risk import run_risk_analysis
from src.analysis.correlation import build_correlation_summary


def _build_pipeline(on_progress: Optional[ProgressCallback] = None) -> EnricherPipeline:
    """Build default pipeline with base enrichers."""
    pipe = (
        EnricherPipeline(on_progress=on_progress)
        .add_enricher(DnsEnricher())
        .add_enricher(WhoisEnricher())
        .add_enricher(SubdomainEnricher(enable_bruteforce=False))
        .add_enricher(SslEnricher())
        .add_enricher(PortEnricher())
        .add_enricher(TechEnricher())
    )
    # External APIs: always add (URLScan, BGPView, ThreatCrowd are free; others need keys)
    pipe = pipe.add_enricher(ExternalApiEnricher())
    pipe = pipe.add_enricher(GeoipEnricher())
    return pipe


def scan_domain(
    domain: str,
    on_progress: Optional[ProgressCallback] = None,
    pipeline: Optional[EnricherPipeline] = None,
) -> ScanResult:
    """
    Perform full domain scan using enricher pipeline.

    Args:
        domain: Domain to scan
        on_progress: Optional callback (stage, progress_percent, message)
        pipeline: Optional custom pipeline (uses default if None)

    Returns:
        ScanResult with all collected data
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
        from src.analysis.normalizer import normalize_dns_info
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

    correlation = build_correlation_summary(subdomains, dns_info, data.get("ssl_info"), domain)

    if on_progress:
        on_progress("analysis", 97, "Building scan summary...")

    total_ips = correlation.get("unique_ips", 0) if correlation else 0
    if total_ips == 0 and dns_info and hasattr(dns_info, "a_records"):
        total_ips = len(dns_info.a_records)

    total_dns = 0
    if dns_info:
        total_dns = (
            len(getattr(dns_info, "a_records", []) or [])
            + len(getattr(dns_info, "aaaa_records", []) or [])
            + len(getattr(dns_info, "mx_records", []) or [])
            + len(getattr(dns_info, "txt_records", []) or [])
            + len(getattr(dns_info, "ns_records", []) or [])
            + len(getattr(dns_info, "cname_records", []) or [])
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
        summary=ScanSummary(
            total_subdomains=len(subdomains),
            total_ip_addresses=total_ips,
            total_dns_records=total_dns,
            total_alerts=len(alerts),
            risk_score=risk_score,
            risk_composite=risk_composite,
            risk_breakdown=risk_breakdown,
        ),
    )
