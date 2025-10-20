"""
Review-related data models for Dating Popcorn Bot
"""

from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class ReviewStatus(Enum):
    """Review approval status"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

@dataclass
class Review:
    """Review data structure"""
    id: str
    reviewer_user_id: int
    reviewer_location: Optional[Dict[str, Any]] = None
    subject_name: str = ""
    subject_phone: Optional[str] = None
    subject_instagram: Optional[str] = None
    review_text: str = ""
    images: List[str] = None
    status: ReviewStatus = ReviewStatus.PENDING
    created_at: datetime = None
    updated_at: datetime = None
    admin_notes: Optional[str] = None
    
    def __post_init__(self):
        if self.images is None:
            self.images = []
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()
    
    def approve(self, admin_notes: Optional[str] = None):
        """Approve the review"""
        self.status = ReviewStatus.APPROVED
        self.admin_notes = admin_notes
        self.updated_at = datetime.now()
    
    def reject(self, admin_notes: Optional[str] = None):
        """Reject the review"""
        self.status = ReviewStatus.REJECTED
        self.admin_notes = admin_notes
        self.updated_at = datetime.now()
    
    def is_approved(self) -> bool:
        """Check if review is approved"""
        return self.status == ReviewStatus.APPROVED
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert review to dictionary"""
        return {
            'id': self.id,
            'reviewer_user_id': self.reviewer_user_id,
            'reviewer_location': self.reviewer_location,
            'subject_name': self.subject_name,
            'subject_phone': self.subject_phone,
            'subject_instagram': self.subject_instagram,
            'review_text': self.review_text,
            'images': self.images,
            'status': self.status.value,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'admin_notes': self.admin_notes
        }

@dataclass
class SearchResult:
    """Search result data"""
    review: Review
    distance_km: float
    match_score: float = 0.0  # For image search results
    relevance_score: float = 0.0  # Overall relevance score
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert search result to dictionary"""
        return {
            'review': self.review.to_dict(),
            'distance_km': self.distance_km,
            'match_score': self.match_score,
            'relevance_score': self.relevance_score
        }
