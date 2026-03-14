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


class ScanSummary(BaseModel):
    """Summary statistics for a scan."""

    total_subdomains: int = 0
    total_ip_addresses: int = 0
    total_dns_records: int = 0
    total_alerts: int = 0
    risk_score: int = 0


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
