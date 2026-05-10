"""
Configuration settings for NetScout.

All values that may differ between environments are read from environment
variables (loaded from `.env` at project root). Constants without env mapping
are intentionally hard-coded defaults.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(_PROJECT_ROOT / ".env")


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("true", "1", "yes", "on")


# DNS settings
DNS_TIMEOUT = 5  # seconds
DNS_RETRIES = 3

# HTTP settings
HTTP_TIMEOUT = 10
HTTP_RETRIES = 3
# Set HTTP_VERIFY_SSL=false to skip TLS verification (e.g. self-signed targets).
HTTP_VERIFY_SSL = _env_bool("HTTP_VERIFY_SSL", default=True)
# Per-port TCP connect timeout for the port scanner.
PORT_SCAN_TIMEOUT = float(os.getenv("PORT_SCAN_TIMEOUT", "3"))
CRTSH_TIMEOUT = int(os.getenv("CRTSH_TIMEOUT", "60"))
USER_AGENT = "NetScout OSINT Scanner 1.0"

# Output settings
RESULTS_DIR = "results"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# API keys for external OSINT sources
SHODAN_API_KEY = os.getenv("SHODAN_API_KEY", "")
VIRUSTOTAL_API_KEY = os.getenv("VIRUSTOTAL_API_KEY", "")
ALIENVAULT_OTX_API_KEY = os.getenv("ALIENVAULT_OTX_API_KEY", "")
ABUSEIPDB_API_KEY = os.getenv("ABUSEIPDB_API_KEY", "")
SECURITYTRAILS_API_KEY = os.getenv("SECURITYTRAILS_API_KEY", "")
CERTSPOTTER_API_TOKEN = os.getenv("CERTSPOTTER_API_TOKEN", "")
ZOOMEYE_API_KEY = os.getenv("ZOOMEYE_API_KEY", "")
PHISHTANK_APP_KEY = os.getenv("PHISHTANK_APP_KEY", "")
CRIMINALIP_API_KEY = os.getenv("CRIMINALIP_API_KEY", "")
PULSEDIVE_API_KEY = os.getenv("PULSEDIVE_API_KEY", "")
NVD_API_KEY = (os.getenv("NVD_API_KEY") or "").strip()
# Censys: Platform API (Personal Access Token) or Legacy (API ID + Secret).
#   New:    CENSYS_API_TOKEN from https://accounts.censys.io/settings/personal-access-tokens
#   Legacy: CENSYS_API_ID + CENSYS_API_SECRET from https://search.censys.io/account
CENSYS_API_TOKEN = os.getenv("CENSYS_API_TOKEN", "")
CENSYS_API_ID = os.getenv("CENSYS_API_ID", "")
CENSYS_API_SECRET = os.getenv("CENSYS_API_SECRET", "")

# PostgreSQL (required for backend)
DATABASE_URL = os.getenv("DATABASE_URL")

# Auth
JWT_SECRET = os.getenv("JWT_SECRET")

# Neo4j graph database (optional)
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "")

# Redis (optional, for cache and rate limiting)
REDIS_URL = os.getenv("REDIS_URL", "")

# Email notifications (optional; if not set, no emails sent)
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", "NetScout <noreply@netscout.local>")
SMTP_USE_TLS = _env_bool("SMTP_USE_TLS", default=True)
# Public app URL used in outbound emails (unsubscribe links, deep links).
APP_URL = os.getenv("APP_URL", "http://localhost:5173")
