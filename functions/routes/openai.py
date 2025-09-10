"""
OpenAI routes for Firebase Functions
"""

from firebase_functions import https_fn
from typing import List, Optional, Dict, Any
import json
import time
import json
import os
import random
import time

from openai import OpenAI

from constants.constants import (
    CORSHeaders,
    HTTP_OK,
    HTTP_BAD_REQUEST,
    HTTP_INTERNAL_SERVER_ERROR,
    HTTP_METHOD_NOT_ALLOWED
)

from constants.openai import (
    SocialMediaPostRequest,
    SocialMediaPostResponse,
    SocialMediaPostError,
    DishReview,
    OPENAI_MODEL,
    MAX_TOKENS,
    TEMPERATURE,
    MIN_RATING,
    MAX_RATING,
    MAX_DISHES
)

from utils import get_cors_headers, is_origin_allowed

def clean_social_media_post(raw_post: str) -> str:
    """
    Clean up the social media post by removing markdown formatting and fixing escape sequences
    """
    # Handle the literal \n characters in the string (not actual newlines)
    cleaned = raw_post.replace('\\n', '\n')  # Convert literal \n to actual newlines
    cleaned = cleaned.replace('\\t', '\t')
    cleaned = cleaned.replace('\\"', '"')
    cleaned = cleaned.replace("\\'", "'")
    
    # Remove markdown formatting
    cleaned = cleaned.replace('**', '')  # Remove bold markers
    cleaned = cleaned.replace('*', '')   # Remove italic markers  
    cleaned = cleaned.replace('__', '')  # Remove underline markers
    cleaned = cleaned.replace('`', '')   # Remove code markers
    
    # Convert bullet points
    cleaned = cleaned.replace('• ', '- ')
    
    # Now we have proper newlines, so format it nicely
    lines = []
    for line in cleaned.split('\n'):
        line = line.strip()
        if line:  # Only keep non-empty lines
            lines.append(line)
    
    # Join with actual newlines
    result = '\n \n'.join(lines)
    return result

def create_social_media_prompt(restaurant_name: str, dishes: List[DishReview], dining_experience: Dict[str, Any]) -> str:
    """
    Create a prompt for OpenAI to generate a social media post
    """
    prompt = f"Create an engaging social media post about a dining experience at {restaurant_name}. "
    
    prompt += "Here are the dishes with ratings and personal thoughts:\n\n"
    
    # Add dining experience details
    if dining_experience:
        prompt += f"\nDining experience details:\n"
        for key, value in dining_experience.items():
            # Format key to be more readable (convert underscores to spaces, capitalize)
            formatted_key = key.replace('_', ' ').title()
            prompt += f"• {formatted_key}: {value}\n"

    for dish in dishes:
        prompt += f"• {dish['name']} ({dish['rating']}/10): {dish['review']}\n"
    
    # Add timestamp to prevent caching (invisible to output)
    prompt += f"\n[Internal timestamp: {int(time.time())}]\n"
    
    prompt += f"""
        Please create a social media post for restaurant that:
        1. Begins the post by referring to "Dining experience details", create 2-4 sentences of describing the dining scenario like a story telling
        2. Then rate and describe dishes as bullet point
        3. End by sharing 1 sentence of personal thoughts
        4. Includes 2-3 relevant hashtags at the end
        5. Format as plain text only - NO markdown, NO bullet symbols, NO special formatting. Keep it simple and copy-pastable for social media
        Return only the social media post text, nothing else.
    """
    
    return prompt

@https_fn.on_request()
def generate_social_media_post(req: https_fn.Request) -> https_fn.Response:
    """
    Generate a social media post based on restaurant dishes and ratings
    
    POST /generate_social_media_post
    Body: {
        "restaurant_name": "Restaurant Name",
        "dishes": [
            {
                "name": "Dish Name",
                "rating": 8,
                "review": "User's personal thoughts about the dish"
            }
        ],
        "dining_experience": {
            "occasion": "date night",
            "atmosphere": "romantic",
            "service_quality": "excellent",
            "group_size": "couple",
            "overall_rating": 8
        }
    }
    """
    
    # Get request origin for CORS
    request_origin: Optional[str] = req.headers.get('Origin')
    headers: CORSHeaders = get_cors_headers(request_origin)
    
    # Handle preflight requests
    if req.method == 'OPTIONS':
        return https_fn.Response(
            '',
            status=200,
            headers=headers
        )
    
    # Only allow POST requests
    if req.method != 'POST':
        error_response: SocialMediaPostError = {
            'success': False,
            'error': f'Method {req.method} not allowed. Use POST.',
            'error_code': 'METHOD_NOT_ALLOWED'
        }
        return https_fn.Response(
            json.dumps(error_response),
            status=HTTP_METHOD_NOT_ALLOWED,
            headers=headers,
            mimetype='application/json'
        )
    
    # Check origin authorization
    if not is_origin_allowed(request_origin):
        error_response = {
            'success': False,
            'error': 'Unauthorized origin',
            'error_code': 'UNAUTHORIZED_ORIGIN'
        }
        return https_fn.Response(
            json.dumps(error_response),
            status=HTTP_BAD_REQUEST,
            headers=headers,
            mimetype='application/json'
        )
    
    try:
        # Parse request body
        request_data: SocialMediaPostRequest = req.get_json()
        if not request_data:
            error_response = {
                'success': False,
                'error': 'Request body is required',
                'error_code': 'MISSING_BODY'
            }
            return https_fn.Response(
                json.dumps(error_response),
                status=HTTP_BAD_REQUEST,
                headers=headers,
                mimetype='application/json'
            )
        
        # Validate required fields
        if 'restaurant_name' not in request_data:
            error_response = {
                'success': False,
                'error': 'restaurant_name is required',
                'error_code': 'MISSING_RESTAURANT_NAME'
            }
            return https_fn.Response(
                json.dumps(error_response),
                status=HTTP_BAD_REQUEST,
                headers=headers,
                mimetype='application/json'
            )
        
        if 'dishes' not in request_data or not isinstance(request_data['dishes'], list):
            error_response = {
                'success': False,
                'error': 'dishes array is required',
                'error_code': 'MISSING_DISHES'
            }
            return https_fn.Response(
                json.dumps(error_response),
                status=HTTP_BAD_REQUEST,
                headers=headers,
                mimetype='application/json'
            )
        
        if len(request_data['dishes']) == 0:
            error_response = {
                'success': False,
                'error': 'At least one dish is required',
                'error_code': 'EMPTY_DISHES'
            }
            return https_fn.Response(
                json.dumps(error_response),
                status=HTTP_BAD_REQUEST,
                headers=headers,
                mimetype='application/json'
            )
        
        if len(request_data['dishes']) > MAX_DISHES:
            error_response = {
                'success': False,
                'error': f'Maximum {MAX_DISHES} dishes allowed',
                'error_code': 'TOO_MANY_DISHES'
            }
            return https_fn.Response(
                json.dumps(error_response),
                status=HTTP_BAD_REQUEST,
                headers=headers,
                mimetype='application/json'
            )
        
        # Validate each dish
        for i, dish in enumerate(request_data['dishes']):
            if not isinstance(dish, dict):
                error_response = {
                    'success': False,
                    'error': f'Dish {i+1} must be an object',
                    'error_code': 'INVALID_DISH_FORMAT'
                }
                return https_fn.Response(
                    json.dumps(error_response),
                    status=HTTP_BAD_REQUEST,
                    headers=headers,
                    mimetype='application/json'
                )
            
            required_dish_fields = ['name', 'rating', 'review']
            for field in required_dish_fields:
                if field not in dish:
                    error_response = {
                        'success': False,
                        'error': f'Dish {i+1} missing required field: {field}',
                        'error_code': 'MISSING_DISH_FIELD'
                    }
                    return https_fn.Response(
                        json.dumps(error_response),
                        status=HTTP_BAD_REQUEST,
                        headers=headers,
                        mimetype='application/json'
                    )
            
            # Validate rating
            if not isinstance(dish['rating'], int) or dish['rating'] < MIN_RATING or dish['rating'] > MAX_RATING:
                error_response = {
                    'success': False,
                    'error': f'Dish {i+1} rating must be an integer between {MIN_RATING} and {MAX_RATING}',
                    'error_code': 'INVALID_RATING'
                }
                return https_fn.Response(
                    json.dumps(error_response),
                    status=HTTP_BAD_REQUEST,
                    headers=headers,
                    mimetype='application/json'
                )
        
        # Validate dining_experience
        if 'dining_experience' not in request_data:
            error_response = {
                'success': False,
                'error': 'dining_experience is required',
                'error_code': 'MISSING_DINING_EXPERIENCE'
            }
            return https_fn.Response(
                json.dumps(error_response),
                status=HTTP_BAD_REQUEST,
                headers=headers,
                mimetype='application/json'
            )
        
        if not isinstance(request_data['dining_experience'], dict):
            error_response = {
                'success': False,
                'error': 'dining_experience must be a dictionary',
                'error_code': 'INVALID_DINING_EXPERIENCE'
            }
            return https_fn.Response(
                json.dumps(error_response),
                status=HTTP_BAD_REQUEST,
                headers=headers,
                mimetype='application/json'
            )
        
        # Extract data
        restaurant_name: str = request_data['restaurant_name'].strip()
        dishes: List[DishReview] = request_data['dishes']
        dining_experience: Dict[str, Any] = request_data['dining_experience']
        
        # Get OpenAI API key from environment
        openai_api_key = os.environ.get('OPENAI_API_KEY')
        if not openai_api_key:
            error_response = {
                'success': False,
                'error': 'OpenAI API key not configured',
                'error_code': 'MISSING_API_KEY'
            }
            return https_fn.Response(
                json.dumps(error_response),
                status=HTTP_INTERNAL_SERVER_ERROR,
                headers=headers,
                mimetype='application/json'
            )
        
        # Initialize OpenAI client
        client = OpenAI(api_key=openai_api_key)
        
        # Create prompt
        prompt = create_social_media_prompt(restaurant_name, dishes, dining_experience)
        
        # Call OpenAI API with anti-caching measures
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You are a social media expert who creates engaging, authentic restaurant posts for food lovers."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            max_tokens=MAX_TOKENS,
            temperature=TEMPERATURE,
            seed=random.randint(1, 1000000),  # Random seed to prevent caching
            top_p=0.95  # Add some randomness to token selection
        )
        
        # Extract and clean the generated post
        raw_post = response.choices[0].message.content.strip()
        social_media_post = clean_social_media_post(raw_post)

        print("pde ", social_media_post)
        
        # Extract hashtags (simple extraction of words starting with #)
        hashtags = [word for word in social_media_post.split() if word.startswith('#')]
        
        # Create response
        success_response: SocialMediaPostResponse = {
            'success': True,
            'social_media_post': social_media_post,
            'character_count': len(social_media_post),
            'hashtags': hashtags
        }
        
        return https_fn.Response(
            json.dumps(success_response),
            status=HTTP_OK,
            headers=headers,
            mimetype='application/json'
        )
        
    except Exception as e:
        error_response = {
            'success': False,
            'error': f'Internal server error: {str(e)}',
            'error_code': 'INTERNAL_ERROR'
        }
        return https_fn.Response(
            json.dumps(error_response),
            status=HTTP_INTERNAL_SERVER_ERROR,
            headers=headers,
            mimetype='application/json'
        )
