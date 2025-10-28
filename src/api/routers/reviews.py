"""
Reviews router for Dating Popcorn Bot API
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List
import logging

from src.database.simple_db import get_all_reviews
from src.api.models import ReviewResponse, ReviewerInfo

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reviews", tags=["reviews"])


@router.get("/", response_model=List[ReviewResponse])
async def get_reviews(
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """Get reviews with pagination"""
    try:
        logger.info(f"API: Getting reviews (limit={limit}, offset={offset})")
        
        # Get all reviews with pagination
        filtered_reviews = await get_all_reviews(limit=limit, offset=offset)
        
        # Convert to response format
        review_responses = []
        for review in filtered_reviews:
            # Get reviewer information
            reviewer_location = None
            if review.reviewer and review.reviewer.location:
                lat, lon = review.reviewer.get_location()
                if lat is not None and lon is not None:
                    reviewer_location = {"latitude": lat, "longitude": lon}
            
            reviewer_info = ReviewerInfo(
                id=review.reviewer_id,
                username=review.reviewer.username if review.reviewer else None,
                location=reviewer_location
            )
            
            review_responses.append(ReviewResponse(
                id=str(review.id),
                full_name=review.full_name,
                content=review.content,
                exact_address=review.exact_address,
                reviewer_id=review.reviewer_id,
                reviewer=reviewer_info,
                status=review.status.value,
                image_url=review.image_url,
                created_at=review.created_at,
                updated_at=review.updated_at
            ))
        
        return review_responses
        
    except Exception as e:
        logger.error(f"API: Error getting reviews: {e}")
        raise HTTPException(status_code=500, detail=str(e))
