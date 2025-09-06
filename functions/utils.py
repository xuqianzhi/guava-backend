"""
Utility functions for Firebase Functions
"""

from typing import Optional
from constants import (
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
    return request_origin is not None and request_origin in ALLOWED_ORIGINS
