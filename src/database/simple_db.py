"""
Simplified database operations for Dating Popcorn Bot
No FastAPI - just direct database operations for Telegram bot
"""

import asyncio
import logging
from typing import Optional, List, Tuple, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, text
from geoalchemy2.functions import ST_Distance, ST_GeomFromText, ST_DWithin
import math

from .models import User, Review, ReviewStatusEnum
from .connection import get_session_factory

logger = logging.getLogger(__name__)

class SimpleDatabase:
    """Simplified database operations for Telegram bot"""
    
    @staticmethod
    async def get_user(telegram_id: str) -> Optional[User]:
        """Get user by telegram_id"""
        session_factory = get_session_factory()
        async with session_factory() as session:
            result = await session.execute(
                select(User).where(User.id == telegram_id)
            )
            return result.scalar_one_or_none()
    
    @staticmethod
    async def create_or_get_user(telegram_id: str, username: Optional[str] = None) -> User:
        """Create user if not exists, or get existing user"""
        session_factory = get_session_factory()
        async with session_factory() as session:
            # Try to get existing user
            result = await session.execute(
                select(User).where(User.id == telegram_id)
            )
            user = result.scalar_one_or_none()
            
            if user:
                # Update username if changed
                if user.username != username:
                    user.username = username
                    await session.commit()
                return user
            
            # Create new user
            user = User(
                id=telegram_id,  # telegram_id as string
                username=username
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            logger.info(f"Created new user: {telegram_id}")
            return user
    
    @staticmethod
    async def set_user_location(telegram_id: str, latitude: float, longitude: float) -> bool:
        """Set user location (only once)"""
        try:
            session_factory = get_session_factory()
            async with session_factory() as session:
                result = await session.execute(
                    select(User).where(User.id == telegram_id)
                )
                user = result.scalar_one_or_none()
                
                if user:
                    # Check if location is already set
                    if user.location is not None:
                        logger.warning(f"User {telegram_id} already has location set")
                        return False
                    
                    user.set_location(latitude, longitude)
                    await session.commit()
                    logger.info(f"Set location for user {telegram_id}")
                    return True
                return False
        except ValueError as e:
            logger.warning(f"Location already set for user {telegram_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error setting location: {e}")
            return False
    
    @staticmethod
    async def get_user_location(telegram_id: str) -> Optional[Tuple[float, float]]:
        """Get user location"""
        session_factory = get_session_factory()
        async with session_factory() as session:
            result = await session.execute(
                select(User).where(User.id == telegram_id)
            )
            user = result.scalar_one_or_none()
            return user.get_location() if user else None
    
    @staticmethod
    async def has_user_location(telegram_id: str) -> bool:
        """Check if user has location set"""
        session_factory = get_session_factory()
        async with session_factory() as session:
            result = await session.execute(
                select(User).where(User.id == telegram_id)
            )
            user = result.scalar_one_or_none()
            return user.location is not None if user else False
    
    @staticmethod
    async def create_review(
        reviewer_id: str,
        full_name: str,
        content: str,
        social_handle: Optional[str] = None,
        images: Optional[List[str]] = None
    ) -> Optional[Review]:
        """Create a new review"""
        try:
            session_factory = get_session_factory()
            async with session_factory() as session:
                review = Review(
                    reviewer_id=reviewer_id,
                    full_name=full_name,
                    content=content,
                    social_handle=social_handle,
                    images=images
                )
                session.add(review)
                await session.commit()
                await session.refresh(review)
                logger.info(f"Created review for {full_name} by user {reviewer_id} with {len(images) if images else 0} images")
                return review
        except Exception as e:
            logger.error(f"Error creating review: {e}")
            return None
    
    @staticmethod
    async def search_reviews_by_name(name: str) -> List[Review]:
        """Search reviews by name"""
        try:
            session_factory = get_session_factory()
            async with session_factory() as session:
                result = await session.execute(
                    select(Review).where(
                        Review.full_name.ilike(f"%{name}%")
                    ).order_by(Review.created_at.desc())
                )
                reviews = result.scalars().all()
                logger.info(f"Found {len(reviews)} reviews for name '{name}'")
                return list(reviews)
        except Exception as e:
            logger.error(f"Error searching reviews by name: {e}")
            return []
    
    @staticmethod
    async def find_nearby_reviews(latitude: float, longitude: float, radius_km: float = 10.0) -> List[Review]:
        """Find reviews within radius of given location"""
        try:
            session_factory = get_session_factory()
            async with session_factory() as session:
                # Convert radius from km to meters
                radius_meters = radius_km * 1000
                
                # Create point from coordinates
                point_wkt = f"POINT({longitude} {latitude})"
                
                result = await session.execute(
                    select(Review)
                    .join(User, Review.reviewer_id == User.id)
                    .where(
                        User.location.isnot(None),
                        func.ST_DWithin(
                            User.location,
                            func.ST_GeomFromText(point_wkt, 4326),
                            radius_meters
                        )
                    )
                    .order_by(
                        func.ST_Distance(
                            User.location,
                            func.ST_GeomFromText(point_wkt, 4326)
                        )
                    )
                )
                reviews = result.scalars().all()
                logger.info(f"Found {len(reviews)} reviews within {radius_km}km of ({latitude}, {longitude})")
                return list(reviews)
        except Exception as e:
            logger.error(f"Error finding nearby reviews: {e}")
            return []
    
    @staticmethod
    async def get_user_reviews(reviewer_id: str) -> List[Review]:
        """Get all reviews by a specific user"""
        try:
            session_factory = get_session_factory()
            async with session_factory() as session:
                result = await session.execute(
                    select(Review)
                    .where(Review.reviewer_id == reviewer_id)
                    .order_by(Review.created_at.desc())
                )
                reviews = result.scalars().all()
                logger.info(f"Found {len(reviews)} reviews by user {reviewer_id}")
                return list(reviews)
        except Exception as e:
            logger.error(f"Error getting user reviews: {e}")
            return []
    
    @staticmethod
    async def get_pending_reviews() -> List[Review]:
        """Get all pending reviews"""
        try:
            session_factory = get_session_factory()
            async with session_factory() as session:
                result = await session.execute(
                    select(Review)
                    .where(Review.status == ReviewStatusEnum.PENDING)
                    .order_by(Review.created_at.desc())
                )
                reviews = result.scalars().all()
                logger.info(f"Found {len(reviews)} pending reviews")
                return list(reviews)
        except Exception as e:
            logger.error(f"Error getting pending reviews: {e}")
            return []
    
    @staticmethod
    async def get_review_stats() -> Dict[str, int]:
        """Get review statistics"""
        try:
            session_factory = get_session_factory()
            async with session_factory() as session:
                # Get total count
                total_result = await session.execute(select(func.count(Review.id)))
                total = total_result.scalar()
                
                # Get counts by status
                pending_result = await session.execute(
                    select(func.count(Review.id)).where(Review.status == ReviewStatusEnum.PENDING)
                )
                pending = pending_result.scalar()
                
                approved_result = await session.execute(
                    select(func.count(Review.id)).where(Review.status == ReviewStatusEnum.APPROVED)
                )
                approved = approved_result.scalar()
                
                rejected_result = await session.execute(
                    select(func.count(Review.id)).where(Review.status == ReviewStatusEnum.REJECTED)
                )
                rejected = rejected_result.scalar()
                
                stats = {
                    'total': total,
                    'pending': pending,
                    'approved': approved,
                    'rejected': rejected
                }
                
                logger.info(f"Review stats: {stats}")
                return stats
        except Exception as e:
            logger.error(f"Error getting review stats: {e}")
            return {'total': 0, 'pending': 0, 'approved': 0, 'rejected': 0}
    
    @staticmethod
    async def search_reviews_by_name(name: str) -> List[Review]:
        """Search approved reviews by name"""
        session_factory = get_session_factory()
        async with session_factory() as session:
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
        radius_km: float = 50,
        limit: int = 10
    ) -> List[Review]:
        """Find approved reviews from users within radius using PostGIS"""
        try:
            session_factory = get_session_factory()
            async with session_factory() as session:
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
                    
        except Exception as e:
            logger.error(f"Error finding nearby reviews: {e}")
            return []
    
    @staticmethod
    def _calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points in kilometers using Haversine formula"""
        R = 6371  # Earth's radius in kilometers
        
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        
        a = (math.sin(dlat/2) * math.sin(dlat/2) + 
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * 
             math.sin(dlon/2) * math.sin(dlon/2))
        
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        distance = R * c
        
        return distance
    
    @staticmethod
    async def get_user_reviews(telegram_id: str) -> List[Review]:
        """Get all reviews by a user"""
        session_factory = get_session_factory()
        async with session_factory() as session:
            result = await session.execute(
                select(Review).where(Review.reviewer_id == telegram_id)
            )
            return result.scalars().all()
    
    @staticmethod
    async def get_pending_reviews() -> List[Review]:
        """Get all pending reviews for admin approval"""
        session_factory = get_session_factory()
        async with session_factory() as session:
            result = await session.execute(
                select(Review).where(Review.status == ReviewStatusEnum.PENDING)
            )
            return result.scalars().all()
    
    @staticmethod
    async def approve_review(review_id: str) -> bool:
        """Approve a review"""
        try:
            session_factory = get_session_factory()
            async with session_factory() as session:
                result = await session.execute(
                    select(Review).where(Review.id == review_id)
                )
                review = result.scalar_one_or_none()
                
                if review:
                    review.approve()
                    await session.commit()
                    logger.info(f"Approved review {review_id}")
                    return True
                return False
        except Exception as e:
            logger.error(f"Error approving review: {e}")
            return False
    
    @staticmethod
    async def reject_review(review_id: str) -> bool:
        """Reject a review"""
        try:
            session_factory = get_session_factory()
            async with session_factory() as session:
                result = await session.execute(
                    select(Review).where(Review.id == review_id)
                )
                review = result.scalar_one_or_none()
                
                if review:
                    review.reject()
                    await session.commit()
                    logger.info(f"Rejected review {review_id}")
                    return True
                return False
        except Exception as e:
            logger.error(f"Error rejecting review: {e}")
            return False
    
    @staticmethod
    async def ban_user(telegram_id: str) -> bool:
        """Ban a user"""
        try:
            session_factory = get_session_factory()
            async with session_factory() as session:
                result = await session.execute(
                    select(User).where(User.id == telegram_id)
                )
                user = result.scalar_one_or_none()
                
                if user:
                    user.ban()
                    await session.commit()
                    logger.info(f"Banned user {telegram_id}")
                    return True
                return False
        except Exception as e:
            logger.error(f"Error banning user: {e}")
            return False
    
    @staticmethod
    async def unban_user(telegram_id: str) -> bool:
        """Unban a user"""
        try:
            session_factory = get_session_factory()
            async with session_factory() as session:
                result = await session.execute(
                    select(User).where(User.id == telegram_id)
                )
                user = result.scalar_one_or_none()
                
                if user:
                    user.unban()
                    await session.commit()
                    logger.info(f"Unbanned user {telegram_id}")
                    return True
                return False
        except Exception as e:
            logger.error(f"Error unbanning user: {e}")
            return False
    
    @staticmethod
    async def is_user_banned(telegram_id: str) -> bool:
        """Check if user is banned"""
        session_factory = get_session_factory()
        async with session_factory() as session:
            result = await session.execute(
                select(User).where(User.id == telegram_id)
            )
            user = result.scalar_one_or_none()
            return user.is_banned_user() if user else False
    
    @staticmethod
    async def get_review_stats() -> dict:
        """Get review statistics"""
        session_factory = get_session_factory()
        async with session_factory() as session:
            total_result = await session.execute(select(func.count(Review.id)))
            total = total_result.scalar()
            
            approved_result = await session.execute(
                select(func.count(Review.id)).where(Review.status == ReviewStatusEnum.APPROVED)
            )
            approved = approved_result.scalar()
            
            pending_result = await session.execute(
                select(func.count(Review.id)).where(Review.status == ReviewStatusEnum.PENDING)
            )
            pending = pending_result.scalar()
            
            return {
                'total': total,
                'approved': approved,
                'pending': pending,
                'rejected': total - approved - pending
            }

# Convenience functions for easier importing
async def get_user(telegram_id: str) -> Optional[User]:
    """Get user by telegram_id"""
    return await SimpleDatabase.get_user(telegram_id)

async def create_or_get_user(telegram_id: str, username: Optional[str] = None) -> User:
    """Create user if not exists, or get existing user"""
    return await SimpleDatabase.create_or_get_user(telegram_id, username)

async def set_user_location(telegram_id: str, latitude: float, longitude: float) -> bool:
    """Set user location (only once)"""
    return await SimpleDatabase.set_user_location(telegram_id, latitude, longitude)

async def get_user_location(telegram_id: str) -> Optional[Tuple[float, float]]:
    """Get user location"""
    return await SimpleDatabase.get_user_location(telegram_id)

async def has_user_location(telegram_id: str) -> bool:
    """Check if user has location set"""
    return await SimpleDatabase.has_user_location(telegram_id)

async def create_review(
    reviewer_id: str,
    full_name: str,
    content: str,
    social_handle: Optional[str] = None,
    images: Optional[List[str]] = None
) -> Optional[Review]:
    """Create a new review"""
    return await SimpleDatabase.create_review(reviewer_id, full_name, content, social_handle, images)

async def search_reviews_by_name(name: str) -> List[Review]:
    """Search reviews by name"""
    return await SimpleDatabase.search_reviews_by_name(name)

async def find_nearby_reviews(latitude: float, longitude: float, radius_km: float = 10.0) -> List[Review]:
    """Find reviews within radius of given location"""
    return await SimpleDatabase.find_nearby_reviews(latitude, longitude, radius_km)

async def get_user_reviews(reviewer_id: str) -> List[Review]:
    """Get all reviews by a specific user"""
    return await SimpleDatabase.get_user_reviews(reviewer_id)

async def get_pending_reviews() -> List[Review]:
    """Get all pending reviews"""
    return await SimpleDatabase.get_pending_reviews()

async def get_review_stats() -> Dict[str, int]:
    """Get review statistics"""
    return await SimpleDatabase.get_review_stats()