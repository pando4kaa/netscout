"""
DNS record models.
"""

from pydantic import BaseModel, Field
from typing import Dict, List, Optional


class EmailSecurityInfo(BaseModel):
    """Parsed SPF, DKIM, DMARC from TXT records."""

    spf_present: bool = False
    spf_record: Optional[str] = None
    dmarc_present: bool = False
    dmarc_record: Optional[str] = None
    dmarc_policy: Optional[str] = None  # none, quarantine, reject
    dkim_hints: List[str] = Field(default_factory=list)  # TXT records starting with v=DKIM1


class MXRecord(BaseModel):
    """MX record with priority and host."""

    priority: int
    host: str


class DNSInfo(BaseModel):
    """DNS records for a domain."""

    domain: str
    a_records: List[str] = Field(default_factory=list)
    aaaa_records: List[str] = Field(default_factory=list)
    mx_records: List[MXRecord] = Field(default_factory=list)
    txt_records: List[str] = Field(default_factory=list)
    ns_records: List[str] = Field(default_factory=list)
    cname_records: List[str] = Field(default_factory=list)
    soa_records: List[str] = Field(default_factory=list)
    ptr_records: Dict[str, str] = Field(default_factory=dict)  # ip -> hostname (reverse DNS)
    zone_transfer_attempted: bool = False
    zone_transfer_available: bool = False
    zone_transfer_error: Optional[str] = None
    email_security: Optional[EmailSecurityInfo] = None
    error: Optional[str] = None
