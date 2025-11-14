"""
Image comparison service for face recognition search
"""

import logging
import math
from typing import List, Dict, Optional, Tuple
from io import BytesIO

from src.utils.rekognition_utils import (
    detect_faces,
    compare_faces,
    download_image_from_url,
    FaceDetectionError,
    FaceComparisonError,
    DEFAULT_MATCH_THRESHOLD
)
from src.database.services import ReviewService
from src.database.models import Review

logger = logging.getLogger(__name__)


class ImageComparisonResult:
    """Result of image comparison for a single face"""
    
    def __init__(self, review: Review, similarity: float, distance_km: Optional[float] = None):
        self.review = review
        self.similarity = similarity
        self.distance_km = distance_km


class FaceMatchResult:
    """Result of face matching for a detected face"""
    
    def __init__(self, face_index: int, matches: List[ImageComparisonResult]):
        self.face_index = face_index
        self.matches = matches  # Sorted by similarity (highest first)


class ImageSearchResult:
    """Complete result of image search"""
    
    def __init__(self):
        self.face_results: List[FaceMatchResult] = []
        self.total_faces_detected = 0
        self.total_comparisons = 0
        self.errors: List[str] = []
    
    def add_face_result(self, face_result: FaceMatchResult):
        """Add result for a detected face"""
        self.face_results.append(face_result)
    
    def has_matches(self) -> bool:
        """Check if any matches were found"""
        return any(len(face_result.matches) > 0 for face_result in self.face_results)
    
    def get_all_matches(self) -> List[ImageComparisonResult]:
        """Get all matches across all faces, sorted by distance (closest first), then by similarity (highest first)"""
        all_matches = []
        for face_result in self.face_results:
            all_matches.extend(face_result.matches)
        
        # Sort by distance (closest first), then by similarity (highest first)
        all_matches.sort(
            key=lambda x: (x.distance_km or float('inf'), -x.similarity)
        )
        
        # Remove duplicates (same review) - keep highest similarity
        seen_reviews = {}
        unique_matches = []
        for match in all_matches:
            review_id = str(match.review.id)
            if review_id not in seen_reviews or seen_reviews[review_id].similarity < match.similarity:
                if review_id in seen_reviews:
                    unique_matches.remove(seen_reviews[review_id])
                seen_reviews[review_id] = match
                unique_matches.append(match)
        
        return unique_matches


async def search_by_image(
    uploaded_image_bytes: bytes,
    user_latitude: float,
    user_longitude: float,
    radius_km: float = 50,
    similarity_threshold: float = DEFAULT_MATCH_THRESHOLD
) -> List[ImageComparisonResult]:
    """
    Search for matching faces in reviews by comparing uploaded image
    
    Args:
        uploaded_image_bytes: Uploaded image data as bytes
        user_latitude: User's latitude for location filtering
        user_longitude: User's longitude for location filtering
        radius_km: Search radius in kilometers (default: 50km)
        similarity_threshold: Minimum similarity score (0-100, default: 90)
        
    Returns:
        List of ImageComparisonResult (max 3), sorted by similarity percentage (highest first)
        
    Raises:
        FaceDetectionError: If no faces detected or face quality issues
    """
    all_matches = []
    
    try:
        # Step 1: Detect faces in uploaded image
        logger.info("Step 1: Detecting faces in uploaded image")
        detection_result = detect_faces(uploaded_image_bytes)
        faces = detection_result['faces']
        total_faces_detected = len(faces)
        
        logger.info(f"Detected {total_faces_detected} face(s) in uploaded image")
        
        if total_faces_detected == 0:
            raise FaceDetectionError("NO_FACE", "No face detected in the image.")
        
        # Step 2: Get reviews with images within radius
        logger.info(f"Step 2: Fetching reviews with images within {radius_km}km radius")
        reviews_with_images = await ReviewService.find_nearby_reviews_with_images(
            latitude=user_latitude,
            longitude=user_longitude,
            radius_km=radius_km
        )
        
        logger.info(f"Found {len(reviews_with_images)} reviews with images in radius")
        
        if not reviews_with_images:
            logger.info("No reviews with images found in radius")
            return []
        
        # Step 3: Compare uploaded image with all review images
        total_comparisons = 0
        for review in reviews_with_images:
            try:
                # Download review image
                logger.debug(f"Downloading image for review {review.id}: {review.image_url}")
                try:
                    review_image_bytes = download_image_from_url(review.image_url)
                except Exception as e:
                    logger.warning(f"Failed to download image for review {review.id} ({review.image_url}): {e}")
                    continue
                
                # Compare faces
                try:
                    comparison_result = compare_faces(
                        source_image_bytes=uploaded_image_bytes,
                        target_image_bytes=review_image_bytes,
                        similarity_threshold=similarity_threshold
                    )
                except FaceComparisonError as e:
                    logger.warning(f"Face comparison error for review {review.id}: {e}")
                    continue
                
                total_comparisons += 1
                logger.info(f"Comparison result: {comparison_result['is_match']}  | {comparison_result['similarity']:.2f}%")
                
                # If match found, add to results
                is_match = comparison_result.get('is_match', False)
                logger.info(f"Checking is_match: {is_match} (type: {type(is_match)})")
                
                if is_match:
                    logger.info(f"✅ Match found for review {review.id} - processing match...")
                    similarity = comparison_result.get('similarity', 0.0)
                    logger.info(f"Similarity: {similarity}")
                    
                    # Calculate distance using Haversine formula
                    distance_km = None
                    try:
                        if review.reviewer and review.reviewer.location:
                            logger.info(f"Reviewer: {review.reviewer} with location: {review.reviewer.location}")
                            try:
                                reviewer_location = review.reviewer.get_location()
                                logger.info(f"Reviewer location: {reviewer_location}")
                                if reviewer_location:
                                    lat1, lon1 = user_latitude, user_longitude
                                    lat2, lon2 = reviewer_location
                                    
                                    # Haversine formula
                                    R = 6371  # Earth radius in km
                                    dlat = math.radians(lat2 - lat1)
                                    dlon = math.radians(lon2 - lon1)
                                    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
                                    c = 2 * math.asin(math.sqrt(a))
                                    distance_km = R * c
                            except Exception as e:
                                logger.debug(f"Could not calculate distance for review {review.id}: {e}")
                    except Exception as e:
                        logger.warning(f"Error accessing reviewer location for review {review.id}: {e}")
                    
                    logger.info(f"Distance: {distance_km}")
                    
                    # Create match object - this should never fail
                    try:
                        match = ImageComparisonResult(
                            review=review,
                            similarity=similarity,
                            distance_km=distance_km
                        )
                        logger.info(f"✅ Created match object for review {review.id}")
                        logger.info(f"Match: Review {review.id} ({review.full_name}) - {similarity:.2f}% similarity, {distance_km:.2f}km away" if distance_km else f"Match: Review {review.id} ({review.full_name}) - {similarity:.2f}% similarity")
                        
                        all_matches.append(match)
                        logger.info(f"✅ Added match to all_matches. Total matches so far: {len(all_matches)}")
                    except Exception as e:
                        logger.error(f"❌ CRITICAL: Error creating/adding match for review {review.id}: {e}")
                        logger.exception("Full traceback:")
                        # Even if there's an error, try to add a basic match
                        try:
                            basic_match = ImageComparisonResult(
                                review=review,
                                similarity=similarity,
                                distance_km=None
                            )
                            all_matches.append(basic_match)
                            logger.info(f"✅ Added basic match as fallback for review {review.id}")
                        except Exception as e2:
                            logger.error(f"❌ CRITICAL: Even fallback match creation failed: {e2}")
                else:
                    logger.debug(f"No match for review {review.id} (similarity: {comparison_result.get('similarity', 0):.2f}% < threshold: {similarity_threshold}%)")
            
            except Exception as e:
                logger.warning(f"Unexpected error comparing with review {review.id}: {e}")
                logger.exception("Full traceback:")
                # Continue with next review
                continue
        
        logger.info(f"Total matches collected: {len(all_matches)}")
        
        # Remove duplicates (same review) - keep highest similarity
        seen_reviews = {}
        unique_matches = []
        for match in all_matches:
            review_id = str(match.review.id)
            if review_id not in seen_reviews or seen_reviews[review_id].similarity < match.similarity:
                if review_id in seen_reviews:
                    unique_matches.remove(seen_reviews[review_id])
                seen_reviews[review_id] = match
                unique_matches.append(match)
        
        logger.info(f"Unique matches after deduplication: {len(unique_matches)}")
        
        # Sort by similarity percentage (highest first)
        unique_matches.sort(key=lambda x: x.similarity, reverse=True)
        
        # Limit to max 3 results
        result = unique_matches[:3]
        
        logger.info(
            f"Image search completed: {total_faces_detected} face(s), "
            f"{total_comparisons} comparison(s), "
            f"{len(all_matches)} total match(es) collected, "
            f"{len(unique_matches)} unique match(es), "
            f"{len(result)} match(es) returned (max 3)"
        )
        
        if len(result) == 0 and len(all_matches) > 0:
            logger.warning(f"⚠️ WARNING: {len(all_matches)} matches collected but 0 returned! This should not happen.")
        
        return result
    
    except FaceDetectionError:
        # Re-raise face detection errors (no face, low quality, etc.)
        raise
    
    except Exception as e:
        logger.error(f"Unexpected error in image search: {e}")
        return []

