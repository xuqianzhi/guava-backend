# Welcome to Cloud Functions for Firebase for Python!
# To get started, simply uncomment the below code or create your own.
# Deploy with `firebase deploy`

from firebase_functions import https_fn
from firebase_functions.options import set_global_options
from firebase_admin import initialize_app, firestore
from datetime import datetime
from typing import List, Optional, Union
import json

from constants import (
    # TypedDict classes
    ContactInput,
    ContactData,
    ContactResponse,
    StoredContactResult,
    ContactError,
    SingleContactRequest,
    MultipleContactsRequest,
    StoreContactResponse,
    GetContactsResponse,
    CORSHeaders,
    # Constants
    CONTACTS_COLLECTION,
    COLLECTION_REQUIRED_FIELDS,
    MAX_INSTANCES,
    HTTP_OK,
    HTTP_NO_CONTENT,
    HTTP_MULTI_STATUS,
    HTTP_BAD_REQUEST,
    HTTP_METHOD_NOT_ALLOWED,
    HTTP_INTERNAL_SERVER_ERROR,
    ALLOWED_ORIGINS,
    CORS_ALLOW_METHODS,
    CORS_ALLOW_HEADERS
)

from utils import get_cors_headers, is_origin_allowed

# For cost control, you can set the maximum number of containers that can be
# running at the same time. This helps mitigate the impact of unexpected
# traffic spikes by instead downgrading performance. This limit is a per-function
# limit. You can override the limit for each function using the max_instances
# parameter in the decorator, e.g. @https_fn.on_request(max_instances=5).
set_global_options(max_instances=MAX_INSTANCES)

# Initialize Firebase Admin SDK
initialize_app()

@https_fn.on_request()
def store_contact(req: https_fn.Request) -> https_fn.Response:
    """
    Cloud Function to store contact information in Firestore.
    Accepts either:
    1. Single contact: JSON object with name, email, phone, company, industry, message
    2. Multiple contacts: JSON object with "contacts" array containing contact objects
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
        data: Optional[Union[SingleContactRequest, MultipleContactsRequest]] = req.get_json()
        
        if not data:
            return https_fn.Response(
                json.dumps({'error': 'No JSON data provided'}),
                status=HTTP_BAD_REQUEST,
                headers=headers,
                mimetype='application/json'
            )
        
        # Required fields for each contact
        required_fields: List[str] = COLLECTION_REQUIRED_FIELDS[CONTACTS_COLLECTION]
        
        # Check if this is a batch request (contains "contacts" array) or single contact
        if 'contacts' in data:
            # Multiple contacts
            contacts_to_process: List[ContactInput] = data['contacts']  # type: ignore
            if not isinstance(contacts_to_process, list):
                return https_fn.Response(
                    json.dumps({'error': 'contacts field must be an array'}),
                    status=HTTP_BAD_REQUEST,
                    headers=headers,
                    mimetype='application/json'
                )
            
            if len(contacts_to_process) == 0:
                return https_fn.Response(
                    json.dumps({'error': 'contacts array cannot be empty'}),
                    status=HTTP_BAD_REQUEST,
                    headers=headers,
                    mimetype='application/json'
                )
        else:
            # Single contact - wrap in array for uniform processing
            contacts_to_process = [data]  # type: ignore
        
        # Validate all contacts before processing any
        validation_errors: List[str] = []
        for i, contact in enumerate(contacts_to_process):
            missing_fields: List[str] = [field for field in required_fields if field not in contact or not contact[field]]
            if missing_fields:
                validation_errors.append(f"Contact {i+1}: Missing required fields: {', '.join(missing_fields)}")
        
        if validation_errors:
            return https_fn.Response(
                json.dumps({'error': validation_errors}),
                status=HTTP_BAD_REQUEST,
                headers=headers,
                mimetype='application/json'
            )
        
        # Process all contacts
        current_datetime: datetime = datetime.now()
        stored_contacts: List[StoredContactResult] = []
        errors: List[ContactError] = []
        
        for i, contact in enumerate(contacts_to_process):
            try:
                doc_id: str = contact['email']
                
                # Check if document already exists
                doc_ref: firestore.DocumentReference = db.collection(CONTACTS_COLLECTION).document(doc_id)
                existing_doc: firestore.DocumentSnapshot = doc_ref.get()
                
                # Prepare new message list
                new_message: str = contact['message']
                
                if existing_doc.exists:
                    # Document exists - get existing messages and append new one
                    existing_data: Optional[dict] = existing_doc.to_dict()
                    existing_messages: Union[List[str], str, None] = existing_data.get('message', []) if existing_data else []
                    
                    # Ensure existing_messages is a list (handle legacy single string messages)
                    if isinstance(existing_messages, str):
                        existing_messages_list: List[str] = [existing_messages]
                    elif isinstance(existing_messages, list):
                        existing_messages_list = existing_messages
                    else:
                        existing_messages_list = []
                    
                    # Append new message to existing list
                    updated_messages: List[str] = existing_messages_list + [new_message]
                else:
                    # New document - create new message list
                    updated_messages = [new_message]
                
                # Prepare document data (override all fields, but append to messages)
                contact_data: ContactData = {
                    'name': contact['name'],
                    'email': contact['email'],
                    'phone': contact.get('phone', ''),  # Default to empty string if not provided
                    'company': contact.get('company', ''),  # Default to empty string if not provided
                    'industry': contact.get('industry', ''),  # Default to empty string if not provided
                    'message': updated_messages,  # Now a list of strings
                    'datetime': current_datetime
                }
                
                # Store in Firestore with custom document ID
                doc_ref.set(contact_data)
                
                stored_contact_result: StoredContactResult = {
                    'email': contact['email'],
                    'document_id': doc_id,
                    'status': 'success',
                    'action': 'updated' if existing_doc.exists else 'created',
                    'total_messages': len(updated_messages)
                }
                stored_contacts.append(stored_contact_result)
                
            except Exception as contact_error:
                error_entry: ContactError = {
                    'contact_index': i + 1,
                    'email': contact.get('email', 'unknown'),
                    'error': str(contact_error)
                }
                errors.append(error_entry)
        
        # Prepare response
        response_data: StoreContactResponse = {
            'success': len(errors) == 0,
            'total_contacts': len(contacts_to_process),
            'stored_successfully': len(stored_contacts),
            'stored_contacts': stored_contacts,
            'message': f'All {len(stored_contacts)} contact(s) stored successfully',
            'errors': None
        }
        
        if errors:
            response_data['errors'] = errors
            response_data['message'] = f'Partially successful: {len(stored_contacts)} of {len(contacts_to_process)} contacts stored'
        
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
def get_contacts(req: https_fn.Request) -> https_fn.Response:
    """
    Cloud Function to retrieve contact information from Firestore.
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
        
        # Get email filter from query parameters
        emails_param: Optional[str] = req.args.get('emails')
        
        contacts: List[ContactResponse] = []
        
        if emails_param:
            # Parse comma-separated email list
            email_list: List[str] = [email.strip() for email in emails_param.split(',') if email.strip()]
            
            if email_list:
                # Fetch specific documents by email (document ID)
                for email in email_list:
                    doc_ref: firestore.DocumentReference = db.collection(CONTACTS_COLLECTION).document(email)
                    doc: firestore.DocumentSnapshot = doc_ref.get()
                    
                    if doc.exists:
                        contact_data_dict: Optional[dict] = doc.to_dict()
                        if contact_data_dict:
                            # Convert datetime to string for JSON serialization
                            if 'datetime' in contact_data_dict and contact_data_dict['datetime']:
                                contact_data_dict['datetime'] = contact_data_dict['datetime'].isoformat()
                            contact_data_dict['id'] = doc.id
                            # Cast to ContactResponse type
                            contact_response: ContactResponse = contact_data_dict  # type: ignore
                            contacts.append(contact_response)
            else:
                return https_fn.Response(
                    json.dumps({'error': 'Invalid emails parameter - no valid emails found'}),
                    status=HTTP_BAD_REQUEST,
                    headers=headers,
                    mimetype='application/json'
                )
        else:
            # No filter - retrieve all contacts from Firestore
            contacts_ref: firestore.CollectionReference = db.collection(CONTACTS_COLLECTION)
            docs: firestore.Generator = contacts_ref.stream()
            
            for doc in docs:
                contact_data_dict = doc.to_dict()
                if contact_data_dict:
                    # Convert datetime to string for JSON serialization
                    if 'datetime' in contact_data_dict and contact_data_dict['datetime']:
                        contact_data_dict['datetime'] = contact_data_dict['datetime'].isoformat()
                    contact_data_dict['id'] = doc.id
                    # Cast to ContactResponse type
                    contact_response = contact_data_dict  # type: ignore
                    contacts.append(contact_response)
        
        response: GetContactsResponse = {
            'success': True,
            'contacts': contacts,
            'count': len(contacts),
            'filtered': bool(emails_param)
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