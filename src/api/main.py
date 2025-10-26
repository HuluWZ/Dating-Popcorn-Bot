"""
FastAPI application for Dating Popcorn Bot API
Provides endpoints to access users and reviews data
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List
import asyncio
import logging

from src.database.simple_db import (
    get_user, create_or_get_user, get_user_location, has_user_location,
    create_review, search_reviews_by_name, find_nearby_reviews,
    get_user_reviews, get_pending_reviews, get_review_stats
)
from src.database.models import User, Review, ReviewStatusEnum

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Dating Popcorn Bot API",
    description="API for accessing users and reviews data",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for API responses
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class UserResponse(BaseModel):
    id: str
    username: Optional[str]
    location: Optional[Dict[str, float]]  # {"latitude": 40.7128, "longitude": -74.0060}
    is_banned: bool
    created_at: datetime
    updated_at: datetime

class ReviewResponse(BaseModel):
    id: str
    full_name: str
    content: str
    social_handle: Optional[str]
    reviewer_id: str
    status: str
    images: Optional[List[str]]
    created_at: datetime
    updated_at: datetime

class ReviewStatsResponse(BaseModel):
    total: int
    approved: int
    pending: int
    rejected: int

# API Routes

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Dating Popcorn Bot API",
        "version": "1.0.0",
        "endpoints": {
            "users": "/users",
            "reviews": "/reviews",
            "stats": "/stats"
        }
    }

@app.get("/users/{user_id}", response_model=UserResponse)
async def get_user_by_id(user_id: str):
    """Get user by telegram ID"""
    try:
        logger.info(f"API: Getting user {user_id}")
        user = await get_user(user_id)
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Convert location to dict if exists
        location_dict = None
        if user.location:
            location_coords = user.get_location()
            if location_coords:
                location_dict = {
                    "latitude": location_coords[0],
                    "longitude": location_coords[1]
                }
        
        return UserResponse(
            id=user.id,
            username=user.username,
            location=location_dict,
            is_banned=user.is_banned,
            created_at=user.created_at,
            updated_at=user.updated_at
        )
    except Exception as e:
        logger.error(f"API: Error getting user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/users", response_model=List[UserResponse])
async def get_all_users(
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    with_location_only: bool = Query(False)
):
    """Get all users with pagination"""
    try:
        logger.info(f"API: Getting users (limit={limit}, offset={offset}, with_location_only={with_location_only})")
        
        # This would need to be implemented in simple_db.py
        # For now, return a placeholder
        raise HTTPException(status_code=501, detail="Get all users endpoint not implemented yet")
        
    except Exception as e:
        logger.error(f"API: Error getting users: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/reviews", response_model=List[ReviewResponse])
async def get_reviews(
    status: Optional[str] = Query(None, regex="^(PENDING|APPROVED|REJECTED)$"),
    reviewer_id: Optional[str] = Query(None),
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """Get reviews with optional filtering"""
    try:
        logger.info(f"API: Getting reviews (status={status}, reviewer_id={reviewer_id}, limit={limit}, offset={offset})")
        
        if reviewer_id:
            # Get reviews by specific user
            reviews = await get_user_reviews(reviewer_id)
        elif status == "PENDING":
            # Get pending reviews
            reviews = await get_pending_reviews()
        else:
            # This would need to be implemented in simple_db.py
            raise HTTPException(status_code=501, detail="Get all reviews endpoint not implemented yet")
        
        # Convert to response format
        review_responses = []
        for review in reviews:
            review_responses.append(ReviewResponse(
                id=str(review.id),
                full_name=review.full_name,
                content=review.content,
                social_handle=review.social_handle,
                reviewer_id=review.reviewer_id,
                status=review.status.value,
                images=review.images,
                created_at=review.created_at,
                updated_at=review.updated_at
            ))
        
        return review_responses
        
    except Exception as e:
        logger.error(f"API: Error getting reviews: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/reviews/{review_id}", response_model=ReviewResponse)
async def get_review_by_id(review_id: str):
    """Get specific review by ID"""
    try:
        logger.info(f"API: Getting review {review_id}")
        
        # This would need to be implemented in simple_db.py
        raise HTTPException(status_code=501, detail="Get review by ID endpoint not implemented yet")
        
    except Exception as e:
        logger.error(f"API: Error getting review {review_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stats", response_model=ReviewStatsResponse)
async def get_statistics():
    """Get database statistics"""
    try:
        logger.info("API: Getting statistics")
        stats = await get_review_stats()
        
        return ReviewStatsResponse(
            total=stats['total'],
            approved=stats['approved'],
            pending=stats['pending'],
            rejected=stats['rejected']
        )
        
    except Exception as e:
        logger.error(f"API: Error getting statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/search/reviews")
async def search_reviews(
    name: str = Query(..., min_length=2),
    latitude: Optional[float] = Query(None),
    longitude: Optional[float] = Query(None),
    radius_km: float = Query(10.0, ge=0.1, le=100.0)
):
    """Search reviews by name and optionally by location"""
    try:
        logger.info(f"API: Searching reviews for name='{name}', lat={latitude}, lng={longitude}, radius={radius_km}km")
        
        if latitude and longitude:
            # Search by name and location
            reviews = await find_nearby_reviews(latitude, longitude, radius_km)
            # Filter by name (this would need additional filtering logic)
            filtered_reviews = [r for r in reviews if name.lower() in r.full_name.lower()]
        else:
            # Search by name only
            filtered_reviews = await search_reviews_by_name(name)
        
        # Convert to response format
        review_responses = []
        for review in filtered_reviews:
            review_responses.append(ReviewResponse(
                id=str(review.id),
                full_name=review.full_name,
                content=review.content,
                social_handle=review.social_handle,
                reviewer_id=review.reviewer_id,
                status=review.status.value,
                images=review.images,
                created_at=review.created_at,
                updated_at=review.updated_at
            ))
        
        return review_responses
        
    except Exception as e:
        logger.error(f"API: Error searching reviews: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
