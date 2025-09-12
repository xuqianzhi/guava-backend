"""
OpenAI-related constants and TypedDict definitions
"""

from typing import TypedDict, List, Optional, Dict, Any

class DishReview(TypedDict):
    """Individual dish review structure"""
    name: str
    rating: int  # 1-10 scale
    review: str  # User's personal thoughts/opinion about the dish

class SocialMediaPostRequest(TypedDict):
    """Request structure for generating social media posts"""
    restaurant_name: str
    dishes: List[DishReview]
    dining_experience: Dict[str, Any]  # Arbitrary key-value pairs describing the dining experience

class SocialMediaPostResponse(TypedDict):
    """Response structure for social media post generation"""
    success: bool
    social_media_post: str  # Clean, human-readable version
    raw_post: str  # Original response from OpenAI
    character_count: int
    hashtags: List[str]

class SocialMediaPostError(TypedDict):
    """Error structure for social media post generation"""
    success: bool
    error: str
    error_code: str

# OpenAI Configuration
OPENAI_MODEL = "gpt-5-nano"  # Using the more cost-effective model
MAX_TOKENS = 500
TEMPERATURE = 0.7  # Balance between creativity and consistency

# Social Media Post Constraints
MAX_POST_LENGTH = 280  # Twitter-like constraint
MIN_RATING = 1
MAX_RATING = 10
MAX_DISHES = 10  # Reasonable limit for a single post
