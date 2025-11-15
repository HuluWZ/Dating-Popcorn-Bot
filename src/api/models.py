"""
Pydantic models for Dating Popcorn Bot API
"""

from pydantic import BaseModel, field_validator
from typing import Optional, List, Dict
from datetime import datetime
from .password_validator import validate_password_strength, get_password_requirements


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
    
    @field_validator('password')
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """
        Validate password meets strength requirements
        """
        is_valid, errors = validate_password_strength(v)
        if not is_valid:
            error_message = "Password does not meet strength requirements:\n" + "\n".join(f"• {error}" for error in errors)
            raise ValueError(error_message)
        return v
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v: str) -> str:
        """
        Basic email validation
        """
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, v):
            raise ValueError("Invalid email format")
        return v.lower().strip()


class AdminLoginRequest(BaseModel):
    email: str
    password: str


class AdminLoginResponse(BaseModel):
    success: bool
    message: str
    access_token: Optional[str] = None
    token_type: str = "bearer"
    admin: Optional[AdminResponse] = None


class AdminPasswordUpdateRequest(BaseModel):
    new_password: str
    
    @field_validator('new_password')
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """
        Validate password meets strength requirements
        """
        is_valid, errors = validate_password_strength(v)
        if not is_valid:
            error_message = "Password does not meet strength requirements:\n" + "\n".join(f"• {error}" for error in errors)
            raise ValueError(error_message)
        return v
