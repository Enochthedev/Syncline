"""Main API router setup."""

from fastapi import APIRouter
from api.routes import health, stats, participants, threads, messages

# Create main API router
api_router = APIRouter(prefix="/api/v1")

# Include all route modules
api_router.include_router(health.router)
api_router.include_router(stats.router)
api_router.include_router(participants.router)
api_router.include_router(threads.router)
api_router.include_router(messages.router)

# Export for use in main application
__all__ = ["api_router"]
