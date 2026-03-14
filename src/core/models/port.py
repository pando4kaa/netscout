"""
Port scan models.
"""

from pydantic import BaseModel, Field
from typing import List, Optional


class OpenPort(BaseModel):
    """Open port with optional banner."""

    port: int
    protocol: str = "tcp"
    banner: Optional[str] = None
    service: Optional[str] = None


class PortScanResult(BaseModel):
    """Port scan results for an IP."""

    ip: str
    open_ports: List[OpenPort] = Field(default_factory=list)
    error: Optional[str] = None
