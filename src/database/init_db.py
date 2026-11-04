"""
Database initialization script for Dating Popcorn Bot
"""

import asyncio
import logging
from sqlalchemy import text
from .connection import create_engine, init_database, close_database
from .models import Base

logger = logging.getLogger(__name__)

async def create_postgis_extensions():
    """Create PostGIS extensions if they don't exist"""
    _, _, sync_engine = create_engine()
    
    with sync_engine.connect() as conn:
        # Create PostGIS extensions
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis_topology;"))
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";"))
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))  # pgvector, face search
        # create_all does not alter existing tables
        conn.execute(text("ALTER TABLE IF EXISTS reviews ADD COLUMN IF NOT EXISTS face_embedding vector(128);"))
        conn.commit()
        logger.info("PostGIS extensions created successfully")

async def initialize_database():
    """Initialize the database with tables and extensions"""
    try:
        logger.info("Initializing database...")
        
        # Create PostGIS extensions
        await create_postgis_extensions()
        
        # Create all tables
        await init_database()
        
        logger.info("Database initialized successfully")
        
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise
    finally:
        await close_database()

async def main():
    """Main function to initialize database"""
    await initialize_database()

if __name__ == "__main__":
    asyncio.run(main())
