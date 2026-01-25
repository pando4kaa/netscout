"""
Subdomain Finder Module

This module provides functionality to discover subdomains using passive methods
(Certificate Transparency logs).
"""

import requests
import json
from typing import List, Set
import time


def find_subdomains_passive(domain: str) -> List[str]:
    """
    Finds subdomains using Certificate Transparency logs (crt.sh).
    
    Args:
        domain: Base domain to search for (e.g., 'example.com')
    
    Returns:
        List of unique subdomains:
        ['www.example.com', 'api.example.com', ...]
    """
    subdomains: Set[str] = set()
    
    try:
        url = f"https://crt.sh/?q={domain}&output=json"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            for entry in data:
                name_value = entry.get('name_value', '')
                
                # Split by newline and comma (some entries contain multiple domains)
                for name in name_value.replace('\n', ',').split(','):
                    name = name.strip()
                    
                    # Filter out wildcards
                    if name.startswith('*.'):
                        name = name[2:]
                    
                    # Validate that it's a subdomain of our target
                    if domain in name and name.endswith(domain):
                        subdomains.add(name.lower())
            
            # Remove the base domain itself
            subdomains.discard(domain.lower())
            
        else:
            print(f"Warning: crt.sh returned status code {response.status_code}")
            
    except requests.Timeout:
        print("Warning: crt.sh request timed out")
    except requests.RequestException as e:
        print(f"Warning: Error querying crt.sh: {e}")
    except json.JSONDecodeError:
        print("Warning: Invalid JSON response from crt.sh")
    except Exception as e:
        print(f"Warning: Unexpected error: {e}")
    
    return sorted(list(subdomains))
