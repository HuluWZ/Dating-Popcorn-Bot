"""
Database service layer for Dating Popcorn Bot
"""

import logging
import re
from typing import Optional, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, text, case, literal
from sqlalchemy.orm import selectinload
from geoalchemy2.functions import ST_Distance, ST_GeomFromText, ST_DWithin, ST_X, ST_Y, ST_MakePoint
from geoalchemy2.shape import from_shape
from shapely.geometry import Point
from geoalchemy2.types import Geography

from .models import User, Review, ReviewStatusEnum, GeographicQueries, Admin
from .connection import get_session, get_session_factory
from src.utils.social_utils import is_phone_like, normalize_phone_number, normalize_query

# Configure logger
logger = logging.getLogger(__name__)

# Minimum pg_trgm word_similarity for a query word to count as matching a name word
FUZZY_NAME_THRESHOLD = 0.5

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
                .options(selectinload(Review.reviewer))
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
    async def find_nearby_reviews_with_images(
        latitude: float, 
        longitude: float, 
        radius_km: float = 50
    ) -> List[Review]:
        """
        Find approved reviews with images from users within a specified radius.
        Used for face comparison image search.
        
        Args:
            latitude: Center latitude
            longitude: Center longitude
            radius_km: Search radius in kilometers (default: 50km)
            
        Returns:
            List of Review objects with image_url set
        """
        async with get_session() as session:
            center_point = ST_GeomFromText(f'POINT({longitude} {latitude})', 4326)
            
            result = await session.execute(
                select(Review)
                .options(selectinload(Review.reviewer))
                .join(User)
                .where(
                    and_(
                        User.location.isnot(None),
                        Review.status == ReviewStatusEnum.APPROVED,
                        Review.image_url.isnot(None),
                        Review.image_url != '',  # Ensure image_url is not empty
                        ST_DWithin(User.location, center_point, radius_km * 1000)
                    )
                )
                .order_by(ST_Distance(User.location, center_point))
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
                    .options(selectinload(Review.reviewer))
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
                
                # Normalize query and determine search mode (identifier vs name)
                query_stripped = query.strip()
                
                # Normalize the query using the same normalization used when writing reviews
                normalized_query = normalize_query(query_stripped)
                logger.debug(f"🔍 Normalized query: '{query_stripped}' -> '{normalized_query}'")
                
                # Check if it's a phone number (contains special chars + numbers)
                is_phone = is_phone_like(query_stripped)
                
                # Identifier search (phone or handle without spaces): exact match on exact_address (case-insensitive), '@' ignored
                # Ensure handles are searched with a leading '@' when user omits it
                if is_phone:
                    # For phone numbers, use the normalized query (last 8-9 digits)
                    handle_candidate = normalized_query
                else:
                    # For handles, ensure @ prefix
                    handle_candidate = normalized_query if normalized_query.startswith('@') else f"@{normalized_query}"
                
                looks_like_identifier = is_phone or ((' ' not in handle_candidate) and len(handle_candidate) > 0)
                
                logger.info(f"🔍 Search type: {'identifier' if looks_like_identifier else 'name'}")
                logger.debug(f"🔍 Is phone: {is_phone}, Handle candidate: '{handle_candidate}'")
                
                if looks_like_identifier:
                    if is_phone:
                        # Phone number search: normalize both query and stored exact_address
                        # Extract digits from stored exact_address, take last 8-9 digits
                        # Use PostgreSQL regexp_replace to remove non-digit characters
                        # Then take last 8-9 digits using substring
                        digits_only_func = func.regexp_replace(Review.exact_address, r'[^\d]', '', 'g')
                        # Get length of digits
                        digits_length = func.length(digits_only_func)
                        # If length <= 8, take all digits; if length > 8, take last 9
                        # For last 9 digits: substring from position (length - 8) for 9 characters
                        # Position calculation: to get last 9 digits, start at position (length - 8)
                        # e.g., if length=12, we want positions 4-12 (last 9), so start = 12-8 = 4
                        # For length=9: start = 9-8 = 1, takes all 9 digits
                        # For length=10: start = 10-8 = 2, takes last 9 digits (positions 2-10)
                        normalized_stored = case(
                            (digits_length <= 8, digits_only_func),
                            else_=func.substring(digits_only_func, digits_length - 8, 9)  # Take last 9 digits
                        )
                        
                        search_condition = and_(
                            Review.exact_address.isnot(None),
                            normalized_stored == handle_candidate
                        )
                        logger.debug(f"🔍 Building phone number search condition: normalized query '{handle_candidate}' matches normalized stored exact_address")
                    else:
                        # Handle/username search: case-insensitive equality on exact_address
                        search_condition = and_(
                            Review.exact_address.isnot(None),
                            func.lower(Review.exact_address) == func.lower(func.cast(handle_candidate, type(Review.exact_address.type)))
                        )
                        logger.debug(f"🔍 Building handle search condition: '{handle_candidate}'")
                    
                    match_count = case((search_condition, 1), else_=0)
                    name_similarity = literal(0)
                else:
                    # Name search: require at least two words; match on whole-word presence in full_name
                    logger.debug("🔍 Building name search condition with min 2-word requirement")
                    query_words = [w.strip().lower() for w in query_stripped.split() if w.strip()]
                    if len(query_words) < 2:
                        logger.warning("❌ Name search requires at least two words")
                        return []
                    
                    # Fuzzy match: every query word must be close to some word of full_name (pg_trgm)
                    # shortcut: no trigram index, fine while reviews are already narrowed by status/radius; add GIN gin_trgm_ops if slow
                    word_scores = [func.word_similarity(word, Review.full_name) for word in query_words]
                    search_condition = and_(*[score >= FUZZY_NAME_THRESHOLD for score in word_scores])
                    
                    # Match count equals number of query words (for ordering); similarity breaks ties below
                    match_count = case((search_condition, len(query_words)), else_=0)
                    name_similarity = sum(word_scores[1:], word_scores[0])
                
                # Calculate distance in kilometers
                distance_km = (ST_Distance(User.location.cast(Geography), searcher_point) / 1000).label("distance_km")
                
                # Main search query
                logger.debug("🔍 Building main search query")
                search_query = (
                    select(Review, match_count.label("match_count"), distance_km)
                    .join(User, Review.reviewer_id == User.id)
                    .options(selectinload(Review.reviewer))
                    .where(search_condition)
                    .filter(Review.status == ReviewStatusEnum.APPROVED)
                    .filter(ST_DWithin(User.location.cast(Geography), searcher_point, radius_km * 1000))  # Convert km to meters
                    .order_by(match_count.desc(), name_similarity.desc(), distance_km.asc(), Review.created_at.desc())
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


class AdminService:
    """Service for admin-related database operations"""
    
    @staticmethod
    async def create_admin(full_name: Optional[str], email: str, password: str) -> Admin:
        """Create a new admin"""
        session_factory = get_session_factory()
        async with session_factory() as session:
            admin = Admin(
                full_name=full_name,
                email=email
            )
            admin.set_password(password)
            
            session.add(admin)
            await session.commit()
            await session.refresh(admin)
            
            return admin
    
    @staticmethod
    async def get_all_admins() -> List[Admin]:
        """Get all admins"""
        session_factory = get_session_factory()
        async with session_factory() as session:
            result = await session.execute(select(Admin).order_by(Admin.created_at.desc()))
            return result.scalars().all()
    
    @staticmethod
    async def get_admin_by_id(admin_id: str) -> Optional[Admin]:
        """Get admin by ID"""
        session_factory = get_session_factory()
        async with session_factory() as session:
            result = await session.execute(
                select(Admin).where(Admin.id == admin_id)
            )
            return result.scalar_one_or_none()
    
    @staticmethod
    async def get_admin_by_email(email: str) -> Optional[Admin]:
        """Get admin by email"""
        session_factory = get_session_factory()
        async with session_factory() as session:
            result = await session.execute(
                select(Admin).where(Admin.email == email)
            )
            return result.scalar_one_or_none()
    
    @staticmethod
    async def delete_admin(admin_id: str) -> bool:
        """Delete admin by ID"""
        session_factory = get_session_factory()
        async with session_factory() as session:
            result = await session.execute(
                select(Admin).where(Admin.id == admin_id)
            )
            admin = result.scalar_one_or_none()
            
            if admin:
                await session.delete(admin)
                await session.commit()
                return True
            
            return False
    
    @staticmethod
    async def authenticate_admin(email: str, password: str) -> Optional[Admin]:
        """Authenticate admin with email and password"""
        session_factory = get_session_factory()
        async with session_factory() as session:
            result = await session.execute(
                select(Admin).where(Admin.email == email)
            )
            admin = result.scalar_one_or_none()
            
            if admin and admin.check_password(password):
                return admin
            
            return None
