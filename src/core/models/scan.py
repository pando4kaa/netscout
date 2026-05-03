"""
Scan result models.
"""

from datetime import datetime
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

from .dns import DNSInfo
from .whois import WhoisInfo
from .ssl import SslInfo
from .port import PortScanResult
from .risk import Alert


class RiskBreakdownItem(BaseModel):
    """Composite risk contribution for a single alert."""

    type: str
    message: str
    target: Optional[str] = None
    level: str
    severity_score: float
    severity_source: str = "legacy"
    asset_weight: float
    likelihood: float
    contribution: float
    asset_class: Optional[str] = None
    cves: List[Dict[str, Any]] = Field(default_factory=list)


class RiskFactorItem(BaseModel):
    """Explainable factor used by the V3 risk model."""

    name: str
    score: float
    weight: float = 1.0
    weighted_score: float
    rationale: Optional[str] = None


class RiskGroupItem(BaseModel):
    """Grouped risk finding scored with the OWASP-adapted V3 model."""

    group_id: str
    type: str
    title: str
    risk_score: float
    risk_level: str
    affected_assets: int
    representative_targets: List[str] = Field(default_factory=list)
    severity: float
    severity_source: str = "legacy"
    likelihood: float
    impact: float
    exposure_score: float
    exposure_multiplier: float
    confidence: str
    confidence_multiplier: float
    factors: Dict[str, List[RiskFactorItem]] = Field(default_factory=dict)
    cves: List[Dict[str, Any]] = Field(default_factory=list)
    evidence: List[str] = Field(default_factory=list)
    recommendation: Optional[str] = None


class ScanSummary(BaseModel):
    """Summary statistics for a scan."""

    total_subdomains: int = 0
    total_ip_addresses: int = 0
    total_dns_records: int = 0
    total_alerts: int = 0
    risk_score: int = 0
    risk_composite: Optional[float] = None
    risk_breakdown: List[RiskBreakdownItem] = Field(default_factory=list)
    risk_overall: Optional[float] = None
    risk_level: Optional[str] = None
    risk_method: Optional[str] = None
    max_severity: Optional[float] = None
    exposure_score: Optional[float] = None
    confidence: Optional[str] = None
    risk_groups: List[RiskGroupItem] = Field(default_factory=list)


class ScanRequest(BaseModel):
    """Scan request payload."""

    domain: str


class ScanResult(BaseModel):
    """Full scan result."""

    target_domain: str
    scan_date: Optional[datetime] = None
    dns_info: Optional[DNSInfo] = None
    whois_info: Optional[WhoisInfo] = None
    subdomains: List[str] = Field(default_factory=list)
    ssl_info: Optional[SslInfo] = None
    port_scan: List[PortScanResult] = Field(default_factory=list)
    tech_stack: Optional[Dict[str, Any]] = None
    external_apis: Optional[Dict[str, Any]] = None
    geoip_info: Optional[Dict[str, Any]] = None
    correlation: Optional[Dict[str, Any]] = None
    alerts: List[Alert] = Field(default_factory=list)
    summary: ScanSummary = Field(default_factory=ScanSummary)
