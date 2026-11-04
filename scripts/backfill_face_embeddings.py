"""One-off: compute face embeddings for existing reviews that have a photo. Run: python -m scripts.backfill_face_embeddings"""

import asyncio
import logging

import requests
from sqlalchemy import select

from src.database.connection import get_session
from src.database.init_db import initialize_database
from src.database.models import Review
from src.utils.face_embedding import FaceDetectionError, embed_face

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    await initialize_database()  # adds the column/extension if missing
    async with get_session() as session:
        reviews = (await session.execute(
            select(Review).where(Review.image_url.isnot(None), Review.face_embedding.is_(None))
        )).scalars().all()
        for review in reviews:
            try:
                image = requests.get(review.image_url, timeout=30)
                image.raise_for_status()
                review.face_embedding = embed_face(image.content)
                logger.info("Embedded review %s", review.id)
            except (FaceDetectionError, requests.RequestException) as exc:
                logger.warning("Skipped review %s: %s", review.id, exc)
        await session.commit()


if __name__ == "__main__":
    asyncio.run(main())
