"""
Review display utilities for Dating Popcorn Bot
Handles secure review display with image splitting and rate limiting
"""

import asyncio
from typing import List, Dict, Any, Optional
from aiogram import Bot
from aiogram.types import Message, InputMediaPhoto, InputMedia

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
        
        # If review has an image, send it with caption
        if review.get('image'):  # image is now an optional string
            await asyncio.sleep(self.rate_limit_delay)  # Rate limit delay
            
            # Get the single image URL
            image_url = review['image']
            try:
                # Send image with caption containing all review info
                await message.answer_photo(
                    photo=image_url, 
                    caption=review_text
                )
            except Exception as e:
                # If image fails, send text only as fallback
                await message.answer(review_text)
        else:
            # If no image, send text only
            await message.answer(review_text)
    
    def _format_review_text(self, review: Dict[str, Any], review_number: int, language: str) -> str:
        """Format review text following the specified pattern"""
        
        # Basic review info
        name = review.get('name', 'Unknown')
        content = review.get('content', '')
        distance = review.get('distance', 0)
        exact_address = review.get('exact_address')  # Address of the person who wrote the review
        
        # Round distance for security (2.3km -> 2km)
        rounded_distance = round(distance)
        
        # Build the review text following the pattern:
        # @username (of the reviewer) - only if available
        # Full Name (of the person being reviewed)
        # Review content
        # Distance
        lines = []
        
        # Add social handle of the reviewer at the top (if available)
        if exact_address:
            lines.append(f"📍 {exact_address}")
        
        # Add full name with bold formatting and emoji
        lines.append(f"👨‍💼 **{name}**")
        
        # Add review content with emoji
        lines.append(f"💬 {content}")
        
        # Add distance with icon
        lines.append(f"📍 {rounded_distance}km away")
        
        return "\n".join(lines)
    
    def _get_results_header(self, count: int, language: str) -> str:
        """Get localized results header"""
        from src.utils.localization import get_message
        
        if count == 1:
            return get_message(language, 'search.results.found', count=count)
        else:
            return get_message(language, 'search.results.found', count=count)
    
    async def _send_no_results(self, message: Message, language: str):
        """Send no results message"""
        from src.utils.localization import get_message
        
        await message.answer(
            get_message(language, 'search.results.none_found')
        )

def create_mock_reviews() -> List[Dict[str, Any]]:
    """Create mock reviews for testing with proper structure (2 of 3 have images)"""
    return [
        {
            'name': 'Carlos Andres Rodriguez',
            'content': 'He is a very nice person.',
            'distance': 1.3,
            'exact_address': '123 Main St, Downtown',  # Address of the person who wrote the review
            'image': 'https://randomuser.me/api/portraits/men/78.jpg'  # Real image URL
        },
        {
            'name': 'Maria Elena Gonzalo', 
            'content': 'She was constantly lying and manipulative. Stay away!',
            'distance': 2.3,
            'exact_address': None,  # No address available for this reviewer
            'image': None  # No image
        },
        {
            'name': 'Andreas Rodriguez Gonzalo',
            'content': 'He was rude to waiters and only talked about himself. Not recommended.',
            'distance': 5.1,
            'exact_address': '456 Oak Ave, Midtown',  # Address of the person who wrote the review
            'image': 'https://randomuser.me/api/portraits/men/10.jpg'  # Real image URL
        }
    ]

def create_mock_image_reviews() -> List[Dict[str, Any]]:
    """Create mock image search reviews for testing (2 of 3 have images)"""
    return [
        {
            'name': 'Gonzalo Carlos Rodriguez',
            'content': 'Face recognition match. Very social and outgoing personality.',
            'distance': 2.1,
            'exact_address': '789 Pine St, Uptown',  # Address of the person who wrote the review
            'image': 'https://randomuser.me/api/portraits/men/78.jpg'  # Real image URL
        },
        {
            'name': 'Rodriguez Andreas Gonzalo',
            'content': 'Recognized from your photo. Stood me up twice without any explanation. Very unreliable.',
            'distance': 3.2,
            'exact_address': None,  # No address available for this reviewer
            'image': None  # No image
        },
        {
            'name': 'Elena Maria Rodriguez',
            'content': 'Similar facial features detected. Known for being honest and direct.',
            'distance': 4.7,
            'exact_address': '321 Elm St, Westside',  # Address of the person who wrote the review
            'image': 'https://randomuser.me/api/portraits/men/10.jpg'  # Real image URL
        }
    ]
