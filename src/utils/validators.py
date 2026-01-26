"""
Domain validation utilities
"""

import re


# Regular expression for valid domain name
DOMAIN_PATTERN = re.compile(
    r'^([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$'
)


def is_valid_domain(domain: str) -> bool:
    """
    Checks if a string is a valid domain name.
    
    Args:
        domain: String to validate
    
    Returns:
        True if domain is valid, False otherwise
    """
    if not domain or len(domain) > 253:
        return False
    
    # Remove protocol and www if present
    domain = normalize_domain(domain)
    
    # Check pattern
    if not DOMAIN_PATTERN.match(domain):
        return False
    
    # Check for consecutive dots
    if '..' in domain:
        return False
    
    return True


def normalize_domain(domain: str) -> str:
    """
    Normalizes a domain (removes http://, https://, www., trailing slashes).
    
    Args:
        domain: Domain to normalize
    
    Returns:
        Normalized domain (e.g., 'example.com')
    """
    if not domain:
        return ""
    
    # Remove protocol
    domain = re.sub(r'^https?://', '', domain)
    
    # Remove www.
    domain = re.sub(r'^www\.', '', domain)
    
    # Remove trailing slashes and paths
    domain = domain.split('/')[0]
    
    # Remove port numbers
    domain = domain.split(':')[0]
    
    # Convert to lowercase
    domain = domain.lower().strip()
    
    return domain
