"""
Service-to-Service Authentication Module

Provides authentication utilities for internal microservice communication.
Services can use these utilities to authenticate when making internal API calls
that require authentication tokens.

Usage:
    from shared.auth.service_auth import get_service_auth_headers
    
    headers = get_service_auth_headers("ppl-meta-media")
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            ...
"""

import os
from typing import Dict, Optional

# Internal service token - should be set via environment variable
# This token is used for service-to-service authentication
INTERNAL_SERVICE_TOKEN = os.getenv(
    "INTERNAL_SERVICE_TOKEN", 
    "ppl-meta-internal-service-secret-key-change-in-production"
)

# List of known internal services for validation
KNOWN_SERVICES = {
    "ppl-meta-media",
    "ppl-meta-cameras",
    "ppl-meta-orchestrator",
    "ppl-meta-gateway",
    "ppl-meta-node",
    "ppl-meta-vision",
    "ppl-meta-vmeta",
    "ppl-meta-discovery",
    "ppl-meta-bootcore",
}


def get_service_auth_headers(service_name: str) -> Dict[str, str]:
    """
    Get authentication headers for service-to-service communication.
    
    Args:
        service_name: Name of the calling service (e.g., "ppl-meta-media")
        
    Returns:
        Dictionary of HTTP headers including Authorization bearer token
        
    Example:
        >>> headers = get_service_auth_headers("ppl-meta-media")
        >>> # Use headers in HTTP request to another internal service
    """
    return {
        "Authorization": f"Bearer {INTERNAL_SERVICE_TOKEN}",
        "X-Service-Name": service_name,
        "X-Service-Auth": "internal",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def is_valid_service_token(token: str) -> bool:
    """
    Validate if a token is a valid internal service token.
    
    Args:
        token: The bearer token to validate
        
    Returns:
        True if token is valid internal service token, False otherwise
    """
    return token == INTERNAL_SERVICE_TOKEN


def is_internal_service_request(
    authorization: Optional[str] = None,
    service_name: Optional[str] = None,
) -> bool:
    """
    Check if a request is from an internal service.
    
    Args:
        authorization: Authorization header value (e.g., "Bearer token...")
        service_name: X-Service-Name header value
        
    Returns:
        True if request is from valid internal service, False otherwise
    """
    if not authorization or not authorization.startswith("Bearer "):
        return False
    
    token = authorization.split(" ", 1)[1]
    
    # Validate token
    if not is_valid_service_token(token):
        return False
    
    # Optionally validate service name if provided
    if service_name and service_name not in KNOWN_SERVICES:
        return False
    
    return True


def validate_service_auth(
    authorization: Optional[str] = None,
    service_name: Optional[str] = None,
) -> tuple[bool, Optional[str]]:
    """
    Validate service authentication and return result with reason.
    
    Args:
        authorization: Authorization header value
        service_name: X-Service-Name header value
        
    Returns:
        Tuple of (is_valid, error_message)
        - (True, None) if valid
        - (False, "error message") if invalid
    """
    if not authorization:
        return False, "Missing Authorization header"
    
    if not authorization.startswith("Bearer "):
        return False, "Invalid Authorization header format"
    
    token = authorization.split(" ", 1)[1]
    
    if not is_valid_service_token(token):
        return False, "Invalid service token"
    
    if service_name and service_name not in KNOWN_SERVICES:
        return False, f"Unknown service: {service_name}"
    
    return True, None
