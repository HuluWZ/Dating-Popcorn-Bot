"""
Review-related data models for Dating Popcorn Bot
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

class ReviewStatus(Enum):
    """Review approval status matching database schema"""
    PENDING = "Pending"
    APPROVED = "Approved"
    REJECTED = "Rejected"

@dataclass
class Review:
    """Review data structure matching database schema"""
    id: Optional[int] = None  # SERIAL PRIMARY KEY (auto-generated)
    reviewer_telegram_id: int = 0
    full_name: str = ""  # Full name of the reviewed person
    exact_information: Optional[str] = None  # Phone number, Instagram handle, etc. (optional)
    review_content: str = ""  # Main review text
    images: List[str] = None  # List of image URLs/paths
    status: ReviewStatus = ReviewStatus.PENDING
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.images is None:
            self.images = []
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()
    
    def approve(self):
        """Approve the review"""
        self.status = ReviewStatus.APPROVED
        self.updated_at = datetime.now()
    
    def reject(self):
        """Reject the review"""
        self.status = ReviewStatus.REJECTED
        self.updated_at = datetime.now()
    
    def is_approved(self) -> bool:
        """Check if review is approved"""
        return self.status == ReviewStatus.APPROVED
    
    def is_pending(self) -> bool:
        """Check if review is pending"""
        return self.status == ReviewStatus.PENDING
    
    def is_rejected(self) -> bool:
        """Check if review is rejected"""
        return self.status == ReviewStatus.REJECTED
    
    def add_image(self, image_url: str):
        """Add an image to the review"""
        if image_url not in self.images:
            self.images.append(image_url)
            self.updated_at = datetime.now()
    
    def remove_image(self, image_url: str):
        """Remove an image from the review"""
        if image_url in self.images:
            self.images.remove(image_url)
            self.updated_at = datetime.now()
    
    def has_images(self) -> bool:
        """Check if review has any images"""
        return len(self.images) > 0
    
    def get_image_count(self) -> int:
        """Get the number of images in the review"""
        return len(self.images)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert review to dictionary"""
        return {
            'id': self.id,
            'reviewer_telegram_id': self.reviewer_telegram_id,
            'full_name': self.full_name,
            'exact_information': self.exact_information,
            'review_content': self.review_content,
            'images': self.images,
            'status': self.status.value,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Review':
        """Create Review from dictionary"""
        return cls(
            id=data.get('id'),
            reviewer_telegram_id=data['reviewer_telegram_id'],
            full_name=data['full_name'],
            exact_information=data.get('exact_information'),
            review_content=data['review_content'],
            images=data.get('images', []),
            status=ReviewStatus(data['status']) if data.get('status') else ReviewStatus.PENDING,
            created_at=datetime.fromisoformat(data['created_at']) if data.get('created_at') else None,
            updated_at=datetime.fromisoformat(data['updated_at']) if data.get('updated_at') else None
        )

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
