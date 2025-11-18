"""
Review display utilities for Dating Popcorn Bot
Handles secure review display with image splitting and rate limiting
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from aiogram import Bot
from aiogram.types import Message, InputMediaPhoto, InputMedia, URLInputFile
from aiogram.exceptions import TelegramNetworkError, TelegramRetryAfter
from src.utils.localization import get_message

class ReviewDisplay:
    """Handles secure and user-friendly review display"""
    
    def __init__(self, bot: Bot):
        self.bot = bot
        self.rate_limit_delay = 1.0  # 1 second between messages to respect rate limits
    
    async def display_reviews(self, message: Message, reviews: List[Dict[str, Any]], language: str):
        """
        Display reviews with proper image handling and rate limiting
        
        Args:
            message: Original message to reply to
            reviews: List of review dictionaries
            language: User's language preference
        """
        if not reviews:
            await self._send_no_results(message, language)
            return
        
        await message.answer(
            self._get_results_header(len(reviews), language)
        )
        
        # Add delay to respect rate limits
        await asyncio.sleep(self.rate_limit_delay)
        
        for i, review in enumerate(reviews, 1):
            await self._display_single_review(message, review, i, language)
            
            # Add delay between reviews to respect rate limits
            if i < len(reviews):
                await asyncio.sleep(self.rate_limit_delay)
    
    async def _display_single_review(self, message: Message, review: Dict[str, Any], 
                                    review_number: int, language: str):
        """Display a single review following the specified pattern"""
        
        # Format the review text
        review_text = self._format_review_text(review, review_number, language)
        
        # Get the image URL and validate it
        image_url = review.get('image')
        
        # Check if image URL exists and is valid
        if image_url and isinstance(image_url, str):
            # Clean and validate the URL
            image_url = image_url.strip()
            
            # Remove any trailing whitespace or newlines
            image_url = image_url.rstrip()
            
            # Validate URL format - must be http or https
            if image_url and (image_url.startswith('http://') or image_url.startswith('https://')):
                # Validate it's a proper URL (basic check)
                if ' ' not in image_url and '\n' not in image_url:
                    await asyncio.sleep(self.rate_limit_delay)  # Rate limit delay
                    
                    try:
                        # Log attempt to send image
                        logger = logging.getLogger(__name__)
                        logger.info(f"Sending image for review '{review.get('name', 'Unknown')}': {image_url}")
                        
                        # Create URLInputFile - Telegram will fetch the image from this URL
                        # Cloudflare Worker URLs work perfectly with this approach
                        photo_file = URLInputFile(image_url)
                        
                        # Retry logic for network errors
                        max_retries = 3
                        retry_delay = 2  # seconds
                        
                        for attempt in range(max_retries):
                            try:
                                # Send the photo with caption
                                await message.answer_photo(
                                    photo=photo_file,
                                    caption=review_text,
                                    parse_mode='Markdown'
                                )
                                logger.info(f"✅ Successfully sent image for review '{review.get('name', 'Unknown')}' from URL: {image_url}")
                                return  # Success, exit early
                                
                            except TelegramRetryAfter as e:
                                # Rate limit - wait and retry
                                wait_time = e.retry_after
                                logger.warning(f"Rate limited, waiting {wait_time} seconds before retry {attempt + 1}/{max_retries}")
                                await asyncio.sleep(wait_time)
                                continue
                                
                            except TelegramNetworkError as e:
                                # Network error - retry with exponential backoff
                                if attempt < max_retries - 1:
                                    wait_time = retry_delay * (2 ** attempt)
                                    logger.warning(f"Network error (attempt {attempt + 1}/{max_retries}), retrying in {wait_time}s: {e}")
                                    await asyncio.sleep(wait_time)
                                    continue
                                else:
                                    # Last attempt failed
                                    logger.error(f"❌ Failed to send image after {max_retries} attempts: {e}")
                                    raise
                                
                            except Exception as e:
                                # Other errors - don't retry
                                logger.error(f"❌ Failed to send image (non-retryable error): {e}")
                                raise
                        
                    except Exception as e:
                        # Log the error for debugging
                        logger.error(f"❌ Failed to send image for review '{review.get('name', 'Unknown')}': {e}")
                        logger.error(f"Image URL: {image_url}")
                        logger.error(f"URL type: {type(image_url)}")
                        logger.exception("Full traceback:")
                        # Fall through to send text only as fallback
                else:
                    # URL contains invalid characters
                    logger = logging.getLogger(__name__)
                    logger.warning(f"Invalid image URL format (contains spaces/newlines) for review '{review.get('name', 'Unknown')}': {image_url}")
            else:
                # Invalid URL format
                logger = logging.getLogger(__name__)
                logger.warning(f"Image URL doesn't start with http:// or https:// for review '{review.get('name', 'Unknown')}': {image_url}")
        
        # If no image or image failed, send text only
        await message.answer(review_text, parse_mode='Markdown')
    
    def _format_review_text(self, review: Dict[str, Any], review_number: int, language: str) -> str:
        """Format review text following the specified pattern"""
        
        # Basic review info
        name = review.get('name', 'Unknown')
        content = review.get('content', '')
        distance = review.get('distance', 0)
        similarity = review.get('similarity')  # Face match similarity score (0-100)
        exact_address = review.get('exact_address')  # kept for future use; intentionally not displayed
        reviewer_username = review.get('reviewer_username')
        
        # Round up distance for security (2.3km -> 3km)
        import math
        rounded_distance = math.ceil(distance) if distance > 0 else 1
        
        # Build the review text following the pattern:
        # @username (of the reviewer) - only if available
        # Full Name (of the person being reviewed)
        # Review content
        # Distance
        # Similarity (if available, for image search results)
        lines = []
        
        
        # If you want to show the identifier in the future, uncomment below:
        # if exact_address:
        #     lines.append(f"📍 {exact_address}")
        
        # Add full name with bold formatting and emoji
        lines.append(f"👨‍💼 **{name}**")
        
                # Normalize reviewer username and add line if available
        if reviewer_username:
            normalized_username = reviewer_username.strip()
            if normalized_username and not normalized_username.startswith('@'):
                normalized_username = f"@{normalized_username}"
            if normalized_username:
                lines.append(f"👤 {normalized_username}")

        # Add review content with emoji
        lines.append(f"💬 {content}")
        
        # Add similarity score if available (for image search results)
        if similarity is not None:
            similarity_text = get_message(language, 'search.results.match_score', score=similarity / 100)
            lines.append(similarity_text)
        
        # Add distance with icon
        lines.append(f"📍 {rounded_distance}km away")
        
        return "\n".join(lines)
    
    def _get_results_header(self, count: int, language: str) -> str:
        """Get localized results header"""
        if count == 1:
            return get_message(language, 'search.results.found', count=count)
        else:
            return get_message(language, 'search.results.found', count=count)
    
    async def _send_no_results(self, message: Message, language: str):
        """Send no results message"""
        await message.answer(
            get_message(language, 'search.results.none_found')
        )

## Removed legacy create_mock_reviews as real search is implemented

def create_mock_image_reviews() -> List[Dict[str, Any]]:
    """Create mock image search reviews for testing (2 of 3 have images)"""
    return [
        {
            'name': 'Gonzalo Carlos Rodriguez',
            'content': 'Face recognition match. Very social and outgoing personality.',
            'distance': 2.1,
            # 'exact_address': '789 Pine St, Uptown',  # intentionally hidden from users
            'image': 'https://randomuser.me/api/portraits/men/78.jpg'  # Real image URL
        },
        {
            'name': 'Rodriguez Andreas Gonzalo',
            'content': 'Recognized from your photo. Stood me up twice without any explanation. Very unreliable.',
            'distance': 3.2,
            # 'exact_address': None,  # intentionally hidden from users
            'image': None  # No image
        },
        {
            'name': 'Elena Maria Rodriguez',
            'content': 'Similar facial features detected. Known for being honest and direct.',
            'distance': 4.7,
            # 'exact_address': '321 Elm St, Westside',  # intentionally hidden from users
            'image': 'https://randomuser.me/api/portraits/men/10.jpg'  # Real image URL
        }
    ]
