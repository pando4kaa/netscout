"""
SSL certificate models.
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class CertificateInfo(BaseModel):
    """SSL certificate details for a host."""

    host: str
    subject_cn: Optional[str] = None
    issuer: Optional[str] = None
    san: List[str] = Field(default_factory=list)  # Subject Alternative Names
    not_before: Optional[datetime] = None
    not_after: Optional[datetime] = None
    is_expired: bool = False
    error: Optional[str] = None


class SslInfo(BaseModel):
    """Aggregated SSL certificate information."""

    certificates: List[CertificateInfo] = Field(default_factory=list)
    error: Optional[str] = None
