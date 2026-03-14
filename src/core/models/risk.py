"""
Risk and alert models.
"""

from enum import Enum
from pydantic import BaseModel, Field
from typing import List, Optional


class RiskLevel(str, Enum):
    """Risk severity level."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class Alert(BaseModel):
    """Security alert / risk finding."""

    type: str  # e.g. "subdomain_takeover", "open_port", "expired_ssl"
    level: RiskLevel
    message: str
    target: Optional[str] = None  # subdomain, IP, etc.
    details: Optional[dict] = None
