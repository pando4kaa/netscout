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


class ScanSummary(BaseModel):
    """Summary statistics for a scan."""

    total_subdomains: int = 0
    total_ip_addresses: int = 0
    total_dns_records: int = 0
    total_alerts: int = 0
    risk_score: int = 0
    risk_composite: Optional[float] = None
    risk_breakdown: List[RiskBreakdownItem] = Field(default_factory=list)


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
