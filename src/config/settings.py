"""
Configuration settings for NetScout
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root (settings.py is in src/config/)
_project_root = Path(__file__).resolve().parent.parent.parent
load_dotenv(_project_root / ".env")

# DNS settings
DNS_TIMEOUT = 5  # seconds
DNS_RETRIES = 3

# HTTP settings
HTTP_TIMEOUT = 10
HTTP_RETRIES = 3
# Set to false to skip SSL verification (useful when target uses self-signed or incomplete cert chain)
HTTP_VERIFY_SSL = os.getenv("HTTP_VERIFY_SSL", "true").lower() in ("true", "1", "yes")
# Port scan timeout per port (seconds); lower = faster but may miss slow hosts
PORT_SCAN_TIMEOUT = float(os.getenv("PORT_SCAN_TIMEOUT", "3"))
CRTSH_TIMEOUT = int(os.getenv("CRTSH_TIMEOUT", "60"))
USER_AGENT = "NetScout OSINT Scanner 1.0"

# Output settings
RESULTS_DIR = "results"
LOG_LEVEL = "INFO"

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
# Censys: Platform API (Personal Access Token) or Legacy (API ID + Secret)
# New: CENSYS_API_TOKEN from https://accounts.censys.io/settings/personal-access-tokens
# Legacy: CENSYS_API_ID + CENSYS_API_SECRET from https://search.censys.io/account
CENSYS_API_TOKEN = os.getenv("CENSYS_API_TOKEN", "")
CENSYS_API_ID = os.getenv("CENSYS_API_ID", "")
CENSYS_API_SECRET = os.getenv("CENSYS_API_SECRET", "")

# PostgreSQL (required)
DATABASE_URL = os.getenv("DATABASE_URL")

# Auth
JWT_SECRET = os.getenv("JWT_SECRET")

# Neo4j graph database (optional)
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "")

# Redis (optional, for cache and rate limiting)
REDIS_URL = os.getenv("REDIS_URL", "")
