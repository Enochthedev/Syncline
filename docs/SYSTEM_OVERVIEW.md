# MESH Ingestion System - System Overview

## Table of Contents
- [System Architecture](#system-architecture)
- [Active Components](#active-components)
- [API Endpoints](#api-endpoints)
- [Database Schema](#database-schema)
- [Event Streams](#event-streams)
- [Platform Connectors](#platform-connectors)
- [Configuration](#configuration)
- [Monitoring & Health](#monitoring--health)
- [Development Status](#development-status)

## System Architecture

The MESH (Multi-platform Event Stream Hub) Ingestion System is a real-time message processing platform that ingests, normalizes, and processes messages from multiple communication platforms.

### Core Components

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Platform      │    │   Event Bus     │    │   Database      │
│   Connectors    │───▶│   (Redis)       │───▶│   (PostgreSQL)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Message       │    │   Normalization │    │   Entity        │
│   Processing    │    │   Service       │    │   Extraction    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Active Components

### ✅ Implemented & Active

#### Core Infrastructure
- **Event Bus System** (`services/event_bus.py`)
  - Redis Streams-based messaging
  - Producer/consumer patterns
  - Consumer groups for reliability
  - Event types: `MESSAGE_RECEIVED`, `MESSAGE_NORMALIZED`, `MESSAGE_PROCESSED`

- **Message Schema** (`services/message_schema.py`)
  - Unified message representation
  - Platform-agnostic data structures
  - Support for attachments, participants, threads

- **Database Models** (`db/models/`)
  - Message storage (`message.py`)
  - Entity extraction (`entity.py`)
  - Alembic migrations for schema management

- **Configuration System** (`config/config.py`)
  - Environment-based configuration
  - Platform-specific settings
  - Database and Redis connection management

#### Platform Connectors
- **Base Connector Framework** (`integrations/base_connector.py`)
  - Abstract base class for all connectors
  - Authentication management
  - Rate limiting and circuit breaker patterns
  - Health monitoring

- **Gmail Connector** (`integrations/gmail_connector.py`) ✅ **ACTIVE**
  - OAuth 2.0 authentication
  - Real-time push notifications
  - Historical message fetching
  - Webhook handling
  - Message content extraction (text, HTML, attachments)

#### Supporting Services
- **Message Normalizer** (`services/message_normalizer.py`)
  - Platform-specific to unified format conversion
  - Content type detection and conversion
  - Attachment processing

- **Ingestion Service** (`services/ingest_service.py`)
  - Orchestrates message processing pipeline
  - Event routing and handling
  - Error recovery mechanisms

### 🚧 In Development

#### Platform Connectors
- **Slack Connector** - Planned
- **Discord Connector** - Planned
- **WhatsApp Connector** - Planned
- **Twitter/X Connector** - Planned

#### Advanced Features
- **Entity Extraction Service** - Planned
- **Message Summarization** - Planned
- **Thread Analysis** - Planned

## API Endpoints

### Main Application (`api/main.py`)

#### Health & Status
- `GET /health` - System health check
- `GET /status` - Detailed system status

#### Platform Management
- `GET /platforms` - List supported platforms
- `GET /platforms/{platform}/status` - Platform-specific status

#### Message Operations
- `GET /messages` - Query messages (with filters)
- `GET /messages/{id}` - Get specific message
- `POST /messages/search` - Advanced message search

#### Webhook Endpoints
- `POST /webhooks/gmail` - Gmail push notification webhook ✅ **ACTIVE**
- `POST /webhooks/slack` - Slack event webhook (planned)
- `POST /webhooks/discord` - Discord webhook (planned)

### Development Server (`main.py`)
- Basic FastAPI application for development
- Auto-reload enabled
- Debug logging

## Database Schema

### Core Tables

#### `messages`
```sql
- id (UUID, Primary Key)
- platform (VARCHAR) - Source platform
- platform_message_id (VARCHAR) - Original message ID
- thread_id (VARCHAR) - Thread/conversation ID
- sender_id (VARCHAR) - Sender identifier
- content (JSONB) - Message content (text, html, attachments)
- timestamp (TIMESTAMP) - Message timestamp
- metadata (JSONB) - Platform-specific metadata
- raw_data (JSONB) - Original platform data
- created_at (TIMESTAMP)
- updated_at (TIMESTAMP)
```

#### `entities`
```sql
- id (UUID, Primary Key)
- message_id (UUID, Foreign Key)
- entity_type (VARCHAR) - Type of entity (person, organization, etc.)
- entity_value (VARCHAR) - Entity value/name
- confidence (FLOAT) - Extraction confidence score
- metadata (JSONB) - Additional entity data
- created_at (TIMESTAMP)
```

### Indexes
- `messages_platform_idx` - Platform filtering
- `messages_timestamp_idx` - Time-based queries
- `messages_thread_idx` - Thread grouping
- `entities_message_idx` - Entity lookups

## Event Streams

### Redis Streams Configuration

#### Stream: `messages.raw`
- **Purpose**: Raw messages from platform connectors
- **Producers**: Platform connectors (Gmail, Slack, etc.)
- **Consumers**: Message normalizer
- **Retention**: 24 hours

#### Stream: `messages.normalized`
- **Purpose**: Normalized messages ready for processing
- **Producers**: Message normalizer
- **Consumers**: Ingestion service, entity extractor
- **Retention**: 7 days

#### Stream: `messages.processed`
- **Purpose**: Fully processed messages
- **Producers**: Ingestion service
- **Consumers**: Analytics, search indexer
- **Retention**: 30 days

### Consumer Groups
- `normalizer-group` - Message normalization
- `ingestion-group` - Message ingestion
- `analytics-group` - Analytics processing

## Platform Connectors

### Gmail Connector ✅ **ACTIVE**

**Status**: Fully implemented and tested  
**Authentication**: OAuth 2.0  
**Real-time**: Gmail push notifications  
**Features**:
- Historical message fetching with pagination
- Real-time webhook processing
- Content extraction (text, HTML, multipart)
- Attachment handling
- Rate limiting and error recovery

**Configuration**:
```python
GMAIL_SCOPES = "https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/gmail.modify"
GMAIL_CREDENTIALS_FILE = "config/credentials.json"
GMAIL_WEBHOOK_ENDPOINT = "/webhooks/gmail"
```

**Webhook URL**: `POST /webhooks/gmail`

### Planned Connectors

#### Slack Connector 🚧
- **Status**: Not implemented
- **Authentication**: OAuth 2.0 + Bot tokens
- **Real-time**: Events API + Socket Mode
- **Priority**: High

#### Discord Connector 🚧
- **Status**: Not implemented  
- **Authentication**: Bot tokens
- **Real-time**: Gateway WebSocket
- **Priority**: Medium

## Configuration

### Environment Variables

#### Database
```bash
DATABASE_URL=postgresql://user:pass@localhost/mesh_db
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=30
```

#### Redis
```bash
REDIS_URL=redis://localhost:6379
```

#### Gmail
```bash
GMAIL_SCOPES="https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/gmail.modify"
GMAIL_CREDENTIALS_FILE="config/credentials.json"
GMAIL_WEBHOOK_SECRET="your-webhook-secret"
GMAIL_TOPIC_NAME="projects/your-project/topics/gmail-push"
```

#### Application
```bash
ENV=development
DEBUG=true
```

## Monitoring & Health

### Health Check Endpoints

#### System Health (`GET /health`)
```json
{
  "status": "healthy",
  "timestamp": "2025-01-15T10:30:00Z",
  "components": {
    "database": "healthy",
    "redis": "healthy",
    "event_bus": "healthy"
  }
}
```

#### Platform Status (`GET /platforms/gmail/status`)
```json
{
  "platform": "gmail",
  "status": "healthy",
  "last_check": "2025-01-15T10:29:45Z",
  "messages_processed": 1250,
  "error_count": 2,
  "uptime_seconds": 86400
}
```

### Metrics & Logging

#### Key Metrics
- Messages processed per platform
- Processing latency
- Error rates
- Queue depths
- Connection health

#### Log Levels
- `DEBUG`: Detailed processing information
- `INFO`: Normal operations
- `WARNING`: Recoverable issues
- `ERROR`: Processing failures
- `CRITICAL`: System failures

## Development Status

### Completed Tasks ✅
1. **Core Infrastructure Setup** - Database, Redis, basic API
2. **Event Bus Implementation** - Redis Streams with consumer groups
3. **Message Schema Design** - Unified data structures
4. **Base Connector Framework** - Abstract connector with utilities
5. **Gmail Connector Implementation** - Full OAuth + real-time capabilities

### Current Task 🚧
6. **System Documentation** - This document

### Upcoming Tasks 📋
7. **Slack Connector Implementation**
8. **Message Normalization Service**
9. **Entity Extraction Pipeline**
10. **Thread Analysis & Summarization**
11. **Search & Analytics API**
12. **Performance Optimization**

### Testing Status
- **Unit Tests**: 18/18 passing for Gmail connector
- **Integration Tests**: Basic coverage
- **End-to-End Tests**: Not implemented
- **Load Tests**: Not implemented

## Getting Started

### Prerequisites
- Python 3.11+
- PostgreSQL 14+
- Redis 6+
- Google Cloud Project (for Gmail)

### Quick Start
```bash
# Install dependencies
pip install -r requirements.txt

# Set up database
alembic upgrade head

# Configure environment
cp .env.example .env
# Edit .env with your settings

# Run development server
python main.py
```

### Gmail Setup
1. Create Google Cloud Project
2. Enable Gmail API
3. Create OAuth 2.0 credentials
4. Download credentials.json
5. Set up push notifications topic
6. Configure webhook endpoint

---

**Last Updated**: January 15, 2025  
**Version**: 1.0.0  
**Status**: Active Development

For technical details, see individual component documentation in `/docs/components/`.