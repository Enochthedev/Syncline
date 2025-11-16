# Backend Rebuild Design Document

## Overview

The R.E.M.I backend rebuild is architected as a four-stage pipeline system with clear separation of concerns. Each stage operates independently and communicates through an event-driven architecture using Redis Streams. This design prioritizes testability, maintainability, and the ability to run each stage in isolation.

### Design Principles

1. **Stage Independence**: Each of the four stages (Connection, Collection, Cleaning, Matching, AI) can be tested and deployed independently
2. **Event-Driven Communication**: Redis Streams provide reliable, ordered message passing between stages
3. **Fail-Safe Processing**: Failures in one stage don't cascade to others; each stage can retry independently
4. **Local-First AI**: Prioritize local models (Ollama, ChromaDB) with cloud fallbacks for cost and privacy
5. **Platform Abstraction**: Unified connector interface allows easy addition of new platforms

## Architecture

### High-Level System Flow

```
User → Connection Stage → Collection Stage → Cleaning Stage → Matching Stage → AI Stage → API/Query Interface
         ↓                    ↓                  ↓                ↓               ↓
      PostgreSQL          Redis Streams      PostgreSQL      PostgreSQL      ChromaDB
```

### Stage Pipeline

1. **Connection Stage**: Manages OAuth flows and credential storage
2. **Collection Stage**: Fetches messages from platforms (historical + real-time)
3. **Cleaning Stage**: Normalizes messages into unified schema
4. **Matching Stage**: Associates threads with contacts across platforms
5. **AI Stage**: Generates embeddings, extracts entities, creates summaries

### Technology Stack

- **API Framework**: FastAPI with async/await
- **Database**: PostgreSQL 14+ with JSONB support
- **Event Bus**: Redis 6+ with Streams
- **AI/ML**: Ollama (local LLM), ChromaDB (vector DB), spaCy (NER)
- **Platform Bridges**: 
  - WhatsApp: Mautrix-WhatsApp bridge (Matrix protocol)
  - Gmail: Google API Client
  - Slack: Slack SDK
  - Discord: Discord.py
  - Twitter: Tweepy
  - Telegram: Telethon

## Components and Interfaces

### 1. Connection Stage

**Purpose**: Authenticate users with platforms and manage credentials

**Components**:
- `ConnectionManager`: Orchestrates OAuth flows for all platforms
- `PlatformConnector` (abstract base): Defines interface for platform-specific connectors
- `CredentialStore`: Encrypts and stores OAuth tokens in PostgreSQL
- `TokenRefresher`: Background service that refreshes expiring tokens

**Platform Connectors**:
- `GmailConnector`: OAuth 2.0 with Google API
- `SlackConnector`: OAuth 2.0 with Slack API
- `DiscordConnector`: OAuth 2.0 with Discord API
- `WhatsAppConnector`: Mautrix bridge connection or WhatsApp Business API
- `TwitterConnector`: OAuth 1.0a/2.0 with Twitter API
- `TelegramConnector`: Bot API or MTProto via Telethon

**API Endpoints**:
```
POST   /api/v1/connections/initiate/{platform}  # Start OAuth flow
GET    /api/v1/connections/callback/{platform}  # OAuth callback
GET    /api/v1/connections                      # List active connections
DELETE /api/v1/connections/{connection_id}      # Disconnect platform
GET    /api/v1/connections/{connection_id}/health # Check connection status
```

**Events Emitted**:
- `CONNECTION_ESTABLISHED`: When OAuth completes successfully
- `CONNECTION_FAILED`: When OAuth fails
- `CONNECTION_REFRESHED`: When tokens are refreshed
- `CONNECTION_REVOKED`: When user disconnects

**Database Schema**:
```sql
CREATE TABLE platform_connections (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    platform VARCHAR(50) NOT NULL,
    credentials JSONB NOT NULL,  -- Encrypted
    status VARCHAR(20) NOT NULL,
    last_sync_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### 2. Collection Stage

**Purpose**: Fetch messages from connected platforms (historical + real-time)

**Components**:
- `CollectionOrchestrator`: Manages collection jobs for all platforms
- `HistoricalFetcher`: Fetches past messages with pagination
- `RealtimeListener`: Listens for new messages via webhooks or polling
- `RateLimiter`: Enforces platform-specific rate limits
- `CollectionQueue`: Prioritizes collection tasks

**Collection Strategies**:
- **Webhook-based** (Gmail, Slack, Discord): Register webhooks for push notifications
- **Polling-based** (Twitter, Telegram): Poll at configurable intervals
- **Bridge-based** (WhatsApp): Connect to Mautrix bridge via Matrix protocol

**API Endpoints**:
```
POST   /api/v1/collection/start/{connection_id}     # Start collection
POST   /api/v1/collection/stop/{connection_id}      # Stop collection
GET    /api/v1/collection/status/{connection_id}    # Collection status
POST   /api/v1/collection/webhook/{platform}        # Webhook receiver
GET    /api/v1/collection/history/{connection_id}   # Historical fetch status
```

**Events Consumed**:
- `CONNECTION_ESTABLISHED`: Triggers initial historical fetch

**Events Emitted**:
- `MESSAGE_COLLECTED`: Raw message fetched from platform
- `COLLECTION_COMPLETED`: Historical fetch finished
- `COLLECTION_ERROR`: Collection failed

**Database Schema**:
```sql
CREATE TABLE raw_messages (
    id UUID PRIMARY KEY,
    connection_id UUID NOT NULL,
    platform VARCHAR(50) NOT NULL,
    platform_message_id VARCHAR(255) NOT NULL,
    raw_data JSONB NOT NULL,
    collected_at TIMESTAMP DEFAULT NOW(),
    processed BOOLEAN DEFAULT FALSE,
    UNIQUE(connection_id, platform_message_id)
);

CREATE TABLE collection_jobs (
    id UUID PRIMARY KEY,
    connection_id UUID NOT NULL,
    job_type VARCHAR(20) NOT NULL,  -- 'historical' or 'realtime'
    status VARCHAR(20) NOT NULL,
    progress JSONB,
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);
```

### 3. Cleaning Stage

**Purpose**: Normalize platform-specific messages into unified schema

**Components**:
- `MessageNormalizer`: Transforms raw messages to unified format
- `PlatformParser` (per platform): Extracts fields from platform-specific formats
- `AttachmentHandler`: Downloads and stores attachments
- `SchemaValidator`: Validates normalized messages against schema

**Unified Message Schema**:
```python
{
    "id": "uuid",
    "platform": "gmail|slack|discord|whatsapp|twitter|telegram",
    "platform_message_id": "string",
    "thread_id": "string",  # Platform-specific thread identifier
    "sender": {
        "platform_user_id": "string",
        "name": "string",
        "email": "string|null",
        "phone": "string|null"
    },
    "recipients": [
        {
            "platform_user_id": "string",
            "name": "string",
            "email": "string|null",
            "phone": "string|null"
        }
    ],
    "content": {
        "text": "string",
        "html": "string|null",
        "format": "plain|html|markdown"
    },
    "attachments": [
        {
            "id": "uuid",
            "filename": "string",
            "mime_type": "string",
            "size_bytes": "integer",
            "storage_path": "string"
        }
    ],
    "metadata": {
        "platform_specific": {},  # Preserve original fields
        "reactions": [],
        "edited": "boolean",
        "forwarded": "boolean"
    },
    "timestamp": "iso8601",
    "collected_at": "iso8601",
    "cleaned_at": "iso8601"
}
```

**API Endpoints**:
```
GET    /api/v1/messages                    # List normalized messages
GET    /api/v1/messages/{message_id}       # Get message details
GET    /api/v1/messages/stats               # Cleaning statistics
POST   /api/v1/messages/reprocess/{message_id}  # Re-clean a message
```

**Events Consumed**:
- `MESSAGE_COLLECTED`: Triggers normalization

**Events Emitted**:
- `MESSAGE_NORMALIZED`: Message cleaned and stored
- `NORMALIZATION_FAILED`: Cleaning failed

**Database Schema**:
```sql
CREATE TABLE messages (
    id UUID PRIMARY KEY,
    connection_id UUID NOT NULL,
    platform VARCHAR(50) NOT NULL,
    platform_message_id VARCHAR(255) NOT NULL,
    thread_id VARCHAR(255),
    sender_id UUID,  -- FK to participants
    content JSONB NOT NULL,
    metadata JSONB,
    timestamp TIMESTAMP NOT NULL,
    collected_at TIMESTAMP NOT NULL,
    cleaned_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(connection_id, platform_message_id)
);

CREATE TABLE attachments (
    id UUID PRIMARY KEY,
    message_id UUID NOT NULL,
    filename VARCHAR(255) NOT NULL,
    mime_type VARCHAR(100),
    size_bytes BIGINT,
    storage_path TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### 4. Matching Stage

**Purpose**: Associate message threads with contacts across platforms

**Components**:
- `ContactMatcher`: Identifies and merges contacts across platforms
- `ThreadGrouper`: Groups messages into conversation threads
- `IdentityResolver`: Matches same person across different platforms
- `ManualMergeHandler`: Allows user-driven contact merging

**Matching Strategies**:
1. **Email-based**: Match contacts with same email address
2. **Phone-based**: Match contacts with same phone number
3. **Name similarity**: Fuzzy matching on names (with user confirmation)
4. **Manual linking**: User explicitly merges contacts

**API Endpoints**:
```
GET    /api/v1/contacts                        # List all contacts
GET    /api/v1/contacts/{contact_id}           # Contact details
GET    /api/v1/contacts/{contact_id}/threads   # Threads with contact
POST   /api/v1/contacts/merge                  # Merge contacts
POST   /api/v1/contacts/split                  # Split merged contact
GET    /api/v1/threads                         # List all threads
GET    /api/v1/threads/{thread_id}             # Thread details
GET    /api/v1/threads/{thread_id}/messages    # Messages in thread
```

**Events Consumed**:
- `MESSAGE_NORMALIZED`: Triggers contact matching

**Events Emitted**:
- `CONTACT_MATCHED`: Message associated with contact
- `CONTACT_CREATED`: New contact identified
- `CONTACT_MERGED`: Contacts merged
- `THREAD_CREATED`: New thread identified

**Database Schema**:
```sql
CREATE TABLE contacts (
    id UUID PRIMARY KEY,
    canonical_name VARCHAR(255) NOT NULL,
    emails TEXT[],
    phones TEXT[],
    platform_identities JSONB,  -- {platform: user_id}
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE threads (
    id UUID PRIMARY KEY,
    platform VARCHAR(50) NOT NULL,
    platform_thread_id VARCHAR(255) NOT NULL,
    contact_id UUID,  -- FK to contacts
    title VARCHAR(500),
    participant_ids UUID[],
    message_count INTEGER DEFAULT 0,
    first_message_at TIMESTAMP,
    last_message_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(platform, platform_thread_id)
);

CREATE TABLE participants (
    id UUID PRIMARY KEY,
    contact_id UUID,  -- FK to contacts (nullable until matched)
    platform VARCHAR(50) NOT NULL,
    platform_user_id VARCHAR(255) NOT NULL,
    name VARCHAR(255),
    email VARCHAR(255),
    phone VARCHAR(50),
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(platform, platform_user_id)
);
```

### 5. AI Stage

**Purpose**: Generate embeddings, extract entities, and create summaries

**Components**:
- `EmbeddingService`: Generates vector embeddings using local models
- `EntityExtractor`: Extracts people, places, dates, topics using spaCy
- `SummaryGenerator`: Creates conversation summaries using Ollama
- `SemanticSearchEngine`: Queries ChromaDB for similar messages
- `InsightGenerator`: Analyzes communication patterns

**AI Pipeline**:
1. **Embedding Generation**: Convert message text to vectors (nomic-embed-text)
2. **Entity Extraction**: Identify named entities (spaCy)
3. **PII Detection**: Detect and optionally redact sensitive info (Presidio)
4. **Summarization**: Generate thread summaries (Ollama with tinyllama)
5. **Insight Generation**: Analyze patterns and relationships

**API Endpoints**:
```
POST   /api/v1/ai/search                       # Semantic search
POST   /api/v1/ai/summarize/{thread_id}        # Generate summary
GET    /api/v1/ai/entities/{message_id}        # Extract entities
POST   /api/v1/ai/insights/{contact_id}        # Generate insights
GET    /api/v1/ai/similar/{message_id}         # Find similar messages
POST   /api/v1/ai/ask                          # Natural language query
```

**Events Consumed**:
- `CONTACT_MATCHED`: Triggers AI processing

**Events Emitted**:
- `EMBEDDING_GENERATED`: Vector embedding created
- `ENTITIES_EXTRACTED`: Named entities identified
- `SUMMARY_GENERATED`: Thread summary created
- `AI_PROCESSING_FAILED`: AI processing error

**Database Schema**:
```sql
CREATE TABLE entities (
    id UUID PRIMARY KEY,
    message_id UUID NOT NULL,
    entity_type VARCHAR(50) NOT NULL,  -- PERSON, ORG, DATE, LOCATION, etc.
    entity_text VARCHAR(500) NOT NULL,
    confidence FLOAT,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE summaries (
    id UUID PRIMARY KEY,
    thread_id UUID NOT NULL,
    summary_type VARCHAR(50) NOT NULL,  -- 'brief', 'detailed', 'insight'
    content TEXT NOT NULL,
    metadata JSONB,
    generated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE embeddings (
    id UUID PRIMARY KEY,
    message_id UUID NOT NULL,
    vector VECTOR(768),  -- Using pgvector extension
    model VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
```

**ChromaDB Collections**:
- `message_embeddings`: All message vectors for semantic search
- `thread_embeddings`: Thread-level vectors for conversation search

## Data Models

### Core Entities

1. **User**: System user who owns connections
2. **PlatformConnection**: Authenticated link to a platform
3. **RawMessage**: Unprocessed message from platform
4. **Message**: Normalized message in unified schema
5. **Thread**: Conversation grouping
6. **Contact**: Person across platforms
7. **Participant**: Platform-specific user identity
8. **Attachment**: File associated with message
9. **Entity**: Extracted named entity
10. **Summary**: AI-generated summary
11. **Embedding**: Vector representation

### Relationships

```
User 1:N PlatformConnection
PlatformConnection 1:N RawMessage
RawMessage 1:1 Message
Message N:1 Thread
Message N:M Participant (via sender/recipients)
Thread N:1 Contact
Participant N:1 Contact
Message 1:N Attachment
Message 1:N Entity
Thread 1:N Summary
Message 1:1 Embedding
```

## Error Handling

### Stage-Level Error Handling

Each stage implements:
1. **Retry Logic**: Exponential backoff for transient failures
2. **Dead Letter Queue**: Failed messages moved to DLQ after max retries
3. **Error Logging**: Structured logs with context
4. **Health Checks**: Per-stage health endpoints
5. **Circuit Breakers**: Prevent cascade failures

### Platform-Specific Errors

- **Rate Limiting**: Respect platform limits, queue requests
- **Authentication Failures**: Trigger token refresh or user notification
- **API Changes**: Log schema mismatches for investigation
- **Network Errors**: Retry with backoff

### Data Quality Errors

- **Schema Validation**: Reject malformed messages
- **Duplicate Detection**: Skip already-processed messages
- **Missing Fields**: Use defaults or mark as incomplete

## Testing Strategy

### Unit Testing

Each component tested in isolation:
- Mock external APIs (Gmail, Slack, etc.)
- Mock database with in-memory SQLite
- Mock Redis with fakeredis
- Test each normalizer with sample platform data

### Integration Testing

Test stage-to-stage communication:
- End-to-end pipeline with test data
- Redis Streams message passing
- Database transactions and rollbacks
- Event ordering and idempotency

### Stage Testing

Each stage independently testable:
1. **Connection Stage**: Mock OAuth flows, test credential storage
2. **Collection Stage**: Mock platform APIs, test pagination
3. **Cleaning Stage**: Test normalization with real platform samples
4. **Matching Stage**: Test contact merging algorithms
5. **AI Stage**: Test with local models, mock cloud APIs

### Platform Testing

Per-platform test suites:
- Gmail: Test with Gmail API test account
- WhatsApp: Test with Mautrix bridge in dev mode
- Slack: Test with Slack workspace
- Discord: Test with Discord bot
- Twitter: Test with Twitter developer account
- Telegram: Test with Telegram bot

### Performance Testing

- Message throughput: 1000+ messages/minute
- Concurrent connections: 10+ platforms simultaneously
- Search latency: <500ms for semantic search
- Real-time processing: <30s from collection to AI

## Deployment Architecture

### Development Environment

```yaml
services:
  api:
    build: .
    ports: ["8000:8000"]
    depends_on: [postgres, redis]
  
  postgres:
    image: postgres:14
    volumes: ["pgdata:/var/lib/postgresql/data"]
  
  redis:
    image: redis:6
    volumes: ["redisdata:/data"]
  
  ollama:
    image: ollama/ollama
    volumes: ["ollama:/root/.ollama"]
  
  chromadb:
    image: chromadb/chroma
    volumes: ["chromadb:/chroma/chroma"]
  
  mautrix-whatsapp:
    image: dock.mau.dev/mautrix/whatsapp
    volumes: ["mautrix:/data"]
```

### Production Considerations

- **Horizontal Scaling**: Multiple API instances behind load balancer
- **Database**: Managed PostgreSQL with replication
- **Redis**: Redis Cluster for high availability
- **AI Services**: Dedicated GPU instances for Ollama
- **Monitoring**: Prometheus + Grafana for metrics
- **Logging**: Centralized logging with ELK stack
- **Secrets**: Vault or AWS Secrets Manager for credentials

## Security Considerations

### Authentication & Authorization

- OAuth 2.0 for platform connections
- JWT tokens for API authentication
- Role-based access control (RBAC)
- Multi-tenant isolation

### Data Protection

- Encryption at rest for credentials (AES-256)
- Encryption in transit (TLS 1.3)
- PII detection and optional redaction
- Secure credential storage with rotation

### Privacy

- User data isolation
- Configurable data retention policies
- GDPR compliance (right to deletion)
- Audit logging for data access

## Monitoring and Observability

### Metrics

- Message processing rate per stage
- API response times
- Platform connection health
- AI processing latency
- Database query performance
- Redis queue depths

### Logging

- Structured JSON logs
- Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
- Correlation IDs for request tracing
- Stage transition logging

### Alerting

- Platform connection failures
- High error rates in any stage
- Database connection issues
- Redis unavailability
- AI service failures
- Disk space warnings

## Migration from Old Backend

### Archive Strategy

1. **Backup**: Full database dump of old backend
2. **Archive Location**: `./archive/old-backend-{timestamp}/`
3. **Documentation**: Document old schema and API
4. **Data Migration**: Optional script to import old data

### Coexistence Period

- Run old and new backends in parallel
- Gradual migration of connections
- Comparison testing between systems
- Rollback plan if issues arise

## Future Enhancements

### Phase 2 Features

- Real-time WebSocket updates to clients
- Advanced analytics dashboard
- Sentiment analysis
- Topic modeling
- Relationship graphs
- Export functionality (PDF, CSV)

### Additional Platforms

- Microsoft Teams
- LinkedIn Messages
- Facebook Messenger
- Instagram DMs
- Signal (if API available)

### AI Enhancements

- Multi-language support
- Custom entity types
- Conversation insights
- Predictive responses
- Smart notifications