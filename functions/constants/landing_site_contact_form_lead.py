"""
Landing Site Contact Form Lead TypedDict definitions for Firebase Functions
"""

from typing import List, Optional, Literal, TypedDict
from datetime import datetime

# Core lead data structures
class LandingSiteContactFormLead(TypedDict):
    """Represents a landing site contact form lead document in Firestore"""
    company: str
    datetime: datetime
    email: str
    industry: str
    message: List[str]
    name: str
    phone: str

class LandingSiteContactFormLeadInput(TypedDict):
    """Input data for creating/updating a lead (optional fields allowed)"""
    name: str
    email: str
    phone: Optional[str]
    company: Optional[str]
    industry: Optional[str]
    message: str

class LandingSiteContactFormLeadResponse(TypedDict):
    """Lead data returned in API responses"""
    company: str
    datetime: str  # ISO format string for JSON serialization
    email: str
    industry: str
    message: List[str]
    name: str
    phone: str
    id: str  # Document ID

# Request and response structures
class MultipleLeadsRequest(TypedDict):
    """Request body for storing multiple leads"""
    contacts: List[LandingSiteContactFormLeadInput]

class StoredLeadResult(TypedDict):
    """Result of storing a single lead"""
    email: str
    document_id: str
    status: Literal['success']
    action: Literal['created', 'updated']
    total_messages: int

class LeadError(TypedDict):
    """Error information for a failed lead operation"""
    contact_index: int
    email: str
    error: str

class StoreLeadsResponse(TypedDict):
    """Response from store_contact function"""
    success: bool
    total_contacts: int
    stored_successfully: int
    stored_contacts: List[StoredLeadResult]
    message: str
    errors: Optional[List[LeadError]]

class GetLeadsResponse(TypedDict):
    """Response from get_contacts function"""
    success: bool
    contacts: List[LandingSiteContactFormLeadResponse]
    count: int
    filtered: bool
