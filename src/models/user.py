"""
User-related data models for Dating Popcorn Bot
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any
from datetime import datetime

@dataclass
class UserLocation:
    """User location data"""
    user_id: int
    latitude: float
    longitude: float
    timestamp: datetime
    city: Optional[str] = None
    country: Optional[str] = None

@dataclass
class User:
    """User data structure"""
    user_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    language: str = 'en'
    location: Optional[UserLocation] = None
    created_at: datetime = None
    is_banned: bool = False
    last_activity: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.last_activity is None:
            self.last_activity = datetime.now()
    
    def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert user to dictionary"""
        return {
            'user_id': self.user_id,
            'username': self.username,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'language': self.language,
            'location': self.location.__dict__ if self.location else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'is_banned': self.is_banned,
            'last_activity': self.last_activity.isoformat() if self.last_activity else None
        }
