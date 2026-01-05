"""
R.E.M.I Backend - Main Application Entry Point

FastAPI application with:
- Lifespan management for startup/shutdown
- CORS middleware
- API routing
- OpenAPI documentation
- Health monitoring
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.routes import health, connections, collection, messages, contacts, threads, auth, whatsapp, chats, ai
from config.config import settings
from db.session import get_engine, init_db


# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager.
    
    Handles startup and shutdown events:
    - Startup: Initialize database, Redis, and other services
    - Shutdown: Clean up connections and resources
    """
    # Startup
    logger.info("Starting R.E.M.I Backend...")
    logger.info(f"Environment: {settings.ENV}")
    logger.info(f"Debug mode: {settings.DEBUG}")
    
    try:
        # Initialize database
        logger.info("Initializing database...")
        await init_db()
        logger.info("Database initialized successfully")

        # Initialize connector cache
        logger.info("Starting connector cache...")
        from services.connector_cache import get_connector_cache
        cache = get_connector_cache()
        await cache.start()
        logger.info("Connector cache started")

        # TODO: Initialize Redis connection
        # TODO: Initialize event bus
        # Start background workers
        from services.tasks.message_collection import start_collection_worker
        start_collection_worker(interval_seconds=30)
        logger.info("Background tasks started")
        
        logger.info("R.E.M.I Backend started successfully")
        
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down R.E.M.I Backend...")
    
    try:
        # Stop background workers
        from services.tasks.message_collection import stop_collection_worker
        stop_collection_worker()

        # Stop connector cache
        logger.info("Stopping connector cache...")
        from services.connector_cache import get_connector_cache
        cache = get_connector_cache()
        await cache.stop()
        logger.info("Connector cache stopped")

        # Close database connections
        logger.info("Closing database connections...")
        engine = get_engine()
        await engine.dispose()
        logger.info("Database connections closed")
        
        logger.info("R.E.M.I Backend shut down successfully")
        
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


# Create FastAPI application
app = FastAPI(
    title="R.E.M.I Backend API",
    description="""
    Real-time External Memory Interface (R.E.M.I) Backend API
    
    A comprehensive mesh ingestion system that unifies messages from multiple 
    communication platforms into a single, searchable, and AI-enhanced interface.
    
    ## Features
    
    - **Multi-Platform Integration**: Connect Gmail, Slack, Discord, WhatsApp, Twitter/X
    - **Real-time Processing**: Event-driven architecture with minimal latency
    - **Unified Data Model**: Normalize messages from different platforms
    - **AI Enhancement**: Local-first AI processing with entity extraction and summarization
    - **Enterprise Ready**: OAuth 2.0, encryption, and scalable architecture
    
    ## Stages
    
    1. **Connection**: OAuth flows and credential management
    2. **Collection**: Historical and real-time message fetching
    3. **Cleaning**: Message normalization and standardization
    4. **Matching**: Contact identification and thread grouping
    5. **AI**: Embeddings, entity extraction, and summarization
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/api/v1", tags=["Health"])
app.include_router(connections.router, prefix="/api/v1/connections", tags=["Connections"])
app.include_router(collection.router, prefix="/api/v1/collection", tags=["Collection"])
app.include_router(messages.router, prefix="/api/v1/messages", tags=["Messages"])
app.include_router(chats.router, prefix="/api/v1/chats", tags=["Chats"])
app.include_router(contacts.router, prefix="/api/v1/contacts", tags=["Contacts"])
app.include_router(threads.router, prefix="/api/v1/threads", tags=["Threads"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(whatsapp.router, prefix="/api/v1/whatsapp", tags=["WhatsApp"])
app.include_router(ai.router, prefix="/api/v1/ai", tags=["AI"])

# Root endpoint
@app.get("/", tags=["Root"])
async def root() -> JSONResponse:
    """
    Root endpoint providing API information.
    
    Returns:
        JSONResponse: API metadata and links
    """
    return JSONResponse(
        content={
            "name": "R.E.M.I Backend API",
            "version": "1.0.0",
            "status": "operational",
            "environment": settings.ENV,
            "docs": "/docs",
            "health": "/api/v1/health",
        }
    )


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc: Exception) -> JSONResponse:
    """
    Global exception handler for unhandled errors.
    
    Args:
        request: The request that caused the exception
        exc: The exception that was raised
        
    Returns:
        JSONResponse: Error response with details
    """
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": str(exc) if settings.DEBUG else "An unexpected error occurred",
            "type": type(exc).__name__,
        }
    )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )
