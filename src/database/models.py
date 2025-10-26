"""
Database models for Dating Popcorn Bot matching the provided schema
"""

from sqlalchemy import Column, String, Text, DateTime, Enum, ForeignKey, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
from geoalchemy2 import Geometry
from geoalchemy2.shape import to_shape, from_shape
from shapely.geometry import Point
import enum
from datetime import datetime
from typing import Optional, Tuple
import uuid

Base = declarative_base()

class ReviewStatusEnum(enum.Enum):
    """Review status enumeration"""
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"

class User(Base):
    """User model matching the provided schema with PostGIS location"""
    __tablename__ = 'users'
    
    # Primary key is telegram_id (string)
    id = Column(String, primary_key=True)  # telegram_id as string
    username = Column(String, nullable=True)
    location = Column(Geometry('POINT', srid=4326), nullable=True)  # PostGIS POINT geometry
    is_banned = Column(Boolean, default=False, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationship to reviews
    reviews = relationship("Review", back_populates="reviewer", cascade="all, delete-orphan")
    
    def set_location(self, latitude: float, longitude: float):
        """Set user location using PostGIS POINT (only once)"""
        if self.location is not None:
            raise ValueError("Location can only be set once and cannot be changed")
        
        point = Point(longitude, latitude)  # Note: PostGIS uses (longitude, latitude)
        self.location = from_shape(point, srid=4326)
        self.updated_at = datetime.now()
    
    def get_location(self) -> Optional[Tuple[float, float]]:
        """Get user location as (latitude, longitude) tuple"""
        if self.location is None:
            return None
        point = to_shape(self.location)
        return (point.y, point.x)  # Return as (latitude, longitude)
    
    @property
    def location_coords(self) -> Optional[Tuple[float, float]]:
        """Location property that returns (latitude, longitude) tuple"""
        return self.get_location()
    
    @location_coords.setter
    def location_coords(self, value: Tuple[float, float]):
        """Location property setter that accepts (latitude, longitude) tuple (only once)"""
        if value is not None:
            self.set_location(value[0], value[1])
    
    def ban(self):
        """Ban the user"""
        self.is_banned = True
        self.updated_at = datetime.utcnow()
    
    def unban(self):
        """Unban the user"""
        self.is_banned = False
        self.updated_at = datetime.utcnow()
    
    def is_banned_user(self) -> bool:
        """Check if user is banned"""
        return self.is_banned
    
    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', banned={self.is_banned})>"

class Review(Base):
    """Review model matching the provided schema"""
    __tablename__ = 'reviews'
    
    # UUID primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    full_name = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    social_handle = Column(String, nullable=True)
    reviewer_id = Column(String, ForeignKey('users.id'), nullable=False)  # References user.id (telegram_id)
    status = Column(Enum(ReviewStatusEnum), default=ReviewStatusEnum.PENDING, nullable=False)
    images = Column(JSON, nullable=True)  # Store image file IDs as JSON array
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationship to user
    reviewer = relationship("User", back_populates="reviews")
    
    def approve(self):
        """Approve the review"""
        self.status = ReviewStatusEnum.APPROVED
        self.updated_at = datetime.utcnow()
    
    def reject(self):
        """Reject the review"""
        self.status = ReviewStatusEnum.REJECTED
        self.updated_at = datetime.utcnow()
    
    def is_approved(self) -> bool:
        """Check if review is approved"""
        return self.status == ReviewStatusEnum.APPROVED
    
    def is_pending(self) -> bool:
        """Check if review is pending"""
        return self.status == ReviewStatusEnum.PENDING
    
    def is_rejected(self) -> bool:
        """Check if review is rejected"""
        return self.status == ReviewStatusEnum.REJECTED
    
    def __repr__(self):
        return f"<Review(id={self.id}, full_name='{self.full_name}', status='{self.status.value}')>"

# Utility functions for geographic queries
class GeographicQueries:
    """Utility class for geographic database queries"""
    
    @staticmethod
    def find_users_within_radius(session, center_lat: float, center_lng: float, radius_km: float):
        """Find users within a specified radius"""
        from sqlalchemy import text
        
        # Create a point for the center
        center_point = f"ST_GeomFromText('POINT({center_lng} {center_lat})', 4326)"
        
        # Query users within radius
        query = session.query(User).filter(
            User.location.isnot(None),
            text(f"ST_DWithin(location, {center_point}, {radius_km * 1000})")  # ST_DWithin uses meters
        )
        
        return query
    
    @staticmethod
    def calculate_distance_between_users(session, user1_id: int, user2_id: int):
        """Calculate distance between two users"""
        from sqlalchemy import text
        
        query = session.query(
            text("ST_Distance(u1.location, u2.location) / 1000")  # Convert to kilometers
        ).select_from(
            User.__table__.alias('u1')
        ).join(
            User.__table__.alias('u2')
        ).filter(
            text("u1.id = :user1_id AND u2.id = :user2_id")
        ).params(user1_id=user1_id, user2_id=user2_id)
        
        result = query.scalar()
        return result
    
    @staticmethod
    def find_nearby_reviews(session, user_lat: float, user_lng: float, radius_km: float, limit: int = 10):
        """Find reviews from users within a specified radius"""
        from sqlalchemy import text
        
        center_point = f"ST_GeomFromText('POINT({user_lng} {user_lat})', 4326)"
        
        query = session.query(Review).join(User).filter(
            User.location.isnot(None),
            Review.status == ReviewStatusEnum.APPROVED,
            text(f"ST_DWithin(User.location, {center_point}, {radius_km * 1000})")
        ).order_by(
            text(f"ST_Distance(User.location, {center_point})")
        ).limit(limit)
        
        return query
