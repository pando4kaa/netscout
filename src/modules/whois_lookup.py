"""
WHOIS Lookup Module

This module provides functionality to retrieve WHOIS information for a domain.
"""

import whois
from typing import Dict, Optional
from datetime import datetime


def get_whois_info(domain: str) -> Dict:
    """
    Retrieves WHOIS information for a domain.
    
    Args:
        domain: Domain name to query
    
    Returns:
        Dictionary with WHOIS data:
        {
            'registrar': '...',
            'creation_date': '2020-01-15',
            'expiration_date': '2025-01-15',
            'name_servers': [...],
            'emails': [...],
            'status': 'active'
        }
    
    Raises:
        WhoisException: If WHOIS data is unavailable
    """
    try:
        w = whois.whois(domain)
        
        # Normalize dates
        creation_date = None
        if w.creation_date:
            if isinstance(w.creation_date, list):
                creation_date = w.creation_date[0]
            else:
                creation_date = w.creation_date
            if isinstance(creation_date, datetime):
                creation_date = creation_date.strftime("%Y-%m-%d")
        
        expiration_date = None
        if w.expiration_date:
            if isinstance(w.expiration_date, list):
                expiration_date = w.expiration_date[0]
            else:
                expiration_date = w.expiration_date
            if isinstance(expiration_date, datetime):
                expiration_date = expiration_date.strftime("%Y-%m-%d")
        
        # Extract emails
        emails = []
        if w.emails:
            if isinstance(w.emails, list):
                emails = [str(email) for email in w.emails if email]
            else:
                emails = [str(w.emails)]
        
        # Extract name servers
        name_servers = []
        if w.name_servers:
            if isinstance(w.name_servers, list):
                name_servers = [str(ns).lower() for ns in w.name_servers]
            else:
                name_servers = [str(w.name_servers).lower()]
        
        return {
            "domain": domain,
            "registrar": str(w.registrar) if w.registrar else None,
            "creation_date": creation_date,
            "expiration_date": expiration_date,
            "name_servers": name_servers,
            "emails": emails,
            "status": str(w.status) if w.status else None
        }
    except Exception as e:
        raise Exception(f"WHOIS lookup failed: {str(e)}")
