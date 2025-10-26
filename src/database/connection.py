"""
Database connection and session management for Dating Popcorn Bot
"""

import os
import asyncio
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine as create_sync_engine
from config.settings import (
    DATABASE_URL, DATABASE_URL_ASYNC, 
    DATABASE_POOL_SIZE, DATABASE_MAX_OVERFLOW, 
    DATABASE_POOL_TIMEOUT, DATABASE_POOL_RECYCLE
)

# Global engine and session factory
_async_engine = None
_async_session_factory = None
_sync_engine = None

def get_database_url() -> str:
    """Get database URL from environment variables"""
    return DATABASE_URL

def get_async_database_url() -> str:
    """Get async database URL from environment variables"""
    return DATABASE_URL_ASYNC

def create_engine():
    """Create and configure database engines"""
    global _async_engine, _async_session_factory, _sync_engine
    
    if _async_engine is None:
        # Create async engine with proper pool settings
        _async_engine = create_async_engine(
            DATABASE_URL_ASYNC,
            echo=False,  # Set to True for SQL query logging
            pool_pre_ping=True,
            pool_size=DATABASE_POOL_SIZE,
            max_overflow=DATABASE_MAX_OVERFLOW,
            pool_timeout=DATABASE_POOL_TIMEOUT,
            pool_recycle=DATABASE_POOL_RECYCLE,
            future=True
        )
        
        # Create async session factory
        _async_session_factory = async_sessionmaker(
            _async_engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
    
    if _sync_engine is None:
        # Create sync engine for migrations
        _sync_engine = create_sync_engine(
            DATABASE_URL,
            echo=False,
            pool_pre_ping=True,
            pool_size=DATABASE_POOL_SIZE,
            max_overflow=DATABASE_MAX_OVERFLOW,
            pool_timeout=DATABASE_POOL_TIMEOUT,
            pool_recycle=DATABASE_POOL_RECYCLE
        )
    
    return _async_engine, _async_session_factory, _sync_engine

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Get async database session"""
    if _async_session_factory is None:
        create_engine()
    
    async with _async_session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

def get_session_factory():
    """Get session factory for direct use"""
    if _async_session_factory is None:
        create_engine()
    return _async_session_factory

async def init_database():
    """Initialize database tables"""
    from .models import Base
    
    if _async_engine is None:
        create_engine()
    
    async with _async_engine.begin() as conn:
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)

async def close_database():
    """Close database connections"""
    global _async_engine, _sync_engine
    
    if _async_engine:
        await _async_engine.dispose()
        _async_engine = None
    
    if _sync_engine:
        _sync_engine.dispose()
        _sync_engine = None

def get_sync_engine():
    """Get sync engine for migrations"""
    if _sync_engine is None:
        create_engine()
    return _sync_engine
