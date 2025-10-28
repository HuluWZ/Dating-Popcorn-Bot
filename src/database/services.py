"""
Database service layer for Dating Popcorn Bot
"""

from typing import Optional, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, text
from sqlalchemy.orm import selectinload
from geoalchemy2.functions import ST_Distance, ST_GeomFromText, ST_DWithin
from geoalchemy2.shape import from_shape
from shapely.geometry import Point

from .models import User, Review, ReviewStatusEnum, GeographicQueries
from .connection import get_session

class UserService:
    """Service for user-related database operations"""
    
    @staticmethod
    async def create_user(telegram_id: int, first_name: str, last_name: Optional[str] = None) -> User:
        """Create a new user"""
        async with get_session() as session:
            user = User(
                telegram_id=telegram_id,
                first_name=first_name,
                last_name=last_name
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            return user
    
    @staticmethod
    async def get_user_by_telegram_id(telegram_id: int) -> Optional[User]:
        """Get user by Telegram ID"""
        async with get_session() as session:
            result = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            return result.scalar_one_or_none()
    
    @staticmethod
    async def update_user_location(telegram_id: int, latitude: float, longitude: float) -> Optional[User]:
        """Update user location"""
        async with get_session() as session:
            result = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            user = result.scalar_one_or_none()
            
            if user:
                user.set_location(latitude, longitude)
                await session.commit()
                await session.refresh(user)
            
            return user
    
    @staticmethod
    async def find_users_within_radius(latitude: float, longitude: float, radius_km: float) -> List[User]:
        """Find users within a specified radius"""
        async with get_session() as session:
            center_point = ST_GeomFromText(f'POINT({longitude} {latitude})', 4326)
            
            result = await session.execute(
                select(User).where(
                    and_(
                        User.location.isnot(None),
                        ST_DWithin(User.location, center_point, radius_km * 1000)
                    )
                )
            )
            return result.scalars().all()
    
    @staticmethod
    async def get_user_location(telegram_id: int) -> Optional[Tuple[float, float]]:
        """Get user location as (latitude, longitude)"""
        user = await UserService.get_user_by_telegram_id(telegram_id)
        return user.get_location() if user else None

class ReviewService:
    """Service for review-related database operations"""
    
    @staticmethod
    async def create_review(
        reviewer_telegram_id: int,
        full_name: str,
        review_content: str,
        exact_information: Optional[str] = None,
        images: Optional[List[str]] = None
    ) -> Review:
        """Create a new review"""
        async with get_session() as session:
            review = Review(
                reviewer_telegram_id=reviewer_telegram_id,
                full_name=full_name,
                review_content=review_content,
                exact_information=exact_information,
                images=images or []
            )
            session.add(review)
            await session.commit()
            await session.refresh(review)
            return review
    
    @staticmethod
    async def get_review_by_id(review_id: int) -> Optional[Review]:
        """Get review by ID"""
        async with get_session() as session:
            result = await session.execute(
                select(Review).where(Review.id == review_id)
            )
            return result.scalar_one_or_none()
    
    @staticmethod
    async def get_user_reviews(telegram_id: int) -> List[Review]:
        """Get all reviews by a user"""
        async with get_session() as session:
            result = await session.execute(
                select(Review).where(Review.reviewer_telegram_id == telegram_id)
            )
            return result.scalars().all()
    
    @staticmethod
    async def get_pending_reviews() -> List[Review]:
        """Get all pending reviews"""
        async with get_session() as session:
            result = await session.execute(
                select(Review).where(Review.status == ReviewStatusEnum.PENDING)
            )
            return result.scalars().all()
    
    @staticmethod
    async def approve_review(review_id: int) -> Optional[Review]:
        """Approve a review"""
        async with get_session() as session:
            result = await session.execute(
                select(Review).where(Review.id == review_id)
            )
            review = result.scalar_one_or_none()
            
            if review:
                review.approve()
                await session.commit()
                await session.refresh(review)
            
            return review
    
    @staticmethod
    async def reject_review(review_id: int) -> Optional[Review]:
        """Reject a review"""
        async with get_session() as session:
            result = await session.execute(
                select(Review).where(Review.id == review_id)
            )
            review = result.scalar_one_or_none()
            
            if review:
                review.reject()
                await session.commit()
                await session.refresh(review)
            
            return review
    
    @staticmethod
    async def search_reviews_by_name(name: str) -> List[Review]:
        """Search reviews by name"""
        async with get_session() as session:
            result = await session.execute(
                select(Review).where(
                    and_(
                        Review.status == ReviewStatusEnum.APPROVED,
                        Review.full_name.ilike(f"%{name}%")
                    )
                )
            )
            return result.scalars().all()
    
    @staticmethod
    async def find_nearby_reviews(
        latitude: float, 
        longitude: float, 
        radius_km: float, 
        limit: int = 10
    ) -> List[Review]:
        """Find approved reviews from users within a specified radius"""
        async with get_session() as session:
            center_point = ST_GeomFromText(f'POINT({longitude} {latitude})', 4326)
            
            result = await session.execute(
                select(Review)
                .join(User)
                .where(
                    and_(
                        User.location.isnot(None),
                        Review.status == ReviewStatusEnum.APPROVED,
                        ST_DWithin(User.location, center_point, radius_km * 1000)
                    )
                )
                .order_by(ST_Distance(User.location, center_point))
                .limit(limit)
            )
            return result.scalars().all()
    
    @staticmethod
    async def add_image_to_review(review_id: int, image_url: str) -> Optional[Review]:
        """Add an image to a review"""
        async with get_session() as session:
            result = await session.execute(
                select(Review).where(Review.id == review_id)
            )
            review = result.scalar_one_or_none()
            
            if review:
                review.add_image(image_url)
                await session.commit()
                await session.refresh(review)
            
            return review
    
    @staticmethod
    async def remove_image_from_review(review_id: int, image_url: str) -> Optional[Review]:
        """Remove an image from a review"""
        async with get_session() as session:
            result = await session.execute(
                select(Review).where(Review.id == review_id)
            )
            review = result.scalar_one_or_none()
            
            if review:
                review.remove_image(image_url)
                await session.commit()
                await session.refresh(review)
            
            return review

class SearchService:
    """Service for search-related database operations"""
    
    @staticmethod
    async def search_by_name_and_location(
        name: str, 
        latitude: float, 
        longitude: float, 
        radius_km: float = 50
    ) -> List[Review]:
        """Search for reviews by name within a radius"""
        async with get_session() as session:
            center_point = ST_GeomFromText(f'POINT({longitude} {latitude})', 4326)
            
            result = await session.execute(
                select(Review)
                .join(User)
                .where(
                    and_(
                        User.location.isnot(None),
                        Review.status == ReviewStatusEnum.APPROVED,
                        Review.full_name.ilike(f"%{name}%"),
                        ST_DWithin(User.location, center_point, radius_km * 1000)
                    )
                )
                .order_by(ST_Distance(User.location, center_point))
            )
            return result.scalars().all()
    
    @staticmethod
    async def get_review_statistics() -> dict:
        """Get review statistics"""
        async with get_session() as session:
            # Total reviews
            total_result = await session.execute(
                select(func.count(Review.id))
            )
            total_reviews = total_result.scalar()
            
            # Approved reviews
            approved_result = await session.execute(
                select(func.count(Review.id)).where(Review.status == ReviewStatusEnum.APPROVED)
            )
            approved_reviews = approved_result.scalar()
            
            # Pending reviews
            pending_result = await session.execute(
                select(func.count(Review.id)).where(Review.status == ReviewStatusEnum.PENDING)
            )
            pending_reviews = pending_result.scalar()
            
            # Rejected reviews
            rejected_result = await session.execute(
                select(func.count(Review.id)).where(Review.status == ReviewStatusEnum.REJECTED)
            )
            rejected_reviews = rejected_result.scalar()
            
            return {
                'total': total_reviews,
                'approved': approved_reviews,
                'pending': pending_reviews,
                'rejected': rejected_reviews
            }
