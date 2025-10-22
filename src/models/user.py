"""
User-related data models for Dating Popcorn Bot
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any, Tuple
from datetime import datetime

@dataclass
class User:
    """User data structure matching database schema"""
    telegram_id: int
    first_name: str
    last_name: Optional[str] = None
    location: Optional[Tuple[float, float]] = None  # (latitude, longitude) for PostGIS POINT
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()
    
    def set_location(self, latitude: float, longitude: float):
        """Set user location coordinates"""
        self.location = (latitude, longitude)
        self.updated_at = datetime.now()
    
    def get_location(self) -> Optional[Tuple[float, float]]:
        """Get user location coordinates"""
        return self.location
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert user to dictionary"""
        return {
            'telegram_id': self.telegram_id,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'location': self.location,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'User':
        """Create User from dictionary"""
        return cls(
            telegram_id=data['telegram_id'],
            first_name=data['first_name'],
            last_name=data.get('last_name'),
            location=data.get('location'),
            created_at=datetime.fromisoformat(data['created_at']) if data.get('created_at') else None,
            updated_at=datetime.fromisoformat(data['updated_at']) if data.get('updated_at') else None
        )
