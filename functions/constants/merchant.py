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
    datetime: datetime

class MerchantInput(TypedDict):
    """Input data for creating/updating a merchant"""
    name: str
    email: str
    address: str
    description: str
    industry: str

class MerchantResponse(TypedDict):
    """Merchant data returned in API responses"""
    name: str
    email: str
    address: str
    description: str
    industry: str
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

class GetMerchantsResponse(TypedDict):
    """Response from get_merchants function"""
    success: bool
    merchants: List[MerchantResponse]
    count: int
    filtered: bool
