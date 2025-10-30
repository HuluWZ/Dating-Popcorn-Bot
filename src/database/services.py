"""
Database service layer for Dating Popcorn Bot
"""

import logging
import re
from typing import Optional, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, text, case
from sqlalchemy.orm import selectinload
from geoalchemy2.functions import ST_Distance, ST_GeomFromText, ST_DWithin, ST_X, ST_Y, ST_MakePoint
from geoalchemy2.shape import from_shape
from shapely.geometry import Point
from geoalchemy2.types import Geography

from .models import User, Review, ReviewStatusEnum, GeographicQueries
from .connection import get_session, get_session_factory

# Configure logger
logger = logging.getLogger(__name__)

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
    async def advanced_search_by_name_and_location(
        searcher_telegram_id: str,
        query: str,
        radius_km: float = 50
    ) -> List[Tuple[Review, int, float]]:
        """
        Advanced search by name with word matching algorithm.
        Returns reviews with match counts and distances for ranking.
        
        Args:
            searcher_telegram_id: Telegram ID of the searcher
            query: Search query (name or handle)
            radius_km: Search radius in kilometers
            
        Returns:
            List of tuples (Review, match_count, distance_km) ordered by relevance
        """
        logger.info(f"🔍 Starting advanced search for user {searcher_telegram_id}")
        logger.info(f"   Query: '{query}'")
        logger.info(f"   Radius: {radius_km} km")
        
        session_factory = get_session_factory()
        async with session_factory() as session:
            try:
                # Get searcher's location from DB
                logger.debug(f"📍 Getting searcher location for user {searcher_telegram_id}")
                user_query = select(User).where(User.id == searcher_telegram_id)
                result = await session.execute(user_query)
                user = result.scalar_one_or_none()
                
                if not user:
                    logger.warning(f"❌ User {searcher_telegram_id} not found in database")
                    return []
                
                if not user.location:
                    logger.warning(f"❌ User {searcher_telegram_id} has no location set")
                    return []
                
                # Extract searcher lat/lon
                logger.debug(f"📍 Extracting coordinates for user {searcher_telegram_id}")
                lat_result = await session.execute(select(ST_Y(user.location)))
                lat = lat_result.scalar()
                lon_result = await session.execute(select(ST_X(user.location)))
                lon = lon_result.scalar()
                searcher_point = ST_MakePoint(lon, lat).cast(Geography)
                
                logger.info(f"📍 Searcher location: {lat:.6f}, {lon:.6f}")
                
                # Check if query is a phone number using regex or other (username/full_name vulnerbility)
                query_stripped = query.strip()
                # Phone number pattern: starts with + followed by digits
                phone_pattern = re.compile(r'^\+\d+')
                is_phone = bool(phone_pattern.match(query_stripped))
                
                logger.info(f"🔍 Search type: {'phone' if is_phone else 'username/name'}")
                
                if is_phone:
                    # For phone numbers, search only in exact_address
                    logger.debug("🔍 Building phone number search query")
                    search_condition = and_(
                        Review.exact_address.isnot(None),
                        Review.exact_address.ilike(f"%{query_stripped.lower()}%")
                    )
                    match_count = case(
                        (search_condition, 1),
                        else_=0
                    )
                else:
                    # For usernames or names, implement word-counting search
                    logger.debug("🔍 Building word-counting search query")
                    
                    # Split query into individual words
                    query_words = [word.strip().lower() for word in query_stripped.split() if word.strip()]
                    logger.debug(f"🔍 Query words: {query_words}")
                    
                    if not query_words:
                        logger.warning("❌ No valid words in search query")
                        return []
                    
                    # Build word matching conditions for full_name
                    name_word_conditions = []
                    for word in query_words:
                        name_word_conditions.append(Review.full_name.ilike(f"%{word}%"))
                    
                    # Build word matching conditions for exact_address
                    address_word_conditions = []
                    for word in query_words:
                        address_word_conditions.append(
                            and_(
                                Review.exact_address.isnot(None),
                                Review.exact_address.ilike(f"%{word}%")
                            )
                        )
                    
                    # Combined search condition - must match at least one word
                    search_condition = or_(
                        *name_word_conditions,
                        *address_word_conditions
                    )
                    
                    # Calculate word match count for full_name
                    name_word_count = 0
                    for i, word_condition in enumerate(name_word_conditions):
                        name_word_count += case((word_condition, 1), else_=0)
                    
                    # Calculate word match count for exact_address
                    address_word_count = 0
                    for i, word_condition in enumerate(address_word_conditions):
                        address_word_count += case((word_condition, 1), else_=0)
                    
                    # Total match count is the sum of word matches in both fields
                    match_count = name_word_count + address_word_count
                
                # Calculate distance in kilometers
                distance_km = (ST_Distance(User.location.cast(Geography), searcher_point) / 1000).label("distance_km")
                
                # Main search query
                logger.debug("🔍 Building main search query")
                search_query = (
                    select(Review, match_count.label("match_count"), distance_km)
                    .join(User, Review.reviewer_id == User.id)
                    .where(search_condition)
                    .filter(Review.status == ReviewStatusEnum.APPROVED)
                    .filter(ST_DWithin(User.location.cast(Geography), searcher_point, radius_km * 1000))  # Convert km to meters
                    .order_by(match_count.desc(), distance_km.asc(), Review.created_at.desc())
                    .limit(3)  # Limit to top 3 results
                )
                
                logger.info(f"🔍 Executing search query with radius {radius_km}km (limit: 3)")
                result = await session.execute(search_query)
                reviews_with_counts_distances = result.all()
                
                logger.info(f"✅ Search completed: Found {len(reviews_with_counts_distances)} results (max 3)")
                
                # Log detailed results
                for i, (review, match_count, distance) in enumerate(reviews_with_counts_distances, 1):
                    logger.info(f"   Result {i}: '{review.full_name}' (match_count: {match_count}, distance: {distance:.2f}km)")
                    if review.exact_address:
                        logger.debug(f"      Address: '{review.exact_address}'")
                
                return reviews_with_counts_distances
                
            except Exception as e:
                logger.error(f"❌ Error in advanced search for user {searcher_telegram_id}: {e}")
                logger.exception("Full traceback:")
                return []
    
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
