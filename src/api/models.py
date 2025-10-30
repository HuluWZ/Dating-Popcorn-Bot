"""
Pydantic models for Dating Popcorn Bot API
"""

from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime


class UserResponse(BaseModel):
    id: str
    username: Optional[str]
    location: Optional[Dict[str, float]]  # {"latitude": 40.7128, "longitude": -74.0060}
    is_banned: bool
    created_at: datetime
    updated_at: datetime


class ReviewerInfo(BaseModel):
    id: str
    username: Optional[str]
    location: Optional[Dict[str, float]]  # {"latitude": 40.7128, "longitude": -74.0060}


class ReviewResponse(BaseModel):
    id: str
    full_name: str
    content: str
    exact_address: Optional[str]
    reviewer_id: str
    reviewer: ReviewerInfo
    status: str
    image_url: Optional[str]
    created_at: datetime
    updated_at: datetime


class ReviewStatsResponse(BaseModel):
    total: int
    approved: int
    pending: int
    rejected: int


class UserStatsResponse(BaseModel):
    total_users: int
    users_with_location: int
    banned_users: int
    active_users: int


class AdminStatsResponse(BaseModel):
    users: UserStatsResponse
    reviews: ReviewStatsResponse


class ReviewActionResponse(BaseModel):
    message: str
    status: str


class UserLocationResponse(BaseModel):
    user_id: str
    username: Optional[str]
    latitude: float
    longitude: float
    location_shared_at: datetime


class UserActionResponse(BaseModel):
    message: str
    status: str
    user_id: str
    username: Optional[str]
    is_banned: bool


class AdminResponse(BaseModel):
    id: str
    full_name: Optional[str]
    email: str
    created_at: datetime


class AdminCreateRequest(BaseModel):
    full_name: Optional[str] = None
    email: str
    password: str


class AdminLoginRequest(BaseModel):
    email: str
    password: str


class AdminLoginResponse(BaseModel):
    success: bool
    message: str
    admin: Optional[AdminResponse] = None
