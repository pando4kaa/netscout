"""
Pydantic models - single source of truth for data schemas.
"""

from .dns import DNSInfo, EmailSecurityInfo, MXRecord
from .port import OpenPort, PortScanResult
from .risk import Alert, RiskLevel
from .scan import (
    RiskBreakdownItem,
    RiskFactorItem,
    RiskGroupItem,
    ScanRequest,
    ScanResult,
    ScanSummary,
)
from .ssl import CertificateInfo, SslInfo
from .subdomain import SubdomainInfo
from .tech import SecurityHeadersInfo, TechStack
from .whois import WhoisInfo

__all__ = [
    "DNSInfo",
    "MXRecord",
    "EmailSecurityInfo",
    "WhoisInfo",
    "SubdomainInfo",
    "SslInfo",
    "CertificateInfo",
    "PortScanResult",
    "OpenPort",
    "Alert",
    "RiskLevel",
    "TechStack",
    "SecurityHeadersInfo",
    "ScanResult",
    "ScanRequest",
    "ScanSummary",
    "RiskBreakdownItem",
    "RiskFactorItem",
    "RiskGroupItem",
]
