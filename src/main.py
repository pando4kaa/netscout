"""
Main entry point for NetScout OSINT system.
"""

import sys
from src.core.orchestrator import scan_domain


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python main.py <domain>")
        print("Example: python main.py example.com")
        sys.exit(1)

    domain = sys.argv[1]

    def on_progress(stage: str, progress: int, message: str):
        print(f"  [{progress}%] {stage}: {message}")

    try:
        results = scan_domain(domain, on_progress=on_progress)
        print("\n" + "=" * 50)
        print("Scan Results:")
        print("=" * 50)
        print(f"Domain: {results.target_domain}")
        print(f"Subdomains found: {results.summary.total_subdomains}")
        print(f"IP addresses: {results.summary.total_ip_addresses}")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
