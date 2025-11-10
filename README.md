# MESH Ingestion System

**Multi-platform Event Stream Hub for Real-time Message Processing**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14+-blue.svg)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-6+-red.svg)](https://redis.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Overview

MESH (Multi-platform Event Stream Hub) is a real-time message ingestion and processing system that connects to multiple communication platforms, normalizes messages into a unified format, and provides powerful APIs for querying and analysis.

## Repository Layout

```
apps/
  backend/   # FastAPI + workers
  web/       # Next.js application
  mobile/    # Expo mobile client
ops/
  infra/     # Infrastructure-as-code and deployment assets
  scripts/   # Operational automation and test runners
  test_bridges/
docs/        # Architecture and platform guides
archives/    # Legacy snapshots kept for reference
examples/    # SDK and usage demos
var/         # Runtime artifacts (databases, generated data)
```

### Key Features

🚀 **Real-time Ingestion** - Process messages as they arrive with minimal latency  
🔗 **Multi-platform Support** - Connect to Gmail, Slack, Discord, and more  
📊 **Unified Data Model** - Normalize messages from different platforms  
🔍 **Advanced Search** - Full-text search with entity extraction  
📈 **Scalable Architecture** - Event-driven design with Redis Streams  
🛡️ **Enterprise Security** - OAuth 2.0, webhook validation, encryption  
📱 **RESTful API** - Comprehensive API for integration  
🔧 **Easy Deployment** - Docker support and detailed deployment guides  

## Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL 14+
- Redis 6+
- Google Cloud Project (for Gmail integration)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-org/mesh-ingestion-system.git
   cd mesh-ingestion-system
   ```

2. **Set up virtual environment**
   ```bash
   cd apps/backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your database and Redis settings
   ```

4. **Set up database**
   ```bash
   # Create PostgreSQL database
   createdb mesh_development
   
   # Run migrations
   alembic upgrade head
   ```

5. **Start the application**
   ```bash
   python main.py
   ```

The API will be available at `http://localhost:8000`

### Docker Setup (Alternative)

```bash
# Build and start services from repo root
docker compose -f ops/infra/docker-compose.yml up -d

# Run migrations inside the app container
docker compose -f ops/infra/docker-compose.yml exec app alembic upgrade head
```

## Platform Support

| Platform | Status | Authentication | Real-time | Historical |
|----------|--------|---------------|-----------|------------|
| **Gmail** | ✅ Active | OAuth 2.0 | Push Notifications | ✅ |
| **Slack** | 🚧 Planned | OAuth 2.0 + Bot | Events API | 🚧 |
| **Discord** | 🚧 Planned | Bot Token | Gateway WS | 🚧 |
| **WhatsApp** | 📋 Roadmap | Business API | Webhooks | 📋 |
| **Twitter/X** | 📋 Roadmap | OAuth 2.0 | Streaming API | 📋 |

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Platform      │    │   Event Bus     │    │   Database      │
│   Connectors    │───▶│   (Redis)       │───▶│   (PostgreSQL)  │
│                 │    │                 │    │                 │
│ • Gmail ✅      │    │ • Raw Messages  │    │ • Messages      │
│ • Slack 🚧      │    │ • Normalized    │    │ • Entities      │
│ • Discord 🚧    │    │ • Processed     │    │ • Threads       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Webhook       │    │   Message       │    │   Search &      │
│   Handlers      │    │   Normalizer    │    │   Analytics     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## API Examples

### Get System Health
```bash
curl http://localhost:8000/health
```

### Query Messages
```bash
curl "http://localhost:8000/messages?platform=gmail&limit=10"
```

### Search Messages
```bash
curl -X POST http://localhost:8000/messages/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "text": "project update",
      "platforms": ["gmail"],
      "date_range": {
        "start": "2025-01-01T00:00:00Z",
        "end": "2025-01-15T23:59:59Z"
      }
    }
  }'
```

## Gmail Integration Setup

1. **Create Google Cloud Project**
   - Enable Gmail API
   - Create OAuth 2.0 credentials
   - Download credentials.json

2. **Configure Push Notifications**
   ```bash
   # Create Pub/Sub topic
   gcloud pubsub topics create gmail-push
   
   # Set webhook URL in your application
   export GMAIL_TOPIC_NAME="projects/your-project/topics/gmail-push"
   ```

3. **Run Initial Authentication**
   ```bash
   python -c "
   from integrations.gmail_factory import setup_gmail_integration
   import asyncio
   asyncio.run(setup_gmail_integration())
   "
   ```

## Development

### Running Tests
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_gmail_connector_simple.py -v

# Run with coverage
pytest --cov=integrations --cov-report=html
```

### Code Quality
```bash
# Format code
black .

# Lint code
flake8 .

# Type checking
mypy .
```

### Database Migrations
```bash
# Create new migration
alembic revision --autogenerate -m "Description of changes"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | Required |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379` |
| `ENV` | Environment (development/production) | `development` |
| `DEBUG` | Enable debug logging | `false` |
| `GMAIL_SCOPES` | Gmail API scopes | Gmail readonly + modify |
| `GMAIL_CREDENTIALS_FILE` | Path to Gmail credentials | `config/credentials.json` |
| `GMAIL_WEBHOOK_SECRET` | Webhook validation secret | Optional |

### Platform Configuration

Each platform connector can be configured independently:

```python
# Gmail configuration
GMAIL_CONFIG = {
    'scopes': ['https://www.googleapis.com/auth/gmail.readonly'],
    'credentials_file': 'config/gmail_credentials.json',
    'webhook_endpoint': '/webhooks/gmail',
    'max_results': 100,
    'rate_limit_rps': 10.0
}
```

## Monitoring & Observability

### Health Checks
- `GET /health` - Basic health status
- `GET /status` - Detailed system status
- `GET /platforms/{platform}/status` - Platform-specific status

### Metrics
- Messages processed per platform
- Processing latency
- Error rates
- Queue depths
- Connection health

### Logging
Structured logging with configurable levels:
- `DEBUG` - Detailed processing information
- `INFO` - Normal operations
- `WARNING` - Recoverable issues
- `ERROR` - Processing failures
- `CRITICAL` - System failures

## Deployment

### Production Deployment
See [Deployment Guide](docs/DEPLOYMENT_GUIDE.md) for detailed instructions.

### Docker Deployment
```bash
# Production build
docker build -t mesh-ingestion:latest -f ops/infra/Dockerfile .

# Run with docker-compose
docker compose -f ops/infra/docker-compose.prod.yml up -d
```

### Kubernetes Deployment
```bash
# Apply Kubernetes manifests
kubectl apply -f ops/infra/k8s/
```

## Documentation

- 📖 [System Overview](docs/SYSTEM_OVERVIEW.md) - Architecture and components
- 🔌 [API Reference](docs/API_REFERENCE.md) - Complete API documentation
- 🚀 [Deployment Guide](docs/DEPLOYMENT_GUIDE.md) - Production deployment
- 🔧 [Development Guide](docs/DEVELOPMENT.md) - Development setup and guidelines
- 🐛 [Troubleshooting](docs/TROUBLESHOOTING.md) - Common issues and solutions

## Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Development Workflow
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Run the test suite
6. Submit a pull request

### Code Standards
- Follow PEP 8 style guidelines
- Write comprehensive tests
- Document new features
- Update the changelog

## Security

### Reporting Security Issues
Please report security vulnerabilities to security@yourcompany.com

### Security Features
- OAuth 2.0 authentication
- Webhook signature validation
- Encrypted token storage
- Rate limiting
- Input validation
- SQL injection protection

## Performance

### Benchmarks
- **Message Ingestion**: 1,000+ messages/second
- **API Response Time**: <100ms (95th percentile)
- **Search Queries**: <500ms (complex queries)
- **Webhook Processing**: <50ms

### Scaling
- Horizontal scaling with multiple workers
- Database read replicas
- Redis clustering
- Load balancing

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- 📧 **Email**: support@yourcompany.com
- 💬 **Slack**: #mesh-support
- 🐛 **Issues**: [GitHub Issues](https://github.com/your-org/mesh-ingestion-system/issues)
- 📚 **Documentation**: [docs/](docs/)

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for a list of changes and version history.

## Roadmap

### Q1 2025
- ✅ Gmail connector implementation
- 🚧 Slack connector implementation
- 🚧 Message normalization service
- 📋 Entity extraction pipeline

### Q2 2025
- 📋 Discord connector
- 📋 Advanced search capabilities
- 📋 Thread analysis
- 📋 Performance optimizations

### Q3 2025
- 📋 WhatsApp Business API integration
- 📋 Real-time analytics dashboard
- 📋 Machine learning insights
- 📋 Multi-tenant support

---

**Built with ❤️ by the MESH Team**

For more information, visit our [documentation](docs/) or contact us at support@yourcompany.com.