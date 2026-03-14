"""
Subdomain models.
"""

from pydantic import BaseModel, Field
from typing import List, Optional


class SubdomainInfo(BaseModel):
    """Subdomain discovery result."""

    subdomains: List[str] = Field(default_factory=list)
    source: Optional[str] = None  # e.g. "crt.sh", "crobat", "bruteforce"
    error: Optional[str] = None
