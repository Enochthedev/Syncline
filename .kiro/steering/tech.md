# Technology Stack & Development Guide

## Core Technologies

### Backend Framework
- **FastAPI**: Modern async web framework with automatic OpenAPI documentation
- **Python 3.11+**: Required minimum version for async/await and type hints
- **Uvicorn**: ASGI server for development and production
- **Pydantic**: Data validation and settings management with BaseSettings

### Database & Storage
- **PostgreSQL 14+**: Primary database with JSONB support and UUID primary keys
- **Redis 6+**: Event streaming, caching, and real-time messaging via Redis Streams
- **SQLAlchemy 2.0**: Async ORM with declarative models and relationship management
- **Alembic**: Database migrations and schema versioning
- **asyncpg**: High-performance async PostgreSQL driver

### AI & ML Stack (Local-First)
- **Ollama**: Local LLM inference (default: tinyllama:latest for M1 Air)
- **ChromaDB**: Vector database for embeddings with local persistence
- **Sentence Transformers**: Text embeddings (nomic-embed-text:latest)
- **spaCy**: NLP processing and entity extraction
- **Presidio**: PII detection and redaction with configurable confidence thresholds
- **OpenAI/Anthropic**: Optional cloud AI APIs as fallbacks

### Integration & Authentication
- **OAuth 2.0**: Google APIs and platform authentication with token refresh
- **aiohttp**: Async HTTP client for platform APIs with session management
- **Google API Client**: Gmail integration with push notifications
- **Tweepy**: Twitter/X API integration (planned)

## Development Commands

### Environment Setup
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Environment configuration
cp .env.example .env
# Edit .env with your DATABASE_URL and other settings
```

### Database Operations
```bash
# Create database (PostgreSQL)
createdb mesh_development

# Run migrations
alembic upgrade head

# Create new migration
alembic revision --autogenerate -m "Description of changes"

# Rollback migration
alembic downgrade -1

# Check migration status
alembic current
```

### Development Server
```bash
# Start development server (recommended)
python main.py

# Alternative with uvicorn directly
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Docker development environment
docker-compose up -d
```

### Testing
```bash
# Run all tests
pytest

# Run specific test file with verbose output
pytest tests/test_gmail_connector.py -v

# Run with coverage report
pytest --cov=integrations --cov-report=html

# Run async infrastructure tests
pytest tests/test_infrastructure.py -v

# Run specific test pattern
pytest -k "test_message" -v
```

### AI Service Management
```bash
# Check AI service status
python scripts/ai_status.py

# Setup AI services (Ollama, ChromaDB)
python scripts/setup_ai.py

# Manage vector database
python scripts/vector_db_manager.py --status
```

## Configuration Patterns

### Environment Variables
- **Required**: `DATABASE_URL` (PostgreSQL connection string)
- **Optional**: `REDIS_URL` (defaults to localhost:6379)
- **Platform configs**: Prefix with platform name (e.g., `GMAIL_`, `SLACK_`)
- **AI configs**: Local-first with cloud fallbacks (`OLLAMA_BASE_URL`, `OPENAI_API_KEY`)

### Settings Management
- Centralized in `config/config.py` using Pydantic BaseSettings
- Environment-specific overrides with `.env` file support
- Built-in validation and type checking
- Secure credential handling with optional fields

## Architecture Patterns

### Event-Driven Architecture
- **Redis Streams**: Reliable message processing with consumer groups
- **Event Types**: `MESSAGE_RECEIVED`, `MESSAGE_NORMALIZED`, `MESSAGE_PROCESSED`
- **Consumer Groups**: Scalability and fault tolerance with automatic acknowledgment
- **Event Bus**: Centralized event management in `services/event_bus.py`

### Connector Pattern
- **BaseConnector**: Abstract base class for all platform integrations
- **Health Monitoring**: Built-in health checks with status enumeration
- **Rate Limiting**: Configurable rate limiting with retry logic
- **Circuit Breaker**: Fault tolerance with automatic recovery
- **Token Management**: Secure OAuth token storage and refresh

### Database Design
- **UUID Primary Keys**: All models use UUID for distributed system compatibility
- **Unified Schema**: Platform-agnostic message model with JSON metadata
- **Relationship Management**: SQLAlchemy relationships with cascade deletes
- **Indexing Strategy**: Optimized indexes for common query patterns

### AI Processing Pipeline
- **Local-First**: Ollama for LLM inference, ChromaDB for vector storage
- **Batch Processing**: Configurable batch sizes for performance
- **Entity Extraction**: spaCy-based NLP with custom entity types
- **PII Redaction**: Presidio integration with confidence thresholds
- **Embeddings**: Sentence transformers for semantic search

## Code Conventions

### File Naming
- **snake_case**: All Python files and directories
- **Descriptive names**: `message_normalizer.py`, `gmail_connector.py`
- **Service suffix**: Core services end with `_service.py`
- **Test prefix**: All tests start with `test_`

### Import Patterns
- **Relative imports**: Within packages (`from .base import BaseConnector`)
- **Absolute imports**: Cross-package (`from services.event_bus import EventBus`)
- **Type imports**: Use `from typing import` for type hints

### Error Handling
- **Custom exceptions**: Platform-specific error classes
- **Async context managers**: For resource management
- **Retry logic**: Exponential backoff with max retries
- **Circuit breakers**: Automatic failure detection and recovery

### Async Patterns
- **async/await**: Throughout the codebase for I/O operations
- **aiohttp sessions**: Reusable HTTP client sessions
- **asyncio.gather**: For concurrent operations
- **Context managers**: For lifecycle management

## Dependencies Management

### Core Dependencies
- `fastapi[all]`: Web framework with all extras including validation
- `sqlalchemy[asyncio]`: Async ORM with PostgreSQL support
- `asyncpg`: High-performance PostgreSQL async driver
- `redis`: Redis client with streams support
- `alembic`: Database migrations
- `pydantic-settings`: Configuration management

### AI/ML Dependencies
- `chromadb`: Vector database with local persistence
- `sentence-transformers`: Text embeddings
- `spacy`: NLP processing and entity extraction
- `presidio-analyzer`, `presidio-anonymizer`: PII handling
- `anthropic`, `openai`: Optional cloud AI APIs

### Platform Integration
- `google-api-python-client`: Gmail API integration
- `google-auth-oauthlib`: OAuth 2.0 authentication flows
- `tweepy`: Twitter API (planned integration)
- `aiohttp`: Async HTTP client for API calls

### Development & Testing
- `pytest`, `pytest-asyncio`: Testing framework with async support
- `python-dotenv`: Environment variable management
- `uvicorn`: ASGI server for development