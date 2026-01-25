"""
Configuration settings for NetScout
"""

import os
from dotenv import load_dotenv

load_dotenv()

# DNS settings
DNS_TIMEOUT = 5  # seconds
DNS_RETRIES = 3

# HTTP settings
HTTP_TIMEOUT = 10
HTTP_RETRIES = 3
USER_AGENT = "NetScout OSINT Scanner 1.0"

# Output settings
RESULTS_DIR = "results"
LOG_LEVEL = "INFO"

# API keys (if needed later)
SHODAN_API_KEY = os.getenv("SHODAN_API_KEY", "")
VIRUSTOTAL_API_KEY = os.getenv("VIRUSTOTAL_API_KEY", "")
CENSYS_API_KEY = os.getenv("CENSYS_API_KEY", "")
