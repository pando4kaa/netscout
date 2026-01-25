"""
Main entry point for NetScout OSINT system
"""

import sys
from src.modules.dns_scanner import get_dns_records
from src.modules.whois_lookup import get_whois_info
from src.modules.subdomain_finder import find_subdomains_passive
from src.utils.validators import is_valid_domain, normalize_domain


def scan_domain(domain: str) -> dict:
    """
    Performs full domain scan using all available modules.
    
    Args:
        domain: Domain name to scan
    
    Returns:
        Dictionary with scan results
    """
    # Normalize domain
    domain = normalize_domain(domain)
    
    # Validate domain
    if not is_valid_domain(domain):
        raise ValueError(f"Invalid domain: {domain}")
    
    print(f"Scanning domain: {domain}")
    
    results = {
        "target_domain": domain,
        "dns_info": {},
        "whois_info": {},
        "subdomains": []
    }
    
    # DNS scan
    try:
        print("  → Running DNS scan...")
        results["dns_info"] = get_dns_records(domain)
    except Exception as e:
        print(f"  ✗ DNS scan failed: {e}")
        results["dns_info"] = {"error": str(e)}
    
    # WHOIS lookup
    try:
        print("  → Running WHOIS lookup...")
        results["whois_info"] = get_whois_info(domain)
    except Exception as e:
        print(f"  ✗ WHOIS lookup failed: {e}")
        results["whois_info"] = {"error": str(e)}
    
    # Subdomain discovery
    try:
        print("  → Running subdomain discovery...")
        results["subdomains"] = find_subdomains_passive(domain)
    except Exception as e:
        print(f"  ✗ Subdomain discovery failed: {e}")
        results["subdomains"] = []
    
    # Summary
    results["summary"] = {
        "total_subdomains": len(results["subdomains"]),
        "total_ip_addresses": len(results["dns_info"].get("a_records", [])),
    }
    
    return results


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python main.py <domain>")
        print("Example: python main.py example.com")
        sys.exit(1)
    
    domain = sys.argv[1]
    
    try:
        results = scan_domain(domain)
        print("\n" + "="*50)
        print("Scan Results:")
        print("="*50)
        print(f"Domain: {results['target_domain']}")
        print(f"Subdomains found: {results['summary']['total_subdomains']}")
        print(f"IP addresses: {results['summary']['total_ip_addresses']}")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
