"""
Users router for Dating Popcorn Bot API
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List
import logging

from src.database.simple_db import get_user, get_all_users
from src.api.models import UserResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/", response_model=List[UserResponse])
async def get_all_users_endpoint(
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """Get all users (location can be null)"""
    try:
        logger.info(f"API: Getting all users (limit={limit}, offset={offset})")
        
        users = await get_all_users(limit, offset)
        
        # Convert users to response format
        user_responses = []
        for user in users:
            location_data = None
            if user.location:
                lat, lon = user.get_location()
                if lat is not None and lon is not None:
                    location_data = {"latitude": lat, "longitude": lon}
            
            user_responses.append(UserResponse(
                id=user.id,
                username=user.username,
                location=location_data,
                is_banned=user.is_banned,
                created_at=user.created_at,
                updated_at=user.updated_at
            ))
        
        logger.info(f"API: Returning {len(user_responses)} users")
        return user_responses
        
    except Exception as e:
        logger.error(f"API: Error getting users: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{user_id}", response_model=UserResponse)
async def get_user_endpoint(user_id: str):
    """Get specific user details"""
    try:
        logger.info(f"API: Getting user {user_id}")
        
        user = await get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Convert location data
        location_data = None
        if user.location:
            lat, lon = user.get_location()
            if lat is not None and lon is not None:
                location_data = {"latitude": lat, "longitude": lon}
        
        return UserResponse(
            id=user.id,
            username=user.username,
            location=location_data,
            is_banned=user.is_banned,
            created_at=user.created_at,
            updated_at=user.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"API: Error getting user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
