"""
Face search: embed the uploaded photo and find the nearest stored review photos (pgvector).
"""

import asyncio
import logging
from typing import List, Optional

from src.database.models import Review
from src.database.services import ReviewService
from src.utils.face_embedding import COSINE_MATCH_THRESHOLD, embed_face

logger = logging.getLogger(__name__)


class ImageComparisonResult:
    """A review whose photo matches the searched face"""

    def __init__(self, review: Review, similarity: float, distance_km: Optional[float] = None):
        self.review = review
        self.similarity = similarity  # cosine similarity as a 0-100 score
        self.distance_km = distance_km


async def search_by_image(
    uploaded_image_bytes: bytes,
    user_latitude: float,
    user_longitude: float,
    radius_km: float = 50,
) -> List[ImageComparisonResult]:
    """Top 3 reviews nearby whose photo matches the face. Raises FaceDetectionError if the photo has no usable face."""
    embedding = await asyncio.to_thread(embed_face, uploaded_image_bytes)
    rows = await ReviewService.find_similar_faces(
        embedding, user_latitude, user_longitude, radius_km, COSINE_MATCH_THRESHOLD
    )
    return [ImageComparisonResult(review, cosine * 100, km) for review, cosine, km in rows]
