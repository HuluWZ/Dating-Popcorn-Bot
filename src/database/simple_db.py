"""
Simplified database operations for Dating Popcorn Bot
No FastAPI - just direct database operations for Telegram bot
"""

import asyncio
import logging
from typing import Optional, List, Tuple, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, text
from sqlalchemy.orm import joinedload
from geoalchemy2.functions import ST_Distance, ST_GeomFromText, ST_DWithin
import math
from datetime import datetime
from fastapi import HTTPException

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
            # Validate coordinates
            if not (-90 <= latitude <= 90):
                raise HTTPException(status_code=400, detail="Latitude must be between -90 and 90 degrees")
            if not (-180 <= longitude <= 180):
                raise HTTPException(status_code=400, detail="Longitude must be between -180 and 180 degrees")
            
            session_factory = get_session_factory()
            async with session_factory() as session:
                result = await session.execute(
                    select(User).where(User.id == telegram_id)
                )
                user = result.scalar_one_or_none()
                
                if not user:
                    raise HTTPException(status_code=404, detail=f"User with ID {telegram_id} not found")
                
                # Check if location is already set
                if user.location is not None:
                    logger.warning(f"User {telegram_id} already has location set")
                    raise HTTPException(status_code=400, detail=f"User {telegram_id} already has location set")
                
                user.set_location(latitude, longitude)
                await session.commit()
                logger.info(f"Set location for user {telegram_id}")
                return True
        except HTTPException:
            # Re-raise HTTPException as it contains our custom error message
            raise
        except ValueError as e:
            logger.warning(f"Location already set for user {telegram_id}: {e}")
            raise HTTPException(status_code=400, detail=f"Location already set for user {telegram_id}")
        except Exception as e:
            logger.error(f"Error setting location: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to set location for user {telegram_id}: {str(e)}")
    
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
        exact_address: Optional[str] = None,
        image_url: Optional[str] = None
    ) -> Review:
        """Create a new review"""
        try:
            logger.info(f"🗄️ Database: Creating review with parameters:")
            logger.info(f"   - reviewer_id: '{reviewer_id}' (type: {type(reviewer_id).__name__})")
            logger.info(f"   - full_name: '{full_name}' (type: {type(full_name).__name__}, length: {len(full_name)})")
            logger.info(f"   - content: '{content[:50]}{'...' if len(content) > 50 else ''}' (type: {type(content).__name__}, length: {len(content)})")
            logger.info(f"   - exact_address: '{exact_address}' (type: {type(exact_address).__name__})")
            logger.info(f"   - image_url: '{image_url}' (type: {type(image_url).__name__})")
            
            # Validate required fields
            if not reviewer_id or not reviewer_id.strip():
                raise HTTPException(status_code=400, detail="Reviewer ID is required")
            if not full_name or not full_name.strip():
                raise HTTPException(status_code=400, detail="Full name is required")
            if not content or not content.strip():
                raise HTTPException(status_code=400, detail="Content is required")
            
            session_factory = get_session_factory()
            async with session_factory() as session:
                # Check if reviewer exists
                reviewer_result = await session.execute(
                    select(User).where(User.id == reviewer_id)
                )
                reviewer = reviewer_result.scalar_one_or_none()
                if not reviewer:
                    raise HTTPException(status_code=404, detail=f"Reviewer with ID {reviewer_id} not found")
                
                review = Review(
                    reviewer_id=reviewer_id,
                    full_name=full_name,
                    content=content,
                    exact_address=exact_address,
                    image_url=image_url
                )
                logger.info(f"🗄️ Database: Review object created, adding to session...")
                session.add(review)
                logger.info(f"🗄️ Database: Committing transaction...")
                await session.commit()
                logger.info(f"🗄️ Database: Refreshing review object...")
                await session.refresh(review)
                
                logger.info(f"✅ Database: Review created successfully!")
                logger.info(f"   - Database ID: {review.id}")
                logger.info(f"   - Reviewer ID: {review.reviewer_id}")
                logger.info(f"   - Full Name: {review.full_name}")
                logger.info(f"   - Content Length: {len(review.content)}")
                logger.info(f"   - Exact Address: {review.exact_address}")
                logger.info(f"   - Image URL: {review.image_url}")
                logger.info(f"   - Status: {review.status.value}")
                logger.info(f"   - Created At: {review.created_at}")
                
                return review
        except HTTPException:
            # Re-raise HTTPException as it contains our custom error message
            raise
        except Exception as e:
            logger.error(f"❌ Database: Error creating review: {e}")
            logger.error(f"   - reviewer_id: '{reviewer_id}'")
            logger.error(f"   - full_name: '{full_name}'")
            logger.error(f"   - content_length: {len(content) if content else 0}")
            logger.error(f"   - exact_address: '{exact_address}'")
            logger.error(f"   - image_url: '{image_url}'")
            raise HTTPException(status_code=500, detail=f"Failed to create review: {str(e)}")
    
    @staticmethod
    async def search_reviews_by_name(name: str) -> List[Review]:
        """Search reviews by name"""
        try:
            session_factory = get_session_factory()
            async with session_factory() as session:
                result = await session.execute(
                    select(Review).options(joinedload(Review.reviewer)).where(
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
                    .options(joinedload(Review.reviewer))
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
    async def get_all_users(limit: int = 100, offset: int = 0) -> List[User]:
        """Get all users with location data"""
        try:
            session_factory = get_session_factory()
            async with session_factory() as session:
                query = select(User).where(User.location.isnot(None)).offset(offset).limit(limit)
                
                result = await session.execute(query)
                users = result.scalars().all()
                
                logger.info(f"Retrieved {len(users)} users with location (limit={limit}, offset={offset})")
                return users
                
        except Exception as e:
            logger.error(f"Error getting all users: {e}")
            return []

    @staticmethod
    async def get_user_stats() -> Dict[str, int]:
        """Get user statistics"""
        try:
            session_factory = get_session_factory()
            async with session_factory() as session:
                # Total users
                total_users_result = await session.execute(select(func.count(User.id)))
                total_users = total_users_result.scalar()
                
                # Users with location
                users_with_location_result = await session.execute(
                    select(func.count(User.id)).where(User.location.isnot(None))
                )
                users_with_location = users_with_location_result.scalar()
                
                # Banned users
                banned_users_result = await session.execute(
                    select(func.count(User.id)).where(User.is_banned == True)
                )
                banned_users = banned_users_result.scalar()
                
                stats = {
                    'total_users': total_users,
                    'users_with_location': users_with_location,
                    'banned_users': banned_users,
                    'active_users': total_users - banned_users
                }
                
                logger.info(f"User stats: {stats}")
                return stats
                
        except Exception as e:
            logger.error(f"Error getting user stats: {e}")
            return {
                'total_users': 0,
                'users_with_location': 0,
                'banned_users': 0,
                'active_users': 0
            }

    @staticmethod
    async def approve_review(review_id: str) -> bool:
        """Approve a review by ID"""
        try:
            session_factory = get_session_factory()
            async with session_factory() as session:
                # Get the review
                result = await session.execute(
                    select(Review).where(Review.id == review_id)
                )
                review = result.scalar_one_or_none()
                
                if not review:
                    logger.warning(f"Review {review_id} not found for approval")
                    raise HTTPException(status_code=404, detail=f"Review with ID {review_id} not found")
                
                # Check if already approved
                if review.status == ReviewStatusEnum.APPROVED:
                    logger.warning(f"Review {review_id} is already approved")
                    raise HTTPException(status_code=400, detail=f"Review {review_id} is already approved")
                
                # Check if already rejected
                if review.status == ReviewStatusEnum.REJECTED:
                    logger.warning(f"Review {review_id} is already rejected and cannot be approved")
                    raise HTTPException(status_code=400, detail=f"Review {review_id} is already rejected and cannot be approved")
                
                # Update status to approved
                review.status = ReviewStatusEnum.APPROVED
                review.updated_at = datetime.now()
                
                await session.commit()
                logger.info(f"Review {review_id} approved successfully")
                return True
                
        except HTTPException:
            # Re-raise HTTPException as it contains our custom error message
            raise
        except Exception as e:
            logger.error(f"Error approving review {review_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to approve review {review_id}: {str(e)}")

    @staticmethod
    async def reject_review(review_id: str) -> bool:
        """Reject a review by ID"""
        try:
            session_factory = get_session_factory()
            async with session_factory() as session:
                # Get the review
                result = await session.execute(
                    select(Review).where(Review.id == review_id)
                )
                review = result.scalar_one_or_none()
                
                if not review:
                    logger.warning(f"Review {review_id} not found for rejection")
                    raise HTTPException(status_code=404, detail=f"Review with ID {review_id} not found")
                
                # Check if already rejected
                if review.status == ReviewStatusEnum.REJECTED:
                    logger.warning(f"Review {review_id} is already rejected")
                    raise HTTPException(status_code=400, detail=f"Review {review_id} is already rejected")
                
                # Check if already approved
                if review.status == ReviewStatusEnum.APPROVED:
                    logger.warning(f"Review {review_id} is already approved and cannot be rejected")
                    raise HTTPException(status_code=400, detail=f"Review {review_id} is already approved and cannot be rejected")
                
                # Update status to rejected
                review.status = ReviewStatusEnum.REJECTED
                review.updated_at = datetime.now()
                
                await session.commit()
                logger.info(f"Review {review_id} rejected successfully")
                return True
                
        except HTTPException:
            # Re-raise HTTPException as it contains our custom error message
            raise
        except Exception as e:
            logger.error(f"Error rejecting review {review_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to reject review {review_id}: {str(e)}")

    @staticmethod
    async def get_user_reviews(reviewer_id: str) -> List[Review]:
        """Get all reviews by a specific user"""
        try:
            session_factory = get_session_factory()
            async with session_factory() as session:
                result = await session.execute(
                    select(Review)
                    .options(joinedload(Review.reviewer))
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
    async def get_all_reviews(limit: int = 100, offset: int = 0) -> List[Review]:
        """Get all reviews with pagination"""
        try:
            session_factory = get_session_factory()
            async with session_factory() as session:
                result = await session.execute(
                    select(Review)
                    .options(joinedload(Review.reviewer))
                    .order_by(Review.created_at.desc())
                    .offset(offset)
                    .limit(limit)
                )
                reviews = result.scalars().all()
                logger.info(f"Retrieved {len(reviews)} reviews (limit={limit}, offset={offset})")
                return list(reviews)
        except Exception as e:
            logger.error(f"Error getting all reviews: {e}")
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
    exact_address: Optional[str] = None,
    image_url: Optional[str] = None
) -> Optional[Review]:
    """Create a new review"""
    return await SimpleDatabase.create_review(reviewer_id, full_name, content, exact_address, image_url)

async def search_reviews_by_name(name: str) -> List[Review]:
    """Search reviews by name"""
    return await SimpleDatabase.search_reviews_by_name(name)

async def find_nearby_reviews(latitude: float, longitude: float, radius_km: float = 10.0) -> List[Review]:
    """Find reviews within radius of given location"""
    return await SimpleDatabase.find_nearby_reviews(latitude, longitude, radius_km)

async def get_user_reviews(reviewer_id: str) -> List[Review]:
    """Get all reviews by a specific user"""
    return await SimpleDatabase.get_user_reviews(reviewer_id)

async def get_all_users(limit: int = 100, offset: int = 0) -> List[User]:
    """Get all users with location data"""
    return await SimpleDatabase.get_all_users(limit, offset)

async def get_user_stats() -> Dict[str, int]:
    """Get user statistics"""
    return await SimpleDatabase.get_user_stats()

async def get_all_reviews(limit: int = 100, offset: int = 0) -> List[Review]:
    """Get all reviews with pagination"""
    return await SimpleDatabase.get_all_reviews(limit, offset)

async def approve_review(review_id: str) -> bool:
    """Approve a review by ID"""
    return await SimpleDatabase.approve_review(review_id)

async def reject_review(review_id: str) -> bool:
    """Reject a review by ID"""
    return await SimpleDatabase.reject_review(review_id)

async def get_pending_reviews() -> List[Review]:
    """Get all pending reviews"""
    return await SimpleDatabase.get_pending_reviews()

async def get_review_stats() -> Dict[str, int]:
    """Get review statistics"""
    return await SimpleDatabase.get_review_stats()