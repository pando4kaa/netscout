"""
Technology detection models.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict


class SecurityHeadersInfo(BaseModel):
    """Key security headers for HTTP response."""

    strict_transport_security: Optional[str] = None  # HSTS
    x_frame_options: Optional[str] = None
    content_security_policy: Optional[str] = None
    x_content_type_options: Optional[str] = None
    referrer_policy: Optional[str] = None


class TechStack(BaseModel):
    """Detected technologies for a URL."""

    url: str
    technologies: List[str] = Field(default_factory=list)
    headers: Dict[str, str] = Field(default_factory=dict)
    security_headers: Optional[SecurityHeadersInfo] = None
    server: Optional[str] = None
    x_powered_by: Optional[str] = None
    favicon_hash: Optional[int] = None
    robots_txt: Optional[str] = None
    security_txt: Optional[str] = None
    meta_generator: Optional[str] = None
    meta_cms: Optional[str] = None
    error: Optional[str] = None
