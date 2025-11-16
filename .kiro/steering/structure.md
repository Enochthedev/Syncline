# Project Structure & Organization

## Directory Layout

### Root Level
```
├── main.py                 # Main application entry point with lifespan management
├── requirements.txt        # Python dependencies with AI/ML packages
├── alembic.ini            # Database migration configuration
├── docker-compose.yml     # Docker development setup
├── Dockerfile             # Container build configuration
├── .env.example           # Environment template with all required variables
└── README.md              # Comprehensive project documentation
```

### Core Application (`/api`)
```
api/
├── __init__.py
├── main.py                # API router setup with versioned endpoints
├── dependencies.py        # FastAPI dependency injection and auth
└── routes/                # API endpoint modules
    ├── health.py          # Health check and system status endpoints
    ├── stats.py           # System statistics and metrics
    ├── participants.py    # User/participant management across platforms
    ├── threads.py         # Conversation thread operations and grouping
    └── messages.py        # Message CRUD, search, and filtering
```

### Configuration (`/config`)
```
config/
├── config.py              # Centralized Pydantic Settings with validation
├── env.py                 # Alembic environment configuration
└── credentials.json       # OAuth credentials (gitignored, platform-specific)
```

### Database Layer (`/db`)
```
db/
├── base.py                # SQLAlchemy declarative base with UUID support
├── session.py             # Async database session management
├── init_db.py             # Database initialization and cleanup utilities
├── redis_client.py        # Redis connection management for streams
├── models/                # SQLAlchemy models with relationships
│   ├── message.py         # Core message model with platform enum
│   ├── thread.py          # Conversation threads with metadata
│   ├── participant.py     # Users/participants across platforms
│   ├── attachment.py      # File attachments with blob storage
│   ├── entity.py          # Extracted entities with confidence scores
│   ├── summary.py         # AI-generated summaries and insights
│   ├── memory.py          # Long-term memory and context
│   ├── contact.py         # Contact information and relationships
│   └── user.py            # System users and authentication
└── alembic/               # Database migrations
    ├── versions/          # Migration files with descriptive names
    ├── env.py             # Migration environment setup
    └── script.py.mako     # Migration template
```

### Business Logic (`/services`)
```
services/
├── event_bus.py           # Redis Streams event system with consumer groups
├── ingest_service.py      # Message ingestion orchestration
├── blob_storage.py        # File storage abstraction (local/cloud)
├── message_normalizer.py  # Platform message normalization
├── message_schema.py      # Unified message schemas and validation
├── ai/                    # AI processing services (local-first)
│   ├── __init__.py
│   ├── base.py            # Base AI agent framework
│   ├── detector.py        # Content detection and classification
│   ├── embeddings.py      # Text embedding service with ChromaDB
│   ├── engine.py          # AI processing engine with Ollama
│   ├── providers.py       # LLM provider abstractions (local/cloud)
│   ├── pii_redaction.py   # PII detection and removal with Presidio
│   ├── entity_extraction.py # Named entity recognition with spaCy
│   ├── entity/            # Entity processing modules
│   │   ├── __init__.py
│   │   ├── extractor.py   # Entity extraction logic
│   │   ├── processors.py  # Entity post-processing
│   │   └── types.py       # Entity type definitions
│   ├── summary/           # Summarization services
│   │   ├── __init__.py
│   │   ├── agent.py       # Summary generation agent
│   │   ├── content_parser.py # Content parsing and preparation
│   │   ├── data_analyzer.py # Data analysis for summaries
│   │   ├── database.py    # Summary database operations
│   │   ├── factory.py     # Summary service factory
│   │   ├── prompt_builder.py # Dynamic prompt construction
│   │   └── types.py       # Summary type definitions
│   └── embedding/         # Embedding utilities
│       ├── __init__.py
│       └── types.py       # Embedding type definitions
├── message/               # Message processing pipeline
│   ├── __init__.py
│   ├── content_processor.py # Content cleaning and formatting
│   ├── normalizer.py      # Message normalization logic
│   └── schema.py          # Message data structures
├── storage/               # Storage backends
│   ├── __init__.py
│   ├── backends.py        # Storage implementations (local/S3/etc)
│   └── blob_storage.py    # Blob storage interface
├── vector_db/             # Vector database services
│   ├── __init__.py
│   ├── chroma_client.py   # ChromaDB integration with persistence
│   ├── integration.py     # Vector DB operations and queries
│   ├── batch_processor.py # Batch processing for embeddings
│   └── types.py           # Vector DB type definitions
└── events/                # Event system types
    ├── __init__.py
    └── types.py           # Event type definitions and enums
```

### Platform Integrations (`/integrations`)
```
integrations/
├── __init__.py
├── base_connector.py      # Abstract connector framework with health checks
├── connector_manager.py   # Connector lifecycle management
├── rate_limiter.py        # Rate limiting utilities with backoff
├── token_manager.py       # OAuth token management and refresh
├── gmail_connector.py     # Gmail integration (fully implemented)
├── gmail_factory.py       # Gmail connector factory
├── gmail_token_handler.py # Gmail-specific token handling
├── gmail_client/          # Gmail API client modules
│   ├── __init__.py
│   ├── auth.py            # Authentication and OAuth flow
│   └── fetch.py           # Message fetching with pagination
├── x_client.py            # Twitter/X integration (planned)
└── x_client/              # Twitter/X client modules
    ├── __init__.py
    ├── auth.py            # Twitter OAuth implementation
    └── fetch.py           # Tweet fetching logic
```

### Testing (`/tests`)
```
tests/
├── README.md              # Testing documentation and guidelines
├── __init__.py
├── test_infrastructure.py # Database and Redis infrastructure tests
├── test_message_schema.py # Schema validation and serialization tests
├── test_content_processor.py # Content processing pipeline tests
├── test_message_normalizer.py # Message normalization tests
├── test_gmail_connector.py # Gmail integration unit tests
├── test_gmail_integration.py # End-to-end Gmail integration tests
├── test_gmail_connector_simple.py # Simplified Gmail tests
├── test_event_bus.py      # Event system and Redis Streams tests
├── test_event_integration.py # Event integration tests
├── test_blob_storage.py   # File storage tests
├── test_entity_extraction.py # AI entity extraction tests
├── test_summary_agent.py  # AI summarization tests
├── test_summary_generation.py # Summary generation tests
├── test_summary_utils.py  # Summary utility tests
├── test_embedding_service.py # Embedding service tests
├── test_vector_db_integration.py # Vector database tests
├── test_ai_processing_engine.py # AI processing engine tests
├── test_pii_redaction.py  # PII redaction tests
├── test_rate_limiter.py   # Rate limiting tests
├── test_token_manager.py  # Token management tests
├── test_base_connector.py # Base connector framework tests
├── test_connector_manager.py # Connector management tests
└── test_mime_utils.py     # MIME utility tests
```

### Documentation (`/docs`)
```
docs/
├── SYSTEM_OVERVIEW.md     # Architecture and component overview
├── API_REFERENCE.md       # Complete API documentation
├── DEPLOYMENT_GUIDE.md    # Production deployment guide
├── AI_SETUP.md            # AI service configuration (Ollama, ChromaDB)
├── AI_SERVICE_OPTIMIZATION.md # AI performance optimization
├── M1_AIR_SETUP.md        # M1 Mac specific setup instructions
├── HARDWARE_MIGRATION.md  # Hardware migration guide
└── SERVICE_ORGANIZATION.md # Service architecture documentation
```

### Utilities & Scripts (`/utils`, `/scripts`)
```
utils/
└── mime_utils.py          # MIME type processing and validation

scripts/
├── setup_ai.py           # AI service initialization and setup
├── ai_status.py          # AI service health check and diagnostics
└── vector_db_manager.py  # Vector database management utilities
```

### Storage & Data (`/storage`, `/vector_db`)
```
storage/
└── attachments/          # File attachment storage by platform
    └── ms/               # Platform-specific attachment folders
        └── msg123/       # Message-specific attachment storage

vector_db/                # ChromaDB persistence directory
├── chroma.sqlite3        # Vector database SQLite file
└── [uuid]/               # Vector index files and metadata
    ├── data_level0.bin   # Vector data files
    ├── header.bin        # Index header
    ├── length.bin        # Vector lengths
    └── link_lists.bin    # Index link lists
```

## Code Organization Principles

### Separation of Concerns
- **API layer** (`/api`): Request/response handling, validation, and routing
- **Service layer** (`/services`): Business logic, orchestration, and processing
- **Data layer** (`/db`): Database models, migrations, and persistence
- **Integration layer** (`/integrations`): External API interactions and connectors

### Abstract Base Classes
- `BaseConnector`: Platform integration framework with health monitoring
- `BaseAIAgent`: AI processing framework (planned)
- `Base`: SQLAlchemy model base class with UUID primary keys

### Event-Driven Architecture
- Redis Streams for reliable inter-service communication
- Event types defined in `services/events/types.py`
- Consumer groups for scalable and fault-tolerant processing
- Event bus in `services/event_bus.py` with producer/consumer patterns

### Database Design Patterns
- **UUID Primary Keys**: All models use UUID for distributed compatibility
- **Platform Enums**: Standardized platform identification
- **JSON Metadata**: Flexible platform-specific data storage
- **Relationship Management**: SQLAlchemy relationships with cascade options
- **Indexing Strategy**: Optimized indexes for common query patterns

### File Naming Conventions
- **snake_case**: All Python files and directories
- **Descriptive names**: `message_normalizer.py`, `gmail_connector.py`
- **Service suffix**: Core services end with `_service.py`
- **Test prefix**: All tests start with `test_`
- **Model names**: Singular nouns (`message.py`, `thread.py`)

### Import Patterns
- **Relative imports**: Within packages (`from .base import BaseConnector`)
- **Absolute imports**: Cross-package (`from services.event_bus import EventBus`)
- **Type imports**: Use `from typing import` for type hints
- **Model imports**: Import all models in `main.py` for SQLAlchemy relationships

### Configuration Management
- **Environment-based**: Configuration in `config/config.py` using Pydantic Settings
- **Platform-specific**: Settings with prefixes (e.g., `GMAIL_`, `SLACK_`)
- **Secure credentials**: OAuth credentials in separate files (gitignored)
- **Validation**: Built-in validation and type checking with Pydantic