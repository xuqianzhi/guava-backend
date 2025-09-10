"""
Utility functions for Firebase Functions
"""

import hashlib
import base64
from typing import Optional
from constants.constants import (
    CORSHeaders,
    ALLOWED_ORIGINS,
    CORS_ALLOW_METHODS,
    CORS_ALLOW_HEADERS
)

def get_cors_headers(request_origin: Optional[str]) -> CORSHeaders:
    """
    Get appropriate CORS headers based on request origin.
    Only allows requests from specified origins.
    """
    if request_origin and request_origin in ALLOWED_ORIGINS:
        return {
            'Access-Control-Allow-Origin': request_origin,
            'Access-Control-Allow-Methods': CORS_ALLOW_METHODS,
            'Access-Control-Allow-Headers': CORS_ALLOW_HEADERS
        }
    else:
        # Return restrictive headers for unauthorized origins
        return {
            'Access-Control-Allow-Origin': '',
            'Access-Control-Allow-Methods': '',
            'Access-Control-Allow-Headers': ''
        }

def is_origin_allowed(request_origin: Optional[str]) -> bool:
    """Check if the request origin is in the allowed list"""
    return request_origin is None or request_origin in ALLOWED_ORIGINS

def normalize_email(email: str) -> str:
    """
    Normalize email address for consistent processing.
    Converts to lowercase and strips whitespace.
    """
    return email.lower().strip()

def email_to_short_id(email: str) -> str:
    """
    Convert email address to a short, deterministic identifier.
    
    Uses SHA-256 hash and base64 encoding to create a short (11-character)
    identifier that's URL-safe and deterministic.
    
    Args:
        email: Email address to convert
        
    Returns:
        Short identifier (11 characters) based on email hash
    """
    # Normalize email first
    normalized_email = normalize_email(email)
    
    # Create SHA-256 hash
    hash_bytes = hashlib.sha256(normalized_email.encode('utf-8')).digest()
    
    # Use base64 encoding and take first 11 characters for short ID
    # Remove padding and use URL-safe characters
    short_id = base64.urlsafe_b64encode(hash_bytes)[:11].decode('utf-8')
    
    return short_id
