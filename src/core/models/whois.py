"""
WHOIS information models.
"""

from pydantic import BaseModel, Field
from typing import List, Optional


class WhoisInfo(BaseModel):
    """WHOIS registration information for a domain."""

    domain: str
    registrar: Optional[str] = None
    creation_date: Optional[str] = None
    expiration_date: Optional[str] = None
    name_servers: List[str] = Field(default_factory=list)
    emails: List[str] = Field(default_factory=list)
    status: Optional[str] = None
    error: Optional[str] = None
