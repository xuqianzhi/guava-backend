"""
Merchant routes for Firebase Functions
"""

from firebase_functions import https_fn
from firebase_admin import firestore
from datetime import datetime
from typing import List, Optional, Union
import json

from constants.constants import (
    CORSHeaders,
    MERCHANTS_COLLECTION,
    COLLECTION_REQUIRED_FIELDS,
    HTTP_OK,
    HTTP_NO_CONTENT,
    HTTP_MULTI_STATUS,
    HTTP_BAD_REQUEST,
    HTTP_METHOD_NOT_ALLOWED,
    HTTP_INTERNAL_SERVER_ERROR,
)

from constants.merchant import (
    Merchant,
    MerchantInput,
    MerchantResponse,
    StoredMerchantResult,
    MerchantError,
    MultipleMerchantsRequest,
    StoreMerchantsResponse,
    GetMerchantsResponse,
)

from utils import get_cors_headers, is_origin_allowed, email_to_short_id, normalize_email


@https_fn.on_request()
def store_merchant(req: https_fn.Request) -> https_fn.Response:
    """
    Cloud Function to store merchant information in Firestore.
    Accepts either:
    1. Single merchant: JSON object with name, email, address, description, industry
    2. Multiple merchants: JSON object with "merchants" array containing merchant objects
    """
    # Get request origin and determine CORS headers
    request_origin: Optional[str] = req.headers.get('Origin')
    headers: CORSHeaders = get_cors_headers(request_origin)
    
    # Handle preflight request
    if req.method == 'OPTIONS':
        return https_fn.Response('', status=HTTP_NO_CONTENT, headers=headers)
    
    # Check if origin is allowed
    if not is_origin_allowed(request_origin):
        return https_fn.Response(
            json.dumps({'error': 'Origin not allowed'}),
            status=403,
            headers=headers,
            mimetype='application/json'
        )
    
    # Only allow POST requests for storing data
    if req.method != 'POST':
        return https_fn.Response(
            json.dumps({'error': 'Only POST method is allowed'}),
            status=HTTP_METHOD_NOT_ALLOWED,
            headers=headers,
            mimetype='application/json'
        )
    
    try:
        # Get Firestore client
        db: firestore.Client = firestore.client()
        
        # Parse JSON data from request
        data: Optional[Union[MerchantInput, MultipleMerchantsRequest]] = req.get_json()
        
        if not data:
            return https_fn.Response(
                json.dumps({'error': 'No JSON data provided'}),
                status=HTTP_BAD_REQUEST,
                headers=headers,
                mimetype='application/json'
            )
        
        # Required fields for each merchant
        required_fields: List[str] = COLLECTION_REQUIRED_FIELDS[MERCHANTS_COLLECTION]
        
        # Check if this is a batch request (contains "merchants" array) or single merchant
        if 'merchants' in data:
            # Multiple merchants
            merchants_to_process: List[MerchantInput] = data['merchants']  # type: ignore
            if not isinstance(merchants_to_process, list):
                return https_fn.Response(
                    json.dumps({'error': 'merchants field must be an array'}),
                    status=HTTP_BAD_REQUEST,
                    headers=headers,
                    mimetype='application/json'
                )
            
            if len(merchants_to_process) == 0:
                return https_fn.Response(
                    json.dumps({'error': 'merchants array cannot be empty'}),
                    status=HTTP_BAD_REQUEST,
                    headers=headers,
                    mimetype='application/json'
                )
        else:
            # Single merchant - wrap in array for uniform processing
            merchants_to_process = [data]  # type: ignore
        
        # Validate all merchants before processing any
        validation_errors: List[str] = []
        for i, merchant in enumerate(merchants_to_process):
            missing_fields: List[str] = [field for field in required_fields if field not in merchant or not merchant[field]]
            if missing_fields:
                validation_errors.append(f"Merchant {i+1}: Missing required fields: {', '.join(missing_fields)}")
        
        if validation_errors:
            return https_fn.Response(
                json.dumps({'error': validation_errors}),
                status=HTTP_BAD_REQUEST,
                headers=headers,
                mimetype='application/json'
            )
        
        # Process all merchants
        current_datetime: datetime = datetime.now()
        stored_merchants: List[StoredMerchantResult] = []
        errors: List[MerchantError] = []
        
        for i, merchant in enumerate(merchants_to_process):
            try:
                # Create short, deterministic document ID from email
                doc_id: str = email_to_short_id(merchant['email'])
                
                # Check if document already exists
                doc_ref: firestore.DocumentReference = db.collection(MERCHANTS_COLLECTION).document(doc_id)
                existing_doc: firestore.DocumentSnapshot = doc_ref.get()
                
                # Prepare document data
                merchant_data: Merchant = {
                    'name': merchant['name'],
                    'email': merchant['email'],
                    'address': merchant['address'],
                    'description': merchant['description'],
                    'industry': merchant['industry'],
                    'datetime': current_datetime
                }
                
                # Store in Firestore with custom document ID
                doc_ref.set(merchant_data)
                
                stored_merchant_result: StoredMerchantResult = {
                    'email': merchant['email'],
                    'document_id': doc_id,
                    'status': 'success',
                    'action': 'updated' if existing_doc.exists else 'created'
                }
                stored_merchants.append(stored_merchant_result)
                
            except Exception as merchant_error:
                error_entry: MerchantError = {
                    'merchant_index': i + 1,
                    'email': merchant.get('email', 'unknown'),
                    'error': str(merchant_error)
                }
                errors.append(error_entry)
        
        # Prepare response
        response_data: StoreMerchantsResponse = {
            'success': len(errors) == 0,
            'total_merchants': len(merchants_to_process),
            'stored_successfully': len(stored_merchants),
            'stored_merchants': stored_merchants,
            'message': f'All {len(stored_merchants)} merchant(s) stored successfully',
            'errors': None
        }
        
        if errors:
            response_data['errors'] = errors
            response_data['message'] = f'Partially successful: {len(stored_merchants)} of {len(merchants_to_process)} merchants stored'
        
        status_code: int = HTTP_OK if len(errors) == 0 else HTTP_MULTI_STATUS  # 207 = Multi-Status for partial success
        
        return https_fn.Response(
            json.dumps(response_data),
            status=status_code,
            headers=headers,
            mimetype='application/json'
        )
        
    except Exception as e:
        return https_fn.Response(
            json.dumps({'error': f'Internal server error: {str(e)}'}),
            status=HTTP_INTERNAL_SERVER_ERROR,
            headers=headers,
            mimetype='application/json'
        )


@https_fn.on_request()
def get_merchants(req: https_fn.Request) -> https_fn.Response:
    """
    Cloud Function to retrieve merchant information from Firestore.
    Optional query parameter: emails (comma-separated list of email addresses)
    """
    # Get request origin and determine CORS headers
    request_origin: Optional[str] = req.headers.get('Origin')
    headers: CORSHeaders = get_cors_headers(request_origin)
    
    # Handle preflight request
    if req.method == 'OPTIONS':
        return https_fn.Response('', status=HTTP_NO_CONTENT, headers=headers)
    
    # Check if origin is allowed
    if not is_origin_allowed(request_origin):
        return https_fn.Response(
            json.dumps({'error': 'Origin not allowed'}),
            status=403,
            headers=headers,
            mimetype='application/json'
        )
    
    # Only allow GET requests for retrieving data
    if req.method != 'GET':
        return https_fn.Response(
            json.dumps({'error': 'Only GET method is allowed'}),
            status=HTTP_METHOD_NOT_ALLOWED,
            headers=headers,
            mimetype='application/json'
        )
    
    try:
        # Get Firestore client
        db: firestore.Client = firestore.client()
        
        # Get identifiers filter from query parameters
        identifiers_param: Optional[str] = req.args.get('identifiers')
        
        merchants: List[MerchantResponse] = []
        
        if identifiers_param:
            # Parse comma-separated identifier list
            identifier_list: List[str] = [identifier.strip() for identifier in identifiers_param.split(',') if identifier.strip()]
            
            if identifier_list:
                # Fetch specific documents by identifier (document ID)
                for identifier in identifier_list:
                    doc_ref: firestore.DocumentReference = db.collection(MERCHANTS_COLLECTION).document(identifier)
                    doc: firestore.DocumentSnapshot = doc_ref.get()
                    
                    if doc.exists:
                        merchant_data_dict: Optional[dict] = doc.to_dict()
                        if merchant_data_dict:
                            # Convert datetime to string for JSON serialization
                            if 'datetime' in merchant_data_dict and merchant_data_dict['datetime']:
                                merchant_data_dict['datetime'] = merchant_data_dict['datetime'].isoformat()
                            merchant_data_dict['id'] = doc.id
                            # Cast to MerchantResponse type
                            merchant_response: MerchantResponse = merchant_data_dict  # type: ignore
                            merchants.append(merchant_response)
            else:
                return https_fn.Response(
                    json.dumps({'error': 'Invalid identifiers parameter - no valid identifiers found'}),
                    status=HTTP_BAD_REQUEST,
                    headers=headers
                )
        else:
            # No filter - retrieve all merchants from Firestore
            merchants_ref: firestore.CollectionReference = db.collection(MERCHANTS_COLLECTION)
            docs: firestore.Generator = merchants_ref.stream()
            
            for doc in docs:
                merchant_data_dict = doc.to_dict()
                if merchant_data_dict:
                    # Convert datetime to string for JSON serialization
                    if 'datetime' in merchant_data_dict and merchant_data_dict['datetime']:
                        merchant_data_dict['datetime'] = merchant_data_dict['datetime'].isoformat()
                    merchant_data_dict['id'] = doc.id
                    # Cast to MerchantResponse type
                    merchant_response = merchant_data_dict  # type: ignore
                    merchants.append(merchant_response)
        
        response: GetMerchantsResponse = {
            'success': True,
            'merchants': merchants,
            'count': len(merchants),
            'filtered': bool(identifiers_param)
        }
        
        return https_fn.Response(
            json.dumps(response),
            status=HTTP_OK,
            headers=headers,
            mimetype='application/json'
        )
        
    except Exception as e:
        return https_fn.Response(
            json.dumps({'error': f'Internal server error: {str(e)}'}),
            status=HTTP_INTERNAL_SERVER_ERROR,
            headers=headers,
            mimetype='application/json'
        )
