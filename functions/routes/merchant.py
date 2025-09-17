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
    PENDING_MERCHANTS_COLLECTION,
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
    PaginationInfo,
)

from utils import get_cors_headers, is_origin_allowed, email_to_short_id, normalize_email


# Helper functions for common merchant operations

def handle_common_request_validation(req: https_fn.Request, allowed_method: str) -> Optional[https_fn.Response]:
    """
    Handle common request validation (CORS, preflight, origin check, method validation).
    Returns None if validation passes, or Response object if validation fails.
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
    
    # Check if method is allowed
    if req.method != allowed_method:
        return https_fn.Response(
            json.dumps({'error': f'Only {allowed_method} method is allowed'}),
            status=HTTP_METHOD_NOT_ALLOWED,
            headers=headers,
            mimetype='application/json'
        )
    
    return None


def process_merchants_for_storage(
    merchants_to_process: List[MerchantInput], 
    collection_name: str,
    required_fields: List[str]
) -> StoreMerchantsResponse:
    """
    Process a list of merchants for storage in the specified collection.
    Returns the response with stored merchants and any errors.
    """
    # Get request origin for CORS headers
    headers: CORSHeaders = get_cors_headers(None)  # We'll set this properly in the calling function
    
    # Validate all merchants before processing any
    validation_errors: List[str] = []
    for i, merchant in enumerate(merchants_to_process):
        missing_fields: List[str] = [field for field in required_fields if field not in merchant or not merchant[field]]
        if missing_fields:
            validation_errors.append(f"Merchant {i+1}: Missing required fields: {', '.join(missing_fields)}")
    
    if validation_errors:
        error_response: StoreMerchantsResponse = {
            'success': False,
            'total_merchants': len(merchants_to_process),
            'stored_successfully': 0,
            'stored_merchants': [],
            'message': f'Validation failed for {len(validation_errors)} merchant(s)',
            'errors': [{'merchant_index': i + 1, 'email': '', 'error': error} for i, error in enumerate(validation_errors)]
        }
        return error_response
    
    # Process merchants for storage
    stored_merchants: List[StoredMerchantResult] = []
    errors: List[MerchantError] = []
    
    # Get Firestore client
    db: firestore.Client = firestore.client()
    current_datetime: datetime = datetime.now()
    
    for i, merchant in enumerate(merchants_to_process):
        try:
            # Normalize email and create document ID
            normalized_email: str = normalize_email(merchant['email'])
            doc_id: str = email_to_short_id(normalized_email)
            
            # Check if document already exists
            doc_ref: firestore.DocumentReference = db.collection(collection_name).document(doc_id)
            existing_doc: firestore.DocumentSnapshot = doc_ref.get()
            
            # Prepare document data
            merchant_data: Merchant = {
                'name': merchant['name'],
                'email': merchant['email'],
                'address': merchant['address'],
                'description': merchant['description'],
                'industry': merchant['industry'],
                'phone': merchant.get('phone'),  # Optional phone field
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
            error_info: MerchantError = {
                'merchant_index': i,
                'email': merchant.get('email', 'unknown'),
                'error': str(merchant_error)
            }
            errors.append(error_info)
    
    # Prepare response
    response: StoreMerchantsResponse = {
        'success': len(errors) == 0,
        'total_merchants': len(merchants_to_process),
        'stored_successfully': len(stored_merchants),
        'stored_merchants': stored_merchants,
        'message': f'Successfully stored {len(stored_merchants)} out of {len(merchants_to_process)} merchants',
        'errors': errors if errors else None
    }
    
    return response


def get_merchants_from_collection(
    collection_name: str,
    identifiers_param: Optional[str] = None,
    limit: Optional[int] = None,
    cursor: Optional[str] = None
) -> GetMerchantsResponse:
    """
    Retrieve merchants from the specified collection.
    Optionally filter by document identifiers.
    Supports pagination with limit and cursor.
    """
    # Get Firestore client
    db: firestore.Client = firestore.client()
    
    merchants: List[MerchantResponse] = []
    
    if identifiers_param:
        # Parse comma-separated identifier list
        identifier_list: List[str] = [identifier.strip() for identifier in identifiers_param.split(',') if identifier.strip()]
        
        if identifier_list:
            # Fetch specific documents by identifier (document ID)
            for identifier in identifier_list:
                doc_ref: firestore.DocumentReference = db.collection(collection_name).document(identifier)
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
            # Invalid identifiers parameter
            return {
                'success': False,
                'merchants': [],
                'count': 0,
                'filtered': True
            }
    else:
        # No filter - retrieve merchants from collection with pagination
        merchants_ref: firestore.CollectionReference = db.collection(collection_name)
        
        # Order by datetime (newest first) for consistent pagination
        query = merchants_ref.order_by('datetime', direction=firestore.Query.DESCENDING)
        
        # Apply cursor if provided
        if cursor:
            try:
                # Get the document to start after
                cursor_doc = db.collection(collection_name).document(cursor).get()
                if cursor_doc.exists:
                    query = query.start_after(cursor_doc)
            except Exception:
                # If cursor document doesn't exist or is invalid, ignore it
                pass
        
        # Apply limit if provided
        if limit and limit > 0:
            query = query.limit(limit)
        
        # Execute query
        docs = query.stream()
        
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
    
    # Prepare pagination info
    has_more = False
    next_cursor = None
    
    # If we have a limit and got exactly that many results, there might be more
    if limit and len(merchants) == limit:
        has_more = True
        # The next cursor is the ID of the last document
        if merchants:
            next_cursor = merchants[-1]['id']
    
    response: GetMerchantsResponse = {
        'success': True,
        'merchants': merchants,
        'count': len(merchants),
        'filtered': bool(identifiers_param),
        'pagination': {
            'has_more': has_more,
            'next_cursor': next_cursor,
            'limit': limit
        } if not identifiers_param else None  # Only include pagination for non-filtered results
    }
    
    return response


@https_fn.on_request()
def store_merchant(req: https_fn.Request) -> https_fn.Response:
    """
    Cloud Function to store merchant information in Firestore.
    Accepts either:
    1. Single merchant: JSON object with name, email, address, description, industry
    2. Multiple merchants: JSON object with "merchants" array containing merchant objects
    """
    # Handle common request validation
    validation_response = handle_common_request_validation(req, 'POST')
    if validation_response:
        return validation_response
    
    # Get CORS headers for this request
    request_origin: Optional[str] = req.headers.get('Origin')
    headers: CORSHeaders = get_cors_headers(request_origin)
    
    try:
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
        
        # Process merchants using helper function
        response_data: StoreMerchantsResponse = process_merchants_for_storage(
            merchants_to_process, 
            MERCHANTS_COLLECTION,
            required_fields
        )
        
        # Determine status code
        status_code: int = HTTP_OK if response_data['success'] else HTTP_MULTI_STATUS
        
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
    Query parameters:
    - identifiers: comma-separated list of document IDs (optional)
    - limit: maximum number of results to return (optional, default: no limit)
    - cursor: document ID to start after for pagination (optional)
    """
    # Handle common request validation
    validation_response = handle_common_request_validation(req, 'GET')
    if validation_response:
        return validation_response
    
    # Get CORS headers for this request
    request_origin: Optional[str] = req.headers.get('Origin')
    headers: CORSHeaders = get_cors_headers(request_origin)
    
    try:
        # Get query parameters
        identifiers_param: Optional[str] = req.args.get('identifiers')
        limit_param: Optional[str] = req.args.get('limit')
        cursor_param: Optional[str] = req.args.get('cursor')
        
        # Parse and validate limit parameter
        limit: Optional[int] = None
        if limit_param:
            try:
                limit = int(limit_param)
                if limit <= 0:
                    return https_fn.Response(
                        json.dumps({'error': 'limit must be a positive integer'}),
                        status=HTTP_BAD_REQUEST,
                        headers=headers,
                        mimetype='application/json'
                    )
                # Set reasonable maximum limit to prevent abuse
                if limit > 100:
                    limit = 100
            except ValueError:
                return https_fn.Response(
                    json.dumps({'error': 'limit must be a valid integer'}),
                    status=HTTP_BAD_REQUEST,
                    headers=headers,
                    mimetype='application/json'
                )
        
        # Use helper function to get merchants with pagination
        response_data: GetMerchantsResponse = get_merchants_from_collection(
            MERCHANTS_COLLECTION, 
            identifiers_param,
            limit,
            cursor_param
        )
        
        if not response_data['success']:
            return https_fn.Response(
                json.dumps({'error': 'Invalid identifiers parameter - no valid identifiers found'}),
                status=HTTP_BAD_REQUEST,
                headers=headers,
                mimetype='application/json'
            )
        
        return https_fn.Response(
            json.dumps(response_data),
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


@https_fn.on_request()
def get_pending_merchants(req: https_fn.Request) -> https_fn.Response:
    """
    Cloud Function to retrieve pending merchant information from Firestore.
    Query parameters:
    - identifiers: comma-separated list of document IDs (optional)
    - limit: maximum number of results to return (optional, default: no limit)
    - cursor: document ID to start after for pagination (optional)
    """
    # Handle common request validation
    validation_response = handle_common_request_validation(req, 'GET')
    if validation_response:
        return validation_response
    
    # Get CORS headers for this request
    request_origin: Optional[str] = req.headers.get('Origin')
    headers: CORSHeaders = get_cors_headers(request_origin)
    
    try:
        # Get query parameters
        identifiers_param: Optional[str] = req.args.get('identifiers')
        limit_param: Optional[str] = req.args.get('limit')
        cursor_param: Optional[str] = req.args.get('cursor')
        
        # Parse and validate limit parameter
        limit: Optional[int] = None
        if limit_param:
            try:
                limit = int(limit_param)
                if limit <= 0:
                    return https_fn.Response(
                        json.dumps({'error': 'limit must be a positive integer'}),
                        status=HTTP_BAD_REQUEST,
                        headers=headers,
                        mimetype='application/json'
                    )
                # Set reasonable maximum limit to prevent abuse
                if limit > 100:
                    limit = 100
            except ValueError:
                return https_fn.Response(
                    json.dumps({'error': 'limit must be a valid integer'}),
                    status=HTTP_BAD_REQUEST,
                    headers=headers,
                    mimetype='application/json'
                )
        
        # Use helper function to get pending merchants with pagination
        response_data: GetMerchantsResponse = get_merchants_from_collection(
            PENDING_MERCHANTS_COLLECTION, 
            identifiers_param,
            limit,
            cursor_param
        )
        
        if not response_data['success']:
            return https_fn.Response(
                json.dumps({'error': 'Invalid identifiers parameter - no valid identifiers found'}),
                status=HTTP_BAD_REQUEST,
                headers=headers,
                mimetype='application/json'
            )
        
        return https_fn.Response(
            json.dumps(response_data),
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


@https_fn.on_request()
def store_pending_merchant(req: https_fn.Request) -> https_fn.Response:
    """
    Cloud Function to store pending merchant information in Firestore.
    Accepts either:
    1. Single merchant: JSON object with name, email, address, description, industry, phone (optional)
    2. Multiple merchants: JSON object with "merchants" array containing merchant objects
    """
    # Handle common request validation
    validation_response = handle_common_request_validation(req, 'POST')
    if validation_response:
        return validation_response
    
    # Get CORS headers for this request
    request_origin: Optional[str] = req.headers.get('Origin')
    headers: CORSHeaders = get_cors_headers(request_origin)
    
    try:
        # Parse JSON data from request
        data: Optional[Union[MerchantInput, MultipleMerchantsRequest]] = req.get_json()
        
        if not data:
            return https_fn.Response(
                json.dumps({'error': 'No JSON data provided'}),
                status=HTTP_BAD_REQUEST,
                headers=headers,
                mimetype='application/json'
            )
        
        # Required fields for each pending merchant
        required_fields: List[str] = COLLECTION_REQUIRED_FIELDS[PENDING_MERCHANTS_COLLECTION]
        
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
        
        # Process merchants using helper function
        response_data: StoreMerchantsResponse = process_merchants_for_storage(
            merchants_to_process, 
            PENDING_MERCHANTS_COLLECTION,
            required_fields
        )
        
        # Update message to indicate these are pending merchants
        if response_data['success']:
            response_data['message'] = f'All {response_data["stored_successfully"]} pending merchant(s) stored successfully'
        else:
            response_data['message'] = f'Partially successful: {response_data["stored_successfully"]} of {response_data["total_merchants"]} pending merchants stored'
        
        # Determine status code
        status_code: int = HTTP_OK if response_data['success'] else HTTP_MULTI_STATUS
        
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
def approve_pending_merchant(req: https_fn.Request) -> https_fn.Response:
    """
    Cloud Function to approve pending merchants.
    Moves merchants from pending collection to regular merchant collection.
    Expects JSON body: {"merchant_ids": ["document_id1", "document_id2", ...]}
    """
    # Handle common request validation
    validation_response = handle_common_request_validation(req, 'POST')
    if validation_response:
        return validation_response
    
    # Get CORS headers for this request
    request_origin: Optional[str] = req.headers.get('Origin')
    headers: CORSHeaders = get_cors_headers(request_origin)
    
    try:
        # Parse JSON data from request
        data = req.get_json()
        
        if not data or 'merchant_ids' not in data:
            return https_fn.Response(
                json.dumps({'error': 'Missing required field: merchant_ids'}),
                status=HTTP_BAD_REQUEST,
                headers=headers,
                mimetype='application/json'
            )
        
        merchant_ids: List[str] = data['merchant_ids']
        
        if not isinstance(merchant_ids, list) or len(merchant_ids) == 0:
            return https_fn.Response(
                json.dumps({'error': 'merchant_ids must be a non-empty array of strings'}),
                status=HTTP_BAD_REQUEST,
                headers=headers,
                mimetype='application/json'
            )
        
        # Validate all merchant IDs are strings
        for merchant_id in merchant_ids:
            if not isinstance(merchant_id, str) or not merchant_id.strip():
                return https_fn.Response(
                    json.dumps({'error': 'All merchant_ids must be non-empty strings'}),
                    status=HTTP_BAD_REQUEST,
                    headers=headers,
                    mimetype='application/json'
                )
        
        # Get Firestore client
        db: firestore.Client = firestore.client()
        
        # Track results
        approved_merchants: List[dict] = []
        failed_merchants: List[dict] = []
        
        # Process each merchant ID
        for merchant_id in merchant_ids:
            try:
                # Get the pending merchant document
                pending_doc_ref: firestore.DocumentReference = db.collection(PENDING_MERCHANTS_COLLECTION).document(merchant_id)
                pending_doc: firestore.DocumentSnapshot = pending_doc_ref.get()
                
                if not pending_doc.exists:
                    failed_merchants.append({
                        'merchant_id': merchant_id,
                        'error': f'Pending merchant with ID {merchant_id} not found'
                    })
                    continue
                
                # Get the merchant data
                merchant_data_dict = pending_doc.to_dict()
                if not merchant_data_dict:
                    failed_merchants.append({
                        'merchant_id': merchant_id,
                        'error': 'Invalid merchant data'
                    })
                    continue
                
                # Prepare merchant data for regular collection (cast to Merchant type)
                merchant_data: Merchant = merchant_data_dict  # type: ignore
                
                # Use a transaction to ensure atomic operation
                transaction = db.transaction()
                
                @firestore.transactional
                def approve_merchant_transaction(transaction, pending_ref, regular_ref, merchant_data):
                    # Add to regular merchants collection
                    transaction.set(regular_ref, merchant_data)
                    # Remove from pending merchants collection
                    transaction.delete(pending_ref)
                
                # Execute the transaction
                regular_doc_ref: firestore.DocumentReference = db.collection(MERCHANTS_COLLECTION).document(merchant_id)
                approve_merchant_transaction(transaction, pending_doc_ref, regular_doc_ref, merchant_data)
                
                approved_merchants.append({
                    'merchant_id': merchant_id,
                    'message': f'Merchant {merchant_id} approved successfully'
                })
                
            except Exception as merchant_error:
                failed_merchants.append({
                    'merchant_id': merchant_id,
                    'error': str(merchant_error)
                })
        
        # Prepare response
        response = {
            'success': len(failed_merchants) == 0,
            'total_merchants': len(merchant_ids),
            'approved_successfully': len(approved_merchants),
            'failed_approvals': len(failed_merchants),
            'approved_merchants': approved_merchants,
            'failed_merchants': failed_merchants if failed_merchants else None,
            'action': 'approved'
        }
        
        if len(failed_merchants) == 0:
            response['message'] = f'All {len(approved_merchants)} merchant(s) approved successfully'
        else:
            response['message'] = f'Partially successful: {len(approved_merchants)} of {len(merchant_ids)} merchants approved'
        
        # Use multi-status if there were failures, otherwise OK
        status_code = HTTP_OK if len(failed_merchants) == 0 else HTTP_MULTI_STATUS
        
        return https_fn.Response(
            json.dumps(response),
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
def deny_pending_merchant(req: https_fn.Request) -> https_fn.Response:
    """
    Cloud Function to deny pending merchants.
    Deletes merchants from pending collection.
    Expects JSON body: {"merchant_ids": ["document_id1", "document_id2", ...]}
    """
    # Handle common request validation
    validation_response = handle_common_request_validation(req, 'POST')
    if validation_response:
        return validation_response
    
    # Get CORS headers for this request
    request_origin: Optional[str] = req.headers.get('Origin')
    headers: CORSHeaders = get_cors_headers(request_origin)
    
    try:
        # Parse JSON data from request
        data = req.get_json()
        
        if not data or 'merchant_ids' not in data:
            return https_fn.Response(
                json.dumps({'error': 'Missing required field: merchant_ids'}),
                status=HTTP_BAD_REQUEST,
                headers=headers,
                mimetype='application/json'
            )
        
        merchant_ids: List[str] = data['merchant_ids']
        
        if not isinstance(merchant_ids, list) or len(merchant_ids) == 0:
            return https_fn.Response(
                json.dumps({'error': 'merchant_ids must be a non-empty array of strings'}),
                status=HTTP_BAD_REQUEST,
                headers=headers,
                mimetype='application/json'
            )
        
        # Validate all merchant IDs are strings
        for merchant_id in merchant_ids:
            if not isinstance(merchant_id, str) or not merchant_id.strip():
                return https_fn.Response(
                    json.dumps({'error': 'All merchant_ids must be non-empty strings'}),
                    status=HTTP_BAD_REQUEST,
                    headers=headers,
                    mimetype='application/json'
                )
        
        # Get Firestore client
        db: firestore.Client = firestore.client()
        
        # Track results
        denied_merchants: List[dict] = []
        failed_merchants: List[dict] = []
        
        # Process each merchant ID
        for merchant_id in merchant_ids:
            try:
                # Get the pending merchant document
                pending_doc_ref: firestore.DocumentReference = db.collection(PENDING_MERCHANTS_COLLECTION).document(merchant_id)
                pending_doc: firestore.DocumentSnapshot = pending_doc_ref.get()
                
                if not pending_doc.exists:
                    failed_merchants.append({
                        'merchant_id': merchant_id,
                        'error': f'Pending merchant with ID {merchant_id} not found'
                    })
                    continue
                
                # Delete the pending merchant
                pending_doc_ref.delete()
                
                denied_merchants.append({
                    'merchant_id': merchant_id,
                    'message': f'Merchant {merchant_id} denied and removed successfully'
                })
                
            except Exception as merchant_error:
                failed_merchants.append({
                    'merchant_id': merchant_id,
                    'error': str(merchant_error)
                })
        
        # Prepare response
        response = {
            'success': len(failed_merchants) == 0,
            'total_merchants': len(merchant_ids),
            'denied_successfully': len(denied_merchants),
            'failed_denials': len(failed_merchants),
            'denied_merchants': denied_merchants,
            'failed_merchants': failed_merchants if failed_merchants else None,
            'action': 'denied'
        }
        
        if len(failed_merchants) == 0:
            response['message'] = f'All {len(denied_merchants)} merchant(s) denied and removed successfully'
        else:
            response['message'] = f'Partially successful: {len(denied_merchants)} of {len(merchant_ids)} merchants denied'
        
        # Use multi-status if there were failures, otherwise OK
        status_code = HTTP_OK if len(failed_merchants) == 0 else HTTP_MULTI_STATUS
        
        return https_fn.Response(
            json.dumps(response),
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
