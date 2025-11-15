"""
Admin router for Dating Popcorn Bot API
"""

from fastapi import APIRouter, HTTPException, Depends
import logging

from src.database.simple_db import (
    get_user, get_user_stats, get_review_stats, 
    approve_review, reject_review, ban_user, unban_user, delete_review
)
from src.api.models import (
    AdminStatsResponse, UserLocationResponse, ReviewActionResponse, UserActionResponse
)
from src.api.auth import get_current_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/stats", response_model=AdminStatsResponse)
async def get_admin_stats_endpoint(current_admin = Depends(get_current_admin)):
    """Get comprehensive admin statistics (users and reviews) - requires authentication"""
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
async def get_user_location_endpoint(user_id: str, current_admin = Depends(get_current_admin)):
    """Get specific user's location coordinates (admin endpoint) - requires authentication"""
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
async def approve_review_endpoint(review_id: str, current_admin = Depends(get_current_admin)):
    """Approve a review (admin endpoint) - requires authentication"""
    try:
        logger.info(f"API: Approving review {review_id}")
        
        success = await approve_review(review_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Review not found or could not be approved")
        
        return ReviewActionResponse(
            message=f"Review approved successfully",
            status="approved"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"API: Error approving review: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reviews/{review_id}/reject", response_model=ReviewActionResponse)
async def reject_review_endpoint(review_id: str, current_admin = Depends(get_current_admin)):
    """Reject a review (admin endpoint) - requires authentication"""
    try:
        logger.info(f"API: Rejecting review {review_id}")
        
        success = await reject_review(review_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Review not found or could not be rejected")
        
        return ReviewActionResponse(
            message=f"Review rejected successfully",
            status="rejected"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"API: Error rejecting review: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/users/{user_id}/ban", response_model=UserActionResponse)
async def ban_user_endpoint(user_id: str, current_admin = Depends(get_current_admin)):
    """Ban a user (admin endpoint) - requires authentication"""
    try:
        logger.info(f"API: Banning user {user_id}")
        
        # Get user info before banning for response
        user = await get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail=f"User with ID {user_id} not found")
        
        # Check if user is already banned
        if user.is_banned:
            raise HTTPException(status_code=400, detail=f"User {user_id} is already banned")
        
        success = await ban_user(user_id)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to ban user")
        
        return UserActionResponse(
            message=f"User banned successfully",
            status="banned",
            user_id=user_id,
            username=user.username,
            is_banned=True
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"API: Error banning user: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/users/{user_id}/unban", response_model=UserActionResponse)
async def unban_user_endpoint(user_id: str, current_admin = Depends(get_current_admin)):
    """Unban a user (admin endpoint) - requires authentication"""
    try:
        logger.info(f"API: Unbanning user {user_id}")
        
        # Get user info before unbanning for response
        user = await get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail=f"User with ID {user_id} not found")
        
        # Check if user is not banned
        if not user.is_banned:
            raise HTTPException(status_code=400, detail=f"User {user_id} is not banned")
        
        success = await unban_user(user_id)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to unban user")
        
        return UserActionResponse(
            message=f"User {user_id} unbanned successfully",
            status="unbanned",
            user_id=user_id,
            username=user.username,
            is_banned=False
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"API: Error unbanning user: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/reviews/{review_id}", response_model=ReviewActionResponse)
async def delete_review_endpoint(review_id: str, current_admin = Depends(get_current_admin)):
    """Delete a review (admin endpoint) - requires authentication"""
    try:
        logger.info(f"API: Deleting review {review_id}")
        
        success = await delete_review(review_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Review not found or could not be deleted")
        
        return ReviewActionResponse(
            message=f"Review deleted successfully",
            status="deleted"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"API: Error deleting review: {e}")
        raise HTTPException(status_code=500, detail=str(e))
