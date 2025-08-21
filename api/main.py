"""Main API router setup."""

from fastapi import APIRouter
from api.routes import (
    health, stats, participants, threads, messages, search, contact_search,
    whatsapp, security, contact_dossiers, summaries, files, websocket, monitoring, tenants, batch_processing
)

# Create main API router
api_router = APIRouter(prefix="/api/v1")

# Include all route modules
api_router.include_router(health.router)
api_router.include_router(stats.router)
api_router.include_router(participants.router)
api_router.include_router(threads.router)
api_router.include_router(messages.router)
api_router.include_router(search.router)
api_router.include_router(contact_search.router)
api_router.include_router(whatsapp.router)
api_router.include_router(security.router)
api_router.include_router(contact_dossiers.router)
api_router.include_router(summaries.router)
api_router.include_router(files.router)
api_router.include_router(websocket.router)
api_router.include_router(monitoring.router)
api_router.include_router(tenants.router)
api_router.include_router(batch_processing.router)

# Export for use in main application
__all__ = ["api_router"]
