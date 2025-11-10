# R.E.M.I Backend Rebuild

A clean, maintainable backend implementation for the R.E.M.I (Real-time External Memory Interface) communication aggregator system.

## Overview

This backend is architected as a four-stage pipeline system:
1. **Connection Stage**: OAuth flows and credential management
2. **Collection Stage**: Message fetching (historical + real-time)
3. **Cleaning Stage**: Message normalization into unified schema
4. **Matching Stage**: Contact matching and thread grouping
5. **AI Stage**: Embeddings, entity extraction, and summarization

## Quick Start

### Prerequisites

- Python 3.11+
- Docker and Docker Compose
- PostgreSQL 14+ (or use Docker)
- Redis 6+ (or use Docker)

### Local Development Setup

1. **Clone and navigate to backend directory**
   ```bash
   cd apps/backend
   ```

2. **Create virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On macOS/Linux
   # or
   .venv\Scripts\activate  # On Windows
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Start infrastructure services with Docker**
   ```bash
   docker-compose up -d
   ```

   This starts:
   - PostgreSQL on port 5432
   - Redis on port 6379
   - Ollama on port 11434
   - ChromaDB on port 8001

6. **Initialize database**
   ```bash
   # Run migrations
   alembic upgrade head
   ```

7. **Download AI models (optional)**
   ```bash
   # Pull tinyllama model for Ollama
   docker exec -it remi_ollama ollama pull tinyllama:latest
   
   # Pull embedding model
   docker exec -it remi_ollama ollama pull nomic-embed-text:latest
   ```

8. **Start development server**
   ```bash
   python main.py
   # or
   uvicorn main:app --reload
   ```

9. **Access the API**
   - API: http://localhost:8000
   - API Docs: http://localhost:8000/docs
   - Health Check: http://localhost:8000/api/v1/health

## Project Structure

```
apps/backend/
├── api/                    # FastAPI routes and endpoints
│   ├── routes/            # API route modules
│   ├── dependencies.py    # Dependency injection
│   └── main.py           # API router setup
├── config/                # Configuration management
│   └── config.py         # Pydantic settings
├── db/                    # Database layer
│   ├── models/           # SQLAlchemy models
│   ├── alembic/          # Database migrations
│   ├── base.py           # Base model class
│   ├── session.py        # Session management
│   └── redis_client.py   # Redis connection
├── integrations/          # Platform connectors
│   ├── base_connector.py # Abstract base class
│   ├── gmail_connector.py
│   ├── slack_connector.py
│   └── ...
├── services/              # Business logic
│   ├── ai/               # AI processing services
│   ├── message/          # Message processing
│   ├── vector_db/        # Vector database
│   ├── event_bus.py      # Redis Streams
│   └── ...
├── tests/                 # Test suite
├── utils/                 # Utility functions
├── main.py               # Application entry point
├── requirements.txt      # Python dependencies
├── docker-compose.yml    # Docker services
├── Dockerfile            # Container build
└── .env.example          # Environment template
```

## Docker Commands

### Start all services
```bash
docker-compose up -d
```

### Stop all services
```bash
docker-compose down
```

### View logs
```bash
docker-compose logs -f
```

### Restart a specific service
```bash
docker-compose restart postgres
```

### Check service health
```bash
docker-compose ps
```

### Access Ollama CLI
```bash
docker exec -it remi_ollama ollama list
docker exec -it remi_ollama ollama pull tinyllama:latest
```

## Database Management

### Create a new migration
```bash
alembic revision --autogenerate -m "Description of changes"
```

### Apply migrations
```bash
alembic upgrade head
```

### Rollback migration
```bash
alembic downgrade -1
```

### Check current migration
```bash
alembic current
```

### View migration history
```bash
alembic history
```

## Testing

### Run all tests
```bash
pytest
```

### Run specific test file
```bash
pytest tests/test_gmail_connector.py -v
```

### Run with coverage
```bash
pytest --cov=. --cov-report=html
```

### Run async tests
```bash
pytest tests/test_infrastructure.py -v
```

## API Documentation

Once the server is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

## Environment Variables

Key environment variables (see `.env.example` for complete list):

### Core
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `ENV`: Environment (development/production)
- `DEBUG`: Enable debug mode

### AI Services
- `OLLAMA_BASE_URL`: Ollama API endpoint
- `CHROMA_HOST`: ChromaDB host
- `DEFAULT_LLM_PROVIDER`: AI provider (ollama/openai/anthropic)

### Platform Integrations
- `GMAIL_CLIENT_ID`: Gmail OAuth client ID
- `SLACK_CLIENT_ID`: Slack OAuth client ID
- `DISCORD_BOT_TOKEN`: Discord bot token
- etc.

## Development Workflow

### Stage-by-Stage Development

The system is designed for independent stage development:

1. **Connection Stage**: Start with OAuth flows
2. **Collection Stage**: Implement message fetching
3. **Cleaning Stage**: Build normalization logic
4. **Matching Stage**: Create contact matching
5. **AI Stage**: Add AI processing

Each stage can be tested independently with mock data.

### Adding a New Platform

1. Create connector in `integrations/`
2. Extend base connector class
3. Implement required methods
4. Add platform-specific tests
5. Update configuration

## Troubleshooting

### Database connection issues
```bash
# Check if PostgreSQL is running
docker-compose ps postgres

# View PostgreSQL logs
docker-compose logs postgres

# Restart PostgreSQL
docker-compose restart postgres
```

### Redis connection issues
```bash
# Check Redis status
docker exec -it remi_redis redis-cli ping

# View Redis logs
docker-compose logs redis
```

### Ollama model issues
```bash
# List installed models
docker exec -it remi_ollama ollama list

# Pull a model
docker exec -it remi_ollama ollama pull tinyllama:latest

# Test model
docker exec -it remi_ollama ollama run tinyllama "Hello"
```

### ChromaDB issues
```bash
# Check ChromaDB health
curl http://localhost:8001/api/v1/heartbeat

# View ChromaDB logs
docker-compose logs chromadb
```

## Production Deployment

### Build production image
```bash
docker build --target production -t remi-backend:latest .
```

### Run production container
```bash
docker run -d \
  --name remi-backend \
  -p 8000:8000 \
  --env-file .env.production \
  remi-backend:latest
```

### Environment-specific configurations
- Use `.env.production` for production settings
- Enable HTTPS/TLS
- Configure proper secrets management
- Set up monitoring and logging
- Configure backup strategies

## Contributing

1. Follow the existing code structure
2. Write tests for new features
3. Update documentation
4. Follow Python best practices (PEP 8)
5. Use type hints
6. Write descriptive commit messages

## Architecture Documentation

For detailed architecture information, see:
- [Design Document](../../.kiro/specs/backend-rebuild/design.md)
- [Requirements](../../.kiro/specs/backend-rebuild/requirements.md)
- [Implementation Tasks](../../.kiro/specs/backend-rebuild/tasks.md)

## License

[Your License Here]
