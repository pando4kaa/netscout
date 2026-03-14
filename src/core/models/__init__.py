"""
Pydantic models — single source of truth for data schemas.
"""

from .dns import DNSInfo, MXRecord, EmailSecurityInfo
from .whois import WhoisInfo
from .subdomain import SubdomainInfo
from .ssl import SslInfo, CertificateInfo
from .port import PortScanResult, OpenPort
from .risk import Alert, RiskLevel
from .tech import TechStack, SecurityHeadersInfo
from .scan import ScanResult, ScanRequest, ScanSummary

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
]
