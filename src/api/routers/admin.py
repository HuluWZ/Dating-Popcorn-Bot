"""
Admin router for Dating Popcorn Bot API
"""

from fastapi import APIRouter, HTTPException
import logging

from src.database.simple_db import (
    get_user, get_user_stats, get_review_stats, 
    approve_review, reject_review
)
from src.api.models import (
    AdminStatsResponse, UserLocationResponse, ReviewActionResponse
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/stats", response_model=AdminStatsResponse)
async def get_admin_stats_endpoint():
    """Get comprehensive admin statistics (users and reviews)"""
    try:
        logger.info("API: Getting admin statistics")
        
        # Get user stats
        user_stats = await get_user_stats()
        
        # Get review stats
        review_stats = await get_review_stats()
        
        return AdminStatsResponse(
            users={
                "total_users": user_stats['total_users'],
                "users_with_location": user_stats['users_with_location'],
                "banned_users": user_stats['banned_users'],
                "active_users": user_stats['active_users']
            },
            reviews={
                "total": review_stats['total'],
                "approved": review_stats['approved'],
                "pending": review_stats['pending'],
                "rejected": review_stats['rejected']
            }
        )
        
    except Exception as e:
        logger.error(f"API: Error getting admin stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/users/{user_id}/location", response_model=UserLocationResponse)
async def get_user_location_endpoint(user_id: str):
    """Get specific user's location coordinates (admin endpoint)"""
    try:
        logger.info(f"API: Getting location for user {user_id}")
        
        user = await get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        if not user.location:
            raise HTTPException(status_code=404, detail="User has not shared location")
        
        lat, lon = user.get_location()
        if lat is None or lon is None:
            raise HTTPException(status_code=404, detail="Invalid location data")
        
        return UserLocationResponse(
            user_id=user_id,
            username=user.username,
            latitude=lat,
            longitude=lon,
            location_shared_at=user.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"API: Error getting user location: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reviews/{review_id}/approve", response_model=ReviewActionResponse)
async def approve_review_endpoint(review_id: str):
    """Approve a review (admin endpoint)"""
    try:
        logger.info(f"API: Approving review {review_id}")
        
        success = await approve_review(review_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Review not found or could not be approved")
        
        return ReviewActionResponse(
            message=f"Review {review_id} approved successfully",
            status="approved"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"API: Error approving review: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reviews/{review_id}/reject", response_model=ReviewActionResponse)
async def reject_review_endpoint(review_id: str):
    """Reject a review (admin endpoint)"""
    try:
        logger.info(f"API: Rejecting review {review_id}")
        
        success = await reject_review(review_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Review not found or could not be rejected")
        
        return ReviewActionResponse(
            message=f"Review {review_id} rejected successfully",
            status="rejected"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"API: Error rejecting review: {e}")
        raise HTTPException(status_code=500, detail=str(e))
