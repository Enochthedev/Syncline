from api.graphql import schema, get_context
from strawberry.fastapi import GraphQLRouter
from fastapi import FastAPI
from contextlib import asynccontextmanager
from config.config import settings
from db.init_db import initialize_infrastructure, cleanup_infrastructure
from api.routes.whatsapp import initialize_whatsapp_service, cleanup_whatsapp_service
from services.event_bus import EventBus
from api.websocket.manager import websocket_manager
from api.routes.websocket import websocket_handlers
from services.batch_processing import BatchScheduler
import logging

# Import all models to ensure SQLAlchemy can resolve relationships
from db.models.participant import Participant
from db.models.thread import Thread
from db.models.message import Message
from db.models.attachment import Attachment
from db.models.entity import Entity, MessageEntity
from db.models.summary import Summary
from db.models.audit import AuditLog
from db.models.contact import Contact
from db.models.memory import ContactMemory, Commitment, FileReference, Nudge, ContactDossier
from db.models.user import User as DBUser
from api.auth.models import User as AuthUser, Role, Permission, APIKey, UserRole

# Import API router
from api.main import api_router

# Import monitoring services
from services.monitoring.logging import setup_structured_logging
from services.monitoring.health import register_default_health_checks
from services.monitoring.metrics import get_metrics_collector, collect_system_metrics
from api.middleware.monitoring import MonitoringMiddleware

# Set up structured logging
setup_structured_logging(
    level="INFO",
    service_name="mesh-system",
    enable_console=True,
    log_file="logs/mesh-system.log"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("🚀 Starting R.E.M.I backend...")
    try:
        await initialize_infrastructure()
        logger.info("✅ Infrastructure initialized successfully")

        # Initialize monitoring
        logger.info("📈 Initializing monitoring and observability...")
        register_default_health_checks()

        # Initialize metrics collector
        metrics_collector = get_metrics_collector()
        metrics_collector.set_system_info(
            version="1.0.0",
            environment=settings.ENVIRONMENT,
            build_date="2024-01-16"
        )

        # Initialize WebSocket manager
        await websocket_manager.start()
        logger.info("✅ WebSocket manager initialized")

        # Start WebSocket event listeners
        await websocket_handlers.start_event_listeners()
        logger.info("✅ WebSocket event listeners started")

        # Initialize batch processing scheduler
        logger.info("⏰ Initializing batch processing scheduler...")
        batch_scheduler = BatchScheduler()
        await batch_scheduler.start()
        logger.info("✅ Batch processing scheduler started")

        # Initialize WhatsApp service if enabled
        if settings.WHATSAPP_BRIDGE_ENABLED:
            event_bus = EventBus()  # This would be properly initialized in production
            whatsapp_config = {
                'max_bridges': 10,
                'matrix_config': {
                    'homeserver_url': settings.MATRIX_HOMESERVER_URL,
                    'access_token': settings.MATRIX_ACCESS_TOKEN,
                    'user_id': settings.MATRIX_USER_ID,
                    'device_id': settings.MATRIX_DEVICE_ID,
                    'bridges': {
                        'whatsapp': {
                            'enabled': True,
                            'executable_path': settings.WHATSAPP_BRIDGE_EXECUTABLE,
                            'config_path': settings.WHATSAPP_BRIDGE_CONFIG_PATH,
                            'database_path': settings.WHATSAPP_BRIDGE_DATABASE_PATH
                        }
                    }
                }
            }
            await initialize_whatsapp_service(whatsapp_config, event_bus)
            logger.info("✅ WhatsApp integration service initialized")

    except Exception as e:
        logger.error(f"❌ Failed to initialize infrastructure: {e}")
        raise

    yield

    # Shutdown
    logger.info("🛑 Shutting down R.E.M.I backend...")

    # Cleanup WebSocket manager
    await websocket_manager.stop()
    logger.info("✅ WebSocket manager stopped")

    # Cleanup WhatsApp service
    if settings.WHATSAPP_BRIDGE_ENABLED:
        await cleanup_whatsapp_service()
        logger.info("✅ WhatsApp service cleaned up")

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

# Add monitoring middleware
app.add_middleware(MonitoringMiddleware, service_name="mesh-api")

# Include API routes
app.include_router(api_router)

# Add GraphQL endpoint

graphql_app = GraphQLRouter(schema, context_getter=get_context)
app.include_router(graphql_app, prefix="/graphql", tags=["GraphQL"])


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
