"""
Constants and TypedDict definitions for Firebase Functions
"""

from typing import List, Optional, Union, Literal, TypedDict
from datetime import datetime

# TypedDict definitions
class ContactInput(TypedDict):
    name: str
    email: str
    phone: Optional[str]
    company: Optional[str]
    industry: Optional[str]
    message: str

class ContactData(TypedDict):
    name: str
    email: str
    phone: str
    company: str
    industry: str
    message: List[str]
    datetime: datetime

class ContactResponse(TypedDict):
    name: str
    email: str
    phone: str
    company: str
    industry: str
    message: List[str]
    datetime: str
    id: str

class StoredContactResult(TypedDict):
    email: str
    document_id: str
    status: Literal['success']
    action: Literal['created', 'updated']
    total_messages: int

class ContactError(TypedDict):
    contact_index: int
    email: str
    error: str

class SingleContactRequest(TypedDict):
    name: str
    email: str
    phone: Optional[str]
    company: Optional[str]
    industry: Optional[str]
    message: str

class MultipleContactsRequest(TypedDict):
    contacts: List[ContactInput]

class StoreContactResponse(TypedDict):
    success: bool
    total_contacts: int
    stored_successfully: int
    stored_contacts: List[StoredContactResult]
    message: str
    errors: Optional[List[ContactError]]

class GetContactsResponse(TypedDict):
    success: bool
    contacts: List[ContactResponse]
    count: int
    filtered: bool

class ErrorResponse(TypedDict):
    error: Union[str, List[str]]

class CORSHeaders(TypedDict):
    Access_Control_Allow_Origin: str
    Access_Control_Allow_Methods: str
    Access_Control_Allow_Headers: str

# Collection Names
CONTACTS_COLLECTION: str = 'contacts'

# Collection to required fields mapping
COLLECTION_REQUIRED_FIELDS: dict[str, List[str]] = {
    CONTACTS_COLLECTION: ['name', 'email', 'message']  # phone, company, industry are now optional
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
ALLOWED_ORIGINS: List[str] = [
    'http://localhost:3000',
    'http://localhost:3001', 
    'http://localhost:8080',
    'https://localhost:3000',
    'https://guavaaa.com',
    'https://www.guavaaa.com'
]
CORS_ALLOW_METHODS: str = 'GET, POST, OPTIONS'
CORS_ALLOW_HEADERS: str = 'Content-Type'
