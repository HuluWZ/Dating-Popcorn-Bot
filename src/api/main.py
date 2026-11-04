"""
FastAPI application for Dating Popcorn Bot API
Provides endpoints to access users and reviews data
"""

import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from src.api.routers import users, reviews, admin, admins
from config.settings import ADMIN_PANEL_URL, ENVIRONMENT

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Determine if docs should be enabled (only in development)
docs_enabled = ENVIRONMENT == "development"

@asynccontextmanager
async def lifespan(_: FastAPI):
    # Single-process deploy (FastAPI Cloud has no worker type): RUN_BOT=true polls Telegram in this process
    task = None
    if os.getenv("RUN_BOT", "").lower() == "true":
        from src.bot.bot import main as run_bot
        task = asyncio.create_task(run_bot(handle_signals=False))
    yield
    if task:
        task.cancel()


# Create FastAPI app
app = FastAPI(
    lifespan=lifespan,
    title="Dating Popcorn Bot API",
    description="API for accessing users and reviews data",
    version="1.0.0",
    docs_url="/docs" if docs_enabled else None,  # Disable docs in production
    redoc_url="/redoc" if docs_enabled else None,  # Disable redoc in production
    openapi_url="/openapi.json" if docs_enabled else None,  # Disable OpenAPI schema in production
)

# Configure CORS - restrict to admin panel URL only
allowed_origins = []
if ADMIN_PANEL_URL:
    # Allow the admin panel URL and its variants
    allowed_origins.append(ADMIN_PANEL_URL)
    # Also allow without trailing slash
    if ADMIN_PANEL_URL.endswith('/'):
        allowed_origins.append(ADMIN_PANEL_URL.rstrip('/'))
    else:
        allowed_origins.append(ADMIN_PANEL_URL + '/')
else:
    # If no admin panel URL is set, log warning and allow nothing
    logger.warning("ADMIN_PANEL_URL not configured - CORS will be very restrictive")
    # In production, don't allow any origins if not configured
    if ENVIRONMENT == "production":
        allowed_origins = []
    else:
        # In development, allow localhost
        allowed_origins = ["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:3000"]

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,  # Only allow admin panel domain
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],  # Restrict methods
    allow_headers=["Content-Type", "Authorization"],  # Restrict headers
)

# Include routers
app.include_router(users.router)
app.include_router(reviews.router)
app.include_router(admin.router)
app.include_router(admins.router)


@app.get("/")
async def root():
    """Root endpoint with minimal API information"""
    return {
        "message": "Dating Popcorn Bot API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "message": "API is running"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)