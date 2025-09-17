"""
Constants and TypedDict definitions for Firebase Functions
"""

from typing import List, Union, TypedDict

# General API response structures
class ErrorResponse(TypedDict):
    error: Union[str, List[str]]

class CORSHeaders(TypedDict):
    Access_Control_Allow_Origin: str
    Access_Control_Allow_Methods: str
    Access_Control_Allow_Headers: str

# Collection Names
LANDING_SITE_CONTACT_FORM_LEAD_COLLECTION: str = 'landing-site-contact-form-lead'
MERCHANTS_COLLECTION: str = 'merchants'
PENDING_MERCHANTS_COLLECTION: str = 'pending-merchants'

# Collection to required fields mapping
COLLECTION_REQUIRED_FIELDS: dict[str, List[str]] = {
    LANDING_SITE_CONTACT_FORM_LEAD_COLLECTION: ['name', 'email', 'message'],  # phone, company, industry are now optional
    MERCHANTS_COLLECTION: ['name', 'email', 'address', 'description', 'industry'],
    PENDING_MERCHANTS_COLLECTION: ['name', 'email', 'address', 'description', 'industry']
}

# Firebase configuration
MAX_INSTANCES: int = 10

# HTTP Status Codes
HTTP_OK: int = 200
HTTP_NO_CONTENT: int = 204
HTTP_MULTI_STATUS: int = 207
HTTP_BAD_REQUEST: int = 400
HTTP_METHOD_NOT_ALLOWED: int = 405
HTTP_INTERNAL_SERVER_ERROR: int = 500

# CORS Configuration
CORS_ALLOW_METHODS: str = 'GET, POST, OPTIONS'
CORS_ALLOW_HEADERS: str = 'Content-Type'

# CORS Configuration
ALLOWED_ORIGINS: List[str] = [
    'http://localhost:3000',
    'https://localhost:3000',
    'https://guavaaa.com',
    'https://www.guavaaa.com',
    'https://kol.guavaaa.com',
    'http://192.168.1.181:3000',
    'https://192.168.1.181:3000',
]
CORS_ALLOW_METHODS: str = 'GET, POST, OPTIONS'
CORS_ALLOW_HEADERS: str = 'Content-Type'


