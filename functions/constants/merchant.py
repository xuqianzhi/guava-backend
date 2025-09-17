"""
Merchant-related TypedDict definitions for Firebase Functions
"""

from typing import List, Optional, Literal, TypedDict
from datetime import datetime

# Core merchant data structures
class Merchant(TypedDict):
    """Represents a merchant document in Firestore"""
    name: str
    email: str
    address: str
    description: str
    industry: str
    phone: Optional[str]  # Optional phone number field
    datetime: datetime

class MerchantInput(TypedDict):
    """Input data for creating/updating a merchant"""
    name: str
    email: str
    address: str
    description: str
    industry: str
    phone: Optional[str]  # Optional phone number field

class MerchantResponse(TypedDict):
    """Merchant data returned in API responses"""
    name: str
    email: str
    address: str
    description: str
    industry: str
    phone: Optional[str]  # Optional phone number field
    datetime: str  # ISO format string for JSON serialization
    id: str  # Document ID

# Request and response structures
class MultipleMerchantsRequest(TypedDict):
    """Request body for storing multiple merchants"""
    merchants: List[MerchantInput]

class StoredMerchantResult(TypedDict):
    """Result of storing a single merchant"""
    email: str
    document_id: str
    status: Literal['success']
    action: Literal['created', 'updated']

class MerchantError(TypedDict):
    """Error information for a failed merchant operation"""
    merchant_index: int
    email: str
    error: str

class StoreMerchantsResponse(TypedDict):
    """Response from store_merchant function"""
    success: bool
    total_merchants: int
    stored_successfully: int
    stored_merchants: List[StoredMerchantResult]
    message: str
    errors: Optional[List[MerchantError]]

class PaginationInfo(TypedDict):
    """Pagination information for paginated responses"""
    has_more: bool
    next_cursor: Optional[str]
    limit: Optional[int]

class GetMerchantsResponse(TypedDict):
    """Response from get_merchants function"""
    success: bool
    merchants: List[MerchantResponse]
    count: int
    filtered: bool
    pagination: Optional[PaginationInfo]
