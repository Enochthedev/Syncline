from fastapi import FastAPI
from contextlib import asynccontextmanager
from config.config import settings
from db.init_db import initialize_infrastructure, cleanup_infrastructure
import logging

# Import all models to ensure SQLAlchemy can resolve relationships
from db.models.participant import Participant
from db.models.thread import Thread
from db.models.message import Message
from db.models.attachment import Attachment
from db.models.entity import Entity, MessageEntity
from db.models.summary import Summary

# Import API router
from api.main import api_router

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("🚀 Starting R.E.M.I backend...")
    try:
        await initialize_infrastructure()
        logger.info("✅ Infrastructure initialized successfully")
    except Exception as e:
        logger.error(f"❌ Failed to initialize infrastructure: {e}")
        raise

    yield

    # Shutdown
    logger.info("🛑 Shutting down R.E.M.I backend...")
    await cleanup_infrastructure()
    logger.info("✅ Cleanup completed")


# Create FastAPI app with enhanced Swagger documentation
app = FastAPI(
    title="R.E.M.I - Mesh Ingestion System",
    description="""
    Real-time External Memory Interface for Unified Message Processing
    
    R.E.M.I is a comprehensive mesh ingestion system that unifies messages from multiple platforms
    into a single, searchable, and AI-enhanced interface.
    
    Features
    - Multi-Platform Support: Gmail, Slack, Discord, WhatsApp, Twitter, Telegram, and more
    - Unified Schema: All messages normalized to a common format
    - Real-time Processing: Event-driven architecture with Redis streaming
    - AI Enhancement: Entity extraction and intelligent summarization
    - Scalable Infrastructure: Async PostgreSQL with connection pooling
    
    API Structure
    - Health: System status and health checks
    - Statistics: System metrics and platform breakdowns
    - Participants: User management across platforms
    - Threads: Conversation management and grouping
    - Messages: Message retrieval, search, and filtering
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Include API routes
app.include_router(api_router)


@app.get("/", tags=["Root"])
async def root():
    """
    Root endpoint providing basic system information.
    """
    return {
        "message": "R.E.M.I Mesh Ingestion System is online! 🚀",
        "status": "healthy",
        "version": "1.0.0",
        "docs_url": "/docs",
        "api_prefix": "/api/v1",
        "features": {
            "platforms_supported": 9,
            "real_time_processing": True,
            "ai_enhancement": True,
            "unified_schema": True
        }
    }
