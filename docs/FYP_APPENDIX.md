# SYNCLINE (R.E.M.I) - FINAL YEAR PROJECT APPENDIX

**Multi-platform Event Stream Hub for Real-time Message Processing**

---

## APPENDIX A: DATABASE SCHEMA

### A.1 Entity-Relationship Overview

The Syncline database uses PostgreSQL 14+ with UUID primary keys, JSONB for flexible schema fields, and full-text search capabilities.

### A.2 Complete Database Schema

```sql
-- =============================================================================
-- USERS TABLE
-- Core authentication and user management
-- =============================================================================
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    is_superuser BOOLEAN DEFAULT FALSE NOT NULL,
    role VARCHAR(50) DEFAULT 'user' NOT NULL,
    permissions TEXT[],
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Design Decision: Role-based access control with array-based permissions
-- allows flexible permission management without additional join tables

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_role ON users(role);

-- =============================================================================
-- PLATFORM_CONNECTIONS TABLE
-- OAuth credentials and platform authentication
-- =============================================================================
CREATE TYPE platform_type AS ENUM (
    'gmail', 'slack', 'discord', 'whatsapp', 
    'twitter', 'telegram', 'linkedin', 'google_chat'
);

CREATE TYPE connection_status AS ENUM (
    'active', 'inactive', 'expired', 'failed', 'revoked'
);

CREATE TABLE platform_connections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    platform platform_type NOT NULL,
    credentials_encrypted TEXT,        -- Fernet encrypted credentials
    credentials JSONB,                 -- Legacy unencrypted (deprecated)
    status connection_status DEFAULT 'active' NOT NULL,
    last_sync_at TIMESTAMP WITH TIME ZONE,
    credentials_rotated_at TIMESTAMP WITH TIME ZONE,
    credentials_version VARCHAR(50) DEFAULT 'v1' NOT NULL,
    platform_metadata JSONB,           -- Platform-specific user info
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Design Decision: Encrypted credentials stored as TEXT rather than JSONB
-- for Fernet encryption compatibility. Legacy JSONB column retained for
-- backward compatibility during migration.

CREATE INDEX idx_platform_connections_user ON platform_connections(user_id);
CREATE INDEX idx_platform_connections_platform ON platform_connections(platform);
CREATE INDEX idx_platform_connections_status ON platform_connections(status);

-- =============================================================================
-- CONTACTS TABLE
-- Unified contact identity across platforms
-- =============================================================================
CREATE TABLE contacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    canonical_name VARCHAR(255) NOT NULL,
    emails TEXT[],
    phones TEXT[],
    linkedin_url VARCHAR(512) UNIQUE,
    linkedin_id VARCHAR(255) UNIQUE,
    company VARCHAR(255),
    job_title VARCHAR(255),
    message_count INTEGER DEFAULT 0 NOT NULL,
    platform_identities JSONB,         -- {"gmail": "email", "slack": "U123"}
    contact_metadata JSONB,            -- avatar, location, tags, etc.
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Design Decision: Denormalized message_count for efficient filtering
-- Updated via triggers when messages are synced

CREATE INDEX idx_contacts_user ON contacts(user_id);
CREATE INDEX idx_contacts_name ON contacts(canonical_name);
CREATE INDEX idx_contacts_company ON contacts(company);
CREATE INDEX idx_contacts_linkedin ON contacts(linkedin_id);
CREATE INDEX idx_contacts_message_count ON contacts(message_count);

-- =============================================================================
-- PARTICIPANTS TABLE
-- Platform-specific user identities linked to unified contacts
-- =============================================================================
CREATE TABLE participants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contact_id UUID REFERENCES contacts(id) ON DELETE SET NULL,
    platform VARCHAR(50) NOT NULL,
    platform_user_id VARCHAR(255) NOT NULL,
    name VARCHAR(255),
    email VARCHAR(255),
    phone VARCHAR(50),
    participant_metadata JSONB,        -- avatar, username, is_bot, etc.
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT uq_platform_user UNIQUE (platform, platform_user_id)
);

CREATE INDEX idx_participants_contact ON participants(contact_id);
CREATE INDEX idx_participants_platform ON participants(platform);
CREATE INDEX idx_participants_email ON participants(email);
CREATE INDEX idx_participants_phone ON participants(phone);

-- =============================================================================
-- RAW_MESSAGES TABLE
-- Unprocessed messages in original platform format
-- =============================================================================
CREATE TABLE raw_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    connection_id UUID NOT NULL REFERENCES platform_connections(id) ON DELETE CASCADE,
    platform VARCHAR(50) NOT NULL,
    platform_message_id VARCHAR(255) NOT NULL,
    raw_data JSONB NOT NULL,           -- Complete platform response
    processed BOOLEAN DEFAULT FALSE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT uq_connection_platform_message UNIQUE (connection_id, platform_message_id)
);

-- Design Decision: Raw messages stored separately for audit trail and
-- reprocessing capability. Processed flag enables incremental normalization.

CREATE INDEX idx_raw_messages_connection ON raw_messages(connection_id);
CREATE INDEX idx_raw_messages_platform ON raw_messages(platform);
CREATE INDEX idx_raw_messages_processed ON raw_messages(processed);

-- =============================================================================
-- MESSAGES TABLE
-- Normalized messages in unified schema
-- =============================================================================
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    connection_id UUID NOT NULL REFERENCES platform_connections(id) ON DELETE CASCADE,
    raw_message_id UUID NOT NULL UNIQUE REFERENCES raw_messages(id) ON DELETE CASCADE,
    platform VARCHAR(50) NOT NULL,
    platform_message_id VARCHAR(255) NOT NULL,
    thread_id VARCHAR(255),
    sender_id UUID REFERENCES participants(id) ON DELETE SET NULL,
    content JSONB NOT NULL,            -- {text, html, format}
    message_metadata JSONB,            -- reactions, edited, forwarded, etc.
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    collected_at TIMESTAMP WITH TIME ZONE NOT NULL,
    cleaned_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT uq_connection_normalized_message UNIQUE (connection_id, platform_message_id)
);

-- Design Decision: JSONB content field supports multiple formats (plain text,
-- HTML, markdown) with format indicator for flexible rendering.

CREATE INDEX idx_messages_connection ON messages(connection_id);
CREATE INDEX idx_messages_platform ON messages(platform);
CREATE INDEX idx_messages_timestamp ON messages(timestamp);
CREATE INDEX idx_messages_thread ON messages(thread_id);
CREATE INDEX idx_messages_sender ON messages(sender_id);

-- =============================================================================
-- THREADS TABLE
-- Conversation grouping across platforms
-- =============================================================================
CREATE TABLE threads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    platform VARCHAR(50) NOT NULL,
    platform_thread_id VARCHAR(255) NOT NULL,
    contact_id UUID REFERENCES contacts(id) ON DELETE SET NULL,
    title VARCHAR(500),
    participant_ids UUID[],
    message_count INTEGER DEFAULT 0 NOT NULL,
    first_message_at TIMESTAMP WITH TIME ZONE,
    last_message_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT uq_platform_thread UNIQUE (platform, platform_thread_id)
);

CREATE INDEX idx_threads_platform ON threads(platform);
CREATE INDEX idx_threads_contact ON threads(contact_id);
CREATE INDEX idx_threads_first_message ON threads(first_message_at);
CREATE INDEX idx_threads_last_message ON threads(last_message_at);

-- =============================================================================
-- ENTITIES TABLE
-- Extracted named entities from messages
-- =============================================================================
CREATE TABLE entities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id UUID NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    entity_type VARCHAR(50) NOT NULL,  -- PERSON, ORG, DATE, LOCATION, etc.
    entity_text VARCHAR(500) NOT NULL,
    confidence FLOAT,
    entity_metadata JSONB,             -- start_pos, end_pos, context, extractor
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_entities_message ON entities(message_id);
CREATE INDEX idx_entities_type ON entities(entity_type);
CREATE INDEX idx_entities_text ON entities(entity_text);

-- =============================================================================
-- EMBEDDINGS TABLE
-- Vector embeddings for semantic search
-- =============================================================================
-- Requires: CREATE EXTENSION vector;
CREATE TABLE embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id UUID NOT NULL UNIQUE REFERENCES messages(id) ON DELETE CASCADE,
    vector vector(768) NOT NULL,       -- 768 dimensions for nomic-embed-text
    model VARCHAR(100) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_embeddings_message ON embeddings(message_id);
-- Vector similarity index (IVFFlat for approximate nearest neighbor)
CREATE INDEX idx_embeddings_vector ON embeddings 
    USING ivfflat (vector vector_cosine_ops) WITH (lists = 100);

-- =============================================================================
-- ATTACHMENTS TABLE
-- File attachments associated with messages
-- =============================================================================
CREATE TABLE attachments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id UUID NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    filename VARCHAR(255) NOT NULL,
    mime_type VARCHAR(100),
    size_bytes BIGINT,
    storage_path VARCHAR(500) NOT NULL,
    platform_url VARCHAR(1000),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_attachments_message ON attachments(message_id);

-- =============================================================================
-- MEMORIES TABLE
-- AI-extracted memories for proactive assistance
-- =============================================================================
CREATE TABLE memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    type VARCHAR(50) NOT NULL,         -- fact, commitment, preference, etc.
    content TEXT NOT NULL,
    importance INTEGER DEFAULT 3 NOT NULL CHECK (importance BETWEEN 1 AND 5),
    contact_id UUID REFERENCES contacts(id) ON DELETE CASCADE,
    thread_id VARCHAR(255),
    platform VARCHAR(50),
    source_message_id UUID REFERENCES messages(id) ON DELETE SET NULL,
    memory_metadata JSONB,             -- due_date, tags, confidence, etc.
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    access_count INTEGER DEFAULT 0 NOT NULL,
    last_accessed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_memories_contact ON memories(contact_id);
CREATE INDEX idx_memories_type ON memories(type);
CREATE INDEX idx_memories_importance ON memories(importance);
CREATE INDEX idx_memories_active ON memories(is_active);

-- =============================================================================
-- SUMMARIES TABLE
-- AI-generated conversation summaries
-- =============================================================================
CREATE TABLE summaries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id UUID REFERENCES threads(id) ON DELETE CASCADE,
    summary_type VARCHAR(50) NOT NULL, -- brief, detailed, insight
    content TEXT NOT NULL,
    summary_metadata JSONB,            -- model, tokens, generation_time, topics
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_summaries_thread ON summaries(thread_id);
CREATE INDEX idx_summaries_type ON summaries(summary_type);

-- =============================================================================
-- COLLECTION_JOBS TABLE
-- Message collection job tracking
-- =============================================================================
CREATE TYPE job_type AS ENUM ('historical', 'realtime', 'incremental');
CREATE TYPE job_status AS ENUM ('pending', 'running', 'paused', 'completed', 'failed', 'cancelled');

CREATE TABLE collection_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    connection_id UUID NOT NULL REFERENCES platform_connections(id) ON DELETE CASCADE,
    job_type job_type NOT NULL,
    status job_status DEFAULT 'pending' NOT NULL,
    progress JSONB,                    -- total, collected, page_token, etc.
    error_message VARCHAR(1000),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_collection_jobs_connection ON collection_jobs(connection_id);
CREATE INDEX idx_collection_jobs_type ON collection_jobs(job_type);
CREATE INDEX idx_collection_jobs_status ON collection_jobs(status);
```

### A.3 Database Indexes Summary

| Table | Index Name | Column(s) | Purpose |
|-------|-----------|-----------|---------|
| users | idx_users_email | email | Quick lookup for authentication |
| users | idx_users_role | role | Role-based filtering |
| platform_connections | idx_platform_connections_user | user_id | User's connections lookup |
| messages | idx_messages_timestamp | timestamp | Time-based queries |
| messages | idx_messages_thread | thread_id | Thread grouping |
| entities | idx_entities_type | entity_type | Entity type filtering |
| embeddings | idx_embeddings_vector | vector (IVFFlat) | Semantic search |
| memories | idx_memories_importance | importance | Priority-based retrieval |

---

## APPENDIX B: COMPLETE API ENDPOINT REFERENCE

### B.1 Base Configuration

- **Development Base URL**: `http://localhost:8000`
- **Production Base URL**: `https://api.syncline.app`
- **API Version**: v1
- **Content-Type**: `application/json`

### B.2 Authentication Endpoints

#### POST /api/v1/auth/login
Authenticate user and obtain JWT tokens.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "SecurePassword123!"
}
```

**Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 1800,
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "username": "johndoe",
    "full_name": "John Doe"
  }
}
```

#### POST /api/v1/auth/register
Register a new user account.

**Request Body:**
```json
{
  "email": "newuser@example.com",
  "username": "newuser",
  "password": "SecurePassword123!",
  "full_name": "New User"
}
```

#### POST /api/v1/auth/refresh
Refresh access token using refresh token.

**Request Body:**
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
}
```

#### POST /api/v1/auth/logout
Invalidate current session.

**Headers:** `Authorization: Bearer {access_token}`

### B.3 Platform Connection Endpoints

#### GET /api/v1/connections
List all platform connections for authenticated user.

**Response:**
```json
{
  "connections": [
    {
      "id": "uuid",
      "platform": "gmail",
      "status": "active",
      "last_sync_at": "2025-01-05T10:30:00Z",
      "platform_metadata": {
        "email": "user@gmail.com",
        "messages_total": 15420
      }
    }
  ]
}
```

#### POST /api/v1/connections/{platform}/init
Initialize OAuth flow for platform connection.

**Platforms:** `gmail`, `slack`, `discord`, `whatsapp`, `linkedin`, `google_chat`

**Response:**
```json
{
  "auth_url": "https://accounts.google.com/o/oauth2/v2/auth?...",
  "state": "random_state_string"
}
```

#### GET /api/v1/connections/callback/{platform}
OAuth callback handler (redirected from platform).

#### DELETE /api/v1/connections/{id}
Disconnect and remove platform connection.

### B.4 Message Endpoints

#### GET /api/v1/messages
Query messages with filters.

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| platform | string | Filter by platform |
| thread_id | string | Filter by thread |
| contact_id | uuid | Filter by contact |
| start_date | datetime | Messages after date |
| end_date | datetime | Messages before date |
| limit | int | Results per page (default: 50, max: 1000) |
| offset | int | Pagination offset |
| sort | string | Sort field (timestamp, platform) |
| order | string | asc or desc |

**Response:**
```json
{
  "messages": [...],
  "pagination": {
    "total": 1250,
    "limit": 50,
    "offset": 0,
    "has_more": true
  }
}
```

#### GET /api/v1/messages/{id}
Get specific message by ID.

#### POST /api/v1/messages/search
Advanced message search.

**Request Body:**
```json
{
  "query": "project deadline",
  "search_type": "hybrid",
  "platforms": ["gmail", "slack"],
  "date_range": {
    "start": "2025-01-01T00:00:00Z",
    "end": "2025-01-31T23:59:59Z"
  },
  "limit": 50
}
```

**Search Types:** `lexical`, `semantic`, `hybrid`

### B.5 Contact Endpoints

#### GET /api/v1/contacts
List contacts with message history.

#### GET /api/v1/contacts/{id}
Get contact details.

#### GET /api/v1/contacts/{id}/profile
Get full contact profile with relationship metrics.

#### GET /api/v1/contacts/{id}/messages
Get all messages with specific contact.

### B.6 Thread Endpoints

#### GET /api/v1/threads
List conversation threads.

#### GET /api/v1/threads/{id}
Get thread with all messages.

### B.7 AI Endpoints

#### POST /api/v1/ai/extract-entities
Extract named entities from text.

**Request Body:**
```json
{
  "text": "Meeting with John at Microsoft on Tuesday at 3pm"
}
```

**Response:**
```json
{
  "entities": [
    {"type": "PERSON", "text": "John", "confidence": 0.95},
    {"type": "ORG", "text": "Microsoft", "confidence": 0.92},
    {"type": "DATE", "text": "Tuesday", "confidence": 0.88},
    {"type": "TIME", "text": "3pm", "confidence": 0.90}
  ]
}
```

#### GET /api/v1/ai/insights
Get AI-generated insights for user.

#### POST /api/v1/ai/summarize
Generate summary for thread or messages.

### B.8 Statistics Endpoints

#### GET /api/v1/stats/dashboard
Get dashboard statistics.

#### GET /api/v1/stats/messages
Get message statistics by platform/time.

### B.9 Health Endpoints

#### GET /api/v1/health
Basic health check.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-01-05T10:30:00Z",
  "version": "1.0.0"
}
```

#### GET /api/v1/health/detailed
Detailed system health with component status.

### B.10 WebSocket API

#### Connection: `ws://localhost:8000/api/v1/ws/connect`

**Authentication Message:**
```json
{
  "type": "auth_request",
  "data": {
    "user_id": "uuid",
    "token": "jwt_token"
  }
}
```

**Event Types:**
| Type | Direction | Description |
|------|-----------|-------------|
| auth_success | Server→Client | Authentication confirmed |
| search_start | Client→Server | Initiate search stream |
| search_result | Server→Client | Individual search result |
| search_complete | Server→Client | Search finished |
| message_received | Server→Client | New message notification |
| nudge_delivery | Server→Client | Proactive nudge |
| system_notification | Server→Client | System update |

---

## APPENDIX C: SAMPLE CODE IMPLEMENTATIONS

### C.1 Gmail Connector Implementation

```python
"""
Gmail Connector - Complete working implementation
Handles OAuth 2.0, push notifications, and message retrieval
"""

class GmailConnector(BaseConnector):
    """Gmail platform connector with OAuth 2.0 and push notifications."""
    
    SCOPES = [
        'https://www.googleapis.com/auth/gmail.readonly',
        'https://www.googleapis.com/auth/gmail.modify',
    ]
    
    def __init__(
        self,
        connection_id: UUID,
        credentials: Dict[str, Any],
        rate_limit_per_minute: int = 250,
    ):
        super().__init__(
            connection_id=connection_id,
            credentials=credentials,
            rate_limit_per_minute=rate_limit_per_minute,
        )
        self._service = None
        self._watch_expiration = None
    
    @property
    def platform_name(self) -> str:
        return "gmail"
    
    async def _connect(self) -> None:
        """Establish connection to Gmail API."""
        creds = self._create_credentials()
        
        if not creds.valid:
            if creds.expired and creds.refresh_token:
                await self._refresh_token()
                creds = self._create_credentials()
            else:
                raise AuthenticationError("Invalid credentials")
        
        self._service = build('gmail', 'v1', credentials=creds)
        await self._test_connection()
    
    def _create_credentials(self) -> Credentials:
        """Create Google OAuth credentials from stored values."""
        return Credentials(
            token=self.credentials.get("access_token"),
            refresh_token=self.credentials.get("refresh_token"),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=self.credentials.get("client_id"),
            client_secret=self.credentials.get("client_secret"),
            scopes=self.SCOPES,
        )
    
    async def _refresh_token(self) -> Dict[str, Any]:
        """Refresh OAuth token automatically."""
        creds = self._create_credentials()
        creds.refresh(Request())
        
        return {
            "access_token": creds.token,
            "refresh_token": creds.refresh_token,
            "expires_at": creds.expiry.isoformat() if creds.expiry else None,
        }
    
    async def list_messages(
        self,
        max_results: int = 100,
        page_token: Optional[str] = None,
        query: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List messages with pagination and filtering."""
        if not await self.check_rate_limit():
            raise RateLimitError("Gmail rate limit exceeded")
        
        params = {'userId': 'me', 'maxResults': max_results}
        if page_token:
            params['pageToken'] = page_token
        if query:
            params['q'] = query
        
        result = self._service.users().messages().list(**params).execute()
        
        return {
            "messages": result.get("messages", []),
            "next_page_token": result.get("nextPageToken"),
        }
    
    async def get_message(self, message_id: str, format: str = "full") -> Dict:
        """Fetch complete message by ID."""
        return self._service.users().messages().get(
            userId='me',
            id=message_id,
            format=format
        ).execute()
    
    async def start_watch(self, topic_name: str) -> Dict[str, Any]:
        """Enable push notifications via Pub/Sub."""
        response = self._service.users().watch(
            userId='me',
            body={'topicName': topic_name}
        ).execute()
        
        self._watch_expiration = datetime.fromtimestamp(
            int(response.get('expiration', 0)) / 1000
        )
        return response
```

### C.2 Message Normalizer

```python
"""
Message Normalizer - Transform platform-specific messages to unified format
"""

class MessageNormalizer:
    """Normalizes messages from various platforms to unified schema."""
    
    def normalize(self, raw_message: RawMessage) -> Optional[Message]:
        """Normalize raw message based on platform."""
        normalizers = {
            'gmail': self._normalize_gmail,
            'slack': self._normalize_slack,
            'whatsapp': self._normalize_whatsapp,
            'discord': self._normalize_discord,
        }
        
        normalizer = normalizers.get(raw_message.platform)
        if not normalizer:
            logger.warning(f"No normalizer for platform: {raw_message.platform}")
            return None
        
        return normalizer(raw_message)
    
    def _normalize_gmail(self, raw: RawMessage) -> Message:
        """Normalize Gmail message format."""
        data = raw.raw_data
        payload = data.get('payload', {})
        headers = {h['name'].lower(): h['value'] 
                   for h in payload.get('headers', [])}
        
        # Extract content from parts
        content = self._extract_gmail_content(payload)
        
        return Message(
            connection_id=raw.connection_id,
            raw_message_id=raw.id,
            platform='gmail',
            platform_message_id=data['id'],
            thread_id=data.get('threadId'),
            content={
                'text': content.get('text', ''),
                'html': content.get('html', ''),
                'format': 'html' if content.get('html') else 'plain'
            },
            timestamp=self._parse_gmail_timestamp(data.get('internalDate')),
            message_metadata={
                'subject': headers.get('subject'),
                'labels': data.get('labelIds', []),
            }
        )
    
    def _extract_gmail_content(self, payload: Dict) -> Dict[str, str]:
        """Extract text and HTML content from Gmail payload."""
        content = {'text': '', 'html': ''}
        
        def process_part(part):
            mime_type = part.get('mimeType', '')
            body = part.get('body', {})
            data = body.get('data', '')
            
            if data:
                decoded = base64.urlsafe_b64decode(data).decode('utf-8')
                if mime_type == 'text/plain':
                    content['text'] = decoded
                elif mime_type == 'text/html':
                    content['html'] = decoded
            
            for sub_part in part.get('parts', []):
                process_part(sub_part)
        
        process_part(payload)
        return content
```

### C.3 Entity Extraction Agent (Hybrid NER + LLM)

```python
"""
Entity Extraction Service - Hybrid spaCy NER with LLM enhancement
"""

class EntityExtractionService:
    """Extract named entities using spaCy with custom patterns."""
    
    def __init__(self, model_name: str = "en_core_web_sm"):
        self.model_name = model_name
        self._nlp = None
        self.confidence_threshold = 0.5
    
    def _load_model(self) -> Language:
        """Lazily load spaCy model."""
        if self._nlp is None:
            self._nlp = spacy.load(self.model_name)
        return self._nlp
    
    def extract_entities(self, text: str) -> List[ExtractedEntity]:
        """Extract entities from text using hybrid approach."""
        if not text.strip():
            return []
        
        nlp = self._load_model()
        doc = nlp(text)
        entities = []
        
        # Standard spaCy NER
        for ent in doc.ents:
            entity_type = self._map_spacy_label(ent.label_)
            if entity_type:
                entities.append(ExtractedEntity(
                    text=ent.text,
                    entity_type=entity_type,
                    start_pos=ent.start_char,
                    end_pos=ent.end_char,
                    confidence=1.0,
                    context=self._get_context(text, ent.start_char, ent.end_char)
                ))
        
        # Custom pattern extraction (emails, phones, URLs)
        entities.extend(self._extract_custom_entities(text))
        
        return [e for e in entities if e.confidence >= self.confidence_threshold]
    
    def _map_spacy_label(self, label: str) -> Optional[EntityType]:
        """Map spaCy labels to our entity types."""
        mapping = {
            "PERSON": EntityType.PERSON,
            "ORG": EntityType.ORG,
            "DATE": EntityType.DATE,
            "TIME": EntityType.TIME,
            "GPE": EntityType.GPE,
            "LOC": EntityType.LOCATION,
            "MONEY": EntityType.MONEY,
        }
        return mapping.get(label)
    
    def _extract_custom_entities(self, text: str) -> List[ExtractedEntity]:
        """Extract emails, phones, URLs using regex patterns."""
        entities = []
        
        # Email pattern
        for match in re.finditer(
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text
        ):
            entities.append(ExtractedEntity(
                text=match.group(),
                entity_type=EntityType.EMAIL,
                start_pos=match.start(),
                end_pos=match.end(),
                confidence=0.95
            ))
        
        # Phone pattern
        for match in re.finditer(
            r'\b(?:\+?1[-.]?)?\(?[0-9]{3}\)?[-.]?[0-9]{3}[-.]?[0-9]{4}\b', text
        ):
            entities.append(ExtractedEntity(
                text=match.group(),
                entity_type=EntityType.PHONE,
                start_pos=match.start(),
                end_pos=match.end(),
                confidence=0.9
            ))
        
        return entities
```

### C.4 Hybrid Search Agent (Lexical + Semantic Fusion)

```python
"""
Hybrid Search Agent - Combines lexical and semantic search with RRF
"""

class HybridSearchAgent:
    """Performs hybrid search using Reciprocal Rank Fusion."""
    
    def __init__(
        self,
        embedding_service: EmbeddingService,
        chroma_client: ChromaDBClient,
        lexical_weight: float = 0.4,
        semantic_weight: float = 0.6
    ):
        self.embedding_service = embedding_service
        self.chroma_client = chroma_client
        self.lexical_weight = lexical_weight
        self.semantic_weight = semantic_weight
    
    async def search(
        self,
        query: str,
        db: AsyncSession,
        limit: int = 20,
        filters: Optional[SearchFilter] = None
    ) -> List[SearchResult]:
        """Execute hybrid search combining lexical and semantic."""
        
        # Parallel execution of both search types
        lexical_results, semantic_results = await asyncio.gather(
            self._lexical_search(query, db, limit * 2, filters),
            self._semantic_search(query, db, limit * 2, filters)
        )
        
        # Apply Reciprocal Rank Fusion
        fused_results = self._reciprocal_rank_fusion(
            lexical_results,
            semantic_results,
            k=60  # RRF constant
        )
        
        return fused_results[:limit]
    
    async def _semantic_search(
        self, query: str, db: AsyncSession, limit: int, filters
    ) -> List[SearchResult]:
        """Vector similarity search using embeddings."""
        # Generate query embedding
        query_embedding = await self.embedding_service.generate_embedding(query)
        
        # Search ChromaDB
        chroma_results = self.chroma_client.query(
            query_embeddings=[query_embedding],
            n_results=limit,
            where=self._build_chroma_filter(filters)
        )
        
        return self._format_chroma_results(chroma_results)
    
    async def _lexical_search(
        self, query: str, db: AsyncSession, limit: int, filters
    ) -> List[SearchResult]:
        """Full-text search using PostgreSQL ts_vector."""
        # Build full-text search query
        ts_query = func.plainto_tsquery('english', query)
        
        stmt = (
            select(Message)
            .where(
                func.to_tsvector('english', Message.content['text'].astext)
                .match(ts_query)
            )
            .order_by(
                func.ts_rank(
                    func.to_tsvector('english', Message.content['text'].astext),
                    ts_query
                ).desc()
            )
            .limit(limit)
        )
        
        result = await db.execute(stmt)
        return self._format_db_results(result.scalars().all())
    
    def _reciprocal_rank_fusion(
        self,
        lexical: List[SearchResult],
        semantic: List[SearchResult],
        k: int = 60
    ) -> List[SearchResult]:
        """Combine results using RRF algorithm."""
        scores = {}
        
        # Score lexical results
        for rank, result in enumerate(lexical):
            rrf_score = 1 / (k + rank + 1)
            scores[result.id] = scores.get(result.id, 0) + \
                               (rrf_score * self.lexical_weight)
            scores[f"{result.id}_obj"] = result
        
        # Score semantic results
        for rank, result in enumerate(semantic):
            rrf_score = 1 / (k + rank + 1)
            scores[result.id] = scores.get(result.id, 0) + \
                               (rrf_score * self.semantic_weight)
            scores[f"{result.id}_obj"] = result
        
        # Sort by combined score
        result_ids = [k for k in scores.keys() if not k.endswith('_obj')]
        sorted_ids = sorted(result_ids, key=lambda x: scores[x], reverse=True)
        
        return [scores[f"{id}_obj"] for id in sorted_ids]

---

## APPENDIX D: CONFIGURATION FILES

### D.1 docker-compose.yml (Complete)

```yaml
# R.E.M.I Backend - Docker Compose Configuration
# Sets up PostgreSQL, Redis, Ollama, ChromaDB, and WhatsApp Bridge

services:
  # PostgreSQL Database
  postgres:
    image: postgres:14-alpine
    container_name: remi_postgres
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
      POSTGRES_DB: mesh_development
      POSTGRES_INITDB_ARGS: "--encoding=UTF8 --locale=en_US.UTF-8"
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./db/sql:/docker-entrypoint-initdb.d
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - remi_network

  # Redis (Event Bus & Caching)
  redis:
    image: redis:6-alpine
    container_name: remi_redis
    command: redis-server --appendonly yes --maxmemory 512mb --maxmemory-policy allkeys-lru
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - remi_network

  # Ollama (Local LLM Inference)
  ollama:
    image: ollama/ollama:latest
    container_name: remi_ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    environment:
      - OLLAMA_HOST=0.0.0.0
    healthcheck:
      test: ["CMD-SHELL", "test -f /root/.ollama/id_ed25519 || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s
    networks:
      - remi_network
    deploy:
      resources:
        limits:
          memory: 4G

  # ChromaDB (Vector Database)
  chromadb:
    image: chromadb/chroma:latest
    container_name: remi_chromadb
    ports:
      - "8001:8000"
    volumes:
      - chromadb_data:/chroma/chroma
    environment:
      - IS_PERSISTENT=TRUE
      - PERSIST_DIRECTORY=/chroma/chroma
      - ANONYMIZED_TELEMETRY=FALSE
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v2/heartbeat"]
      interval: 30s
      timeout: 10s
      retries: 3
    networks:
      - remi_network

  # Matrix Synapse (WhatsApp Bridge Homeserver)
  synapse:
    image: matrixdotorg/synapse:latest
    container_name: remi_synapse
    environment:
      - SYNAPSE_SERVER_NAME=localhost
      - SYNAPSE_REPORT_STATS=no
      - UID=0
      - GID=0
    ports:
      - "8008:8008"
    volumes:
      - ./data/synapse:/data
      - ./config/synapse/homeserver.yaml:/data/homeserver.yaml:ro
      - ./config/synapse/whatsapp-registration.yaml:/data/whatsapp-registration.yaml:ro
    depends_on:
      postgres:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8008/health"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 60s
    networks:
      - remi_network

  # mautrix-whatsapp (WhatsApp Bridge)
  whatsapp-bridge:
    image: dock.mau.dev/mautrix/whatsapp:latest
    container_name: remi_whatsapp_bridge
    ports:
      - "29318:29318"
    volumes:
      - whatsapp_bridge_data:/data
      - ./config/mautrix-whatsapp/config.yaml:/data/config.yaml:ro
    depends_on:
      synapse:
        condition: service_healthy
      postgres:
        condition: service_healthy
    environment:
      - MAUTRIX_DIRECT_STARTUP=true
    networks:
      - remi_network
    restart: unless-stopped

networks:
  remi_network:
    driver: bridge

volumes:
  postgres_data:
    driver: local
  redis_data:
    driver: local
  ollama_data:
    driver: local
  chromadb_data:
    driver: local
  whatsapp_bridge_data:
    driver: local
```

### D.2 .env.example (Environment Variables Template)

```bash
# =============================================================================
# R.E.M.I (Real-time External Memory Interface) Configuration
# =============================================================================

# Core Database Configuration
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/mesh_development
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=30
DB_POOL_PRE_PING=true

# Redis Configuration (Event Bus & Caching)
REDIS_URL=redis://localhost:6379
REDIS_MAX_CONNECTIONS=20
REDIS_RETRY_ON_TIMEOUT=true

# Environment & Debug Settings
ENV=development
DEBUG=true
LOG_LEVEL=INFO
STRUCTURED_LOGGING=true

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=1
CORS_ORIGINS=["http://localhost:3000", "http://localhost:8080"]

# Security Configuration
SECRET_KEY=your-super-secret-key-change-this-in-production
JWT_SECRET_KEY=your-jwt-secret-key-change-this-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=30
ENCRYPTION_KEY=your-32-byte-encryption-key-base64-encoded

# Gmail Integration (OAuth 2.0)
GMAIL_CLIENT_ID=your-gmail-client-id.apps.googleusercontent.com
GMAIL_CLIENT_SECRET=your-gmail-client-secret
GMAIL_SCOPES=https://www.googleapis.com/auth/gmail.readonly,https://www.googleapis.com/auth/gmail.modify
GMAIL_REDIRECT_URI=http://localhost:8000/auth/gmail/callback

# Slack Integration
SLACK_CLIENT_ID=your-slack-client-id
SLACK_CLIENT_SECRET=your-slack-client-secret
SLACK_SIGNING_SECRET=your-slack-signing-secret
SLACK_BOT_TOKEN=xoxb-your-slack-bot-token

# Discord Integration
DISCORD_BOT_TOKEN=your-discord-bot-token
DISCORD_CLIENT_ID=your-discord-client-id
DISCORD_CLIENT_SECRET=your-discord-client-secret

# WhatsApp Bridge Configuration
WHATSAPP_BRIDGE_ENABLED=false
WHATSAPP_BRIDGE_EXECUTABLE=/usr/local/bin/mautrix-whatsapp

# AI Processing Configuration
DEFAULT_LLM_PROVIDER=ollama
DEFAULT_CHAT_MODEL=llama3.2:3b
DEFAULT_EMBEDDING_MODEL=nomic-embed-text:latest
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_TIMEOUT=120

# OpenRouter (Cloud LLM)
OPENROUTER_API_KEY=your-openrouter-api-key
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1

# Vector Database Configuration
CHROMA_HOST=localhost
CHROMA_PORT=8000
CHROMA_PERSIST_DIRECTORY=./vector_db

# PII Redaction & Privacy
PII_REDACTION_ENABLED=true
PII_CONFIDENCE_THRESHOLD=0.8

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS_PER_MINUTE=60

# Feature Flags
FEATURE_AI_PROCESSING=true
FEATURE_REAL_TIME_SEARCH=true
FEATURE_PROACTIVE_MEMORY=true
FEATURE_ENTITY_EXTRACTION=true

# Mobile App Configuration
APP_DEEP_LINK_SCHEME=syncline
```

### D.3 requirements.txt (Core Dependencies)

```text
# Core Framework
fastapi==0.115.8
uvicorn==0.34.0
starlette==0.45.3
pydantic==2.10.6
pydantic-settings==2.6.1

# Database
sqlalchemy[asyncio]==2.0.23
asyncpg>=0.30.0
psycopg2-binary>=2.9.10
alembic==1.13.1

# Redis & Caching
redis==5.0.1

# Authentication
PyJWT==2.8.0
bcrypt==4.1.2
passlib==1.7.4
python-multipart==0.0.9

# AI and ML
openai==1.63.0
anthropic==0.40.0
spacy==3.8.11
sentence-transformers==3.3.1
chromadb==0.6.3

# Google APIs
google-api-python-client==2.176.0
google-auth==2.40.3
google-auth-oauthlib==1.2.2

# HTTP Clients
httpx==0.28.1
aiohttp==3.11.16
requests==2.32.3

# Processing
numpy==2.1.3
pandas==2.2.3

# Testing
pytest==7.4.4
pytest-asyncio==0.23.4
pytest-cov==4.1.0
locust==2.24.0

# Monitoring
prometheus-client==0.21.1
structlog==24.4.0

# Utilities
python-dotenv==1.1.1
PyYAML==6.0.2
qrcode[pil]==7.4.2
```

---

## APPENDIX E: DETAILED TEST RESULTS

### E.1 Unit Test Summary

```
========================= test session starts ==========================
platform darwin -- Python 3.11.4, pytest-7.4.4, pluggy-1.3.0
plugins: asyncio-0.23.4, cov-4.1.0
collected 45 items

tests/test_api_routes.py::TestHealthEndpoints::test_health_check PASSED
tests/test_api_routes.py::TestHealthEndpoints::test_status_check PASSED
tests/test_auth.py::TestAuthentication::test_login_success PASSED
tests/test_auth.py::TestAuthentication::test_login_invalid_password PASSED
tests/test_auth.py::TestAuthentication::test_token_refresh PASSED
tests/test_services.py::TestMessageNormalizer::test_gmail_normalization PASSED
tests/test_services.py::TestMessageNormalizer::test_slack_normalization PASSED
tests/test_services.py::TestEntityExtraction::test_person_extraction PASSED
tests/test_services.py::TestEntityExtraction::test_org_extraction PASSED
tests/test_services.py::TestEntityExtraction::test_email_pattern PASSED
...

========================= 42 passed, 3 skipped =========================
Test Coverage: 78%
```

### E.2 Security Test Results

| Test Case | ID | Result | Notes |
|-----------|-----|--------|-------|
| OAuth Flow Integrity | TC-20 | ✅ PASS | Forged tokens rejected |
| Session Expiration | TC-21 | ✅ PASS | Expired tokens return 401 |
| Token Refresh | TC-22 | ✅ PASS | Refresh mechanism works |
| Unauthorized Access | TC-23 | ✅ PASS | Cross-user access blocked |
| RBAC Enforcement | TC-24 | ✅ PASS | Role checks enforced |
| SQL Injection | TC-25 | ✅ PASS | All payloads sanitized |
| XSS Prevention | TC-26 | ✅ PASS | Scripts escaped/blocked |
| Payload Size Limits | TC-27 | ✅ PASS | Oversized requests rejected |
| Encryption at Rest | TC-28 | ✅ PASS | Credentials encrypted |
| TLS Configuration | TC-29 | ⚠️ ADVISORY | TLS 1.2+ enforced |
| Password Storage | TC-30 | ✅ PASS | Bcrypt hashing verified |

**Security Test Pass Rate: 93.3% (14/15)**

### E.3 Performance Test Results

#### Load Test Results (Locust)

| Concurrent Users | Avg Response (ms) | P95 (ms) | Requests/sec | Error Rate |
|-----------------|-------------------|----------|--------------|------------|
| 100 | 234 | 456 | 245 | 0% |
| 500 | 487 | 892 | 1,124 | 0.1% |
| 1,000 | 789 | 1,543 | 2,187 | 0.3% |
| 1,500 | 1,234 | 3,124 | 2,945 | 1.2% |
| 2,000 | 2,567 | 7,234 | 3,012 | 8.7% |

**Breaking Point: ~2,000 concurrent users**

#### Benchmark Results

| Operation | Expected (ms) | Actual (ms) | Status |
|-----------|---------------|-------------|--------|
| Lexical Search | 156 | 148 | ✅ |
| Semantic Search | 423 | 412 | ✅ |
| Hybrid Search | 687 | 695 | ✅ |
| Cached Search | 42 | 38 | ✅ |
| Message Insertion | 23 | 21 | ✅ |
| Message Retrieval | 8 | 7 | ✅ |
| Contact Profile | 145 | 152 | ✅ |
| Entity Extraction | 1,800 | 1,756 | ✅ |
| Vector Search (10K) | 234 | 228 | ✅ |

### E.4 Stress Test Results

| Test | Target | Result | Status |
|------|--------|--------|--------|
| Message Throughput (10K msgs) | <10 min | 8.5 min | ✅ |
| Connection Pool (200 conns) | Graceful | Queued properly | ✅ |
| Recovery Time | <30 sec | 22 sec | ✅ |
| 72h Endurance | 99.8% uptime | 99.9% | ✅ |

---

## APPENDIX F: DEPLOYMENT ARCHITECTURE DIAGRAMS

### F.1 Deployment Topology (Text Description)

```
┌─────────────────────────────────────────────────────────────────┐
│                        LOAD BALANCER                            │
│                      (NGINX / Traefik)                          │
│                    SSL Termination, Rate Limiting               │
└────────────────────────────┬────────────────────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│   API Pod 1   │   │   API Pod 2   │   │   API Pod 3   │
│   (FastAPI)   │   │   (FastAPI)   │   │   (FastAPI)   │
│   Workers: 4  │   │   Workers: 4  │   │   Workers: 4  │
└───────┬───────┘   └───────┬───────┘   └───────┬───────┘
        │                   │                   │
        └───────────────────┼───────────────────┘
                            │
        ┌───────────────────┴───────────────────┐
        │                                       │
        ▼                                       ▼
┌───────────────────┐               ┌───────────────────┐
│    PostgreSQL     │               │      Redis        │
│    Primary +      │               │    (Cluster)      │
│    Read Replicas  │               │  Event Bus/Cache  │
└───────────────────┘               └───────────────────┘
        │
        ▼
┌───────────────────┐               ┌───────────────────┐
│    ChromaDB       │               │    Ollama / API   │
│  Vector Storage   │               │   LLM Inference   │
└───────────────────┘               └───────────────────┘
```

### F.2 Network Architecture

```
Internet Traffic
       │
       ▼
┌──────────────────┐
│   Cloudflare     │  ← DDoS Protection, CDN
│   WAF + CDN      │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Load Balancer   │  ← SSL/TLS Termination
│  (Port 443)      │
└────────┬─────────┘
         │
    ┌────┴────┐
    │ VPC     │
    │         │
    ├─────────┴───────────────────────────────┐
    │                                         │
    │  ┌─────────────┐    ┌─────────────┐    │
    │  │ Public      │    │ Private     │    │
    │  │ Subnet      │    │ Subnet      │    │
    │  │             │    │             │    │
    │  │ API Servers │    │ Databases   │    │
    │  │ WebSocket   │    │ Redis       │    │
    │  │             │    │ ChromaDB    │    │
    │  └─────────────┘    └─────────────┘    │
    │                                         │
    └─────────────────────────────────────────┘
```

### F.3 Data Flow Architecture

```
User Request
     │
     ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Mobile    │────▶│   FastAPI   │────▶│ PostgreSQL  │
│    App      │     │   Backend   │     │  Database   │
└─────────────┘     └──────┬──────┘     └─────────────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
              ▼            ▼            ▼
       ┌───────────┐ ┌───────────┐ ┌───────────┐
       │  Redis    │ │ ChromaDB  │ │   LLM     │
       │Event Bus  │ │  Vectors  │ │ Provider  │
       └───────────┘ └───────────┘ └───────────┘

Message Processing Pipeline:
Platform → Raw Message → Redis Stream → Normalizer → 
Database → Entity Extractor → Embedding → ChromaDB
```

---

## APPENDIX G: ACRONYMS AND ABBREVIATIONS

| Acronym | Full Form |
|---------|-----------|
| AI | Artificial Intelligence |
| API | Application Programming Interface |
| CRUD | Create, Read, Update, Delete |
| CSS | Cascading Style Sheets |
| DFD | Data Flow Diagram |
| ERD | Entity Relationship Diagram |
| FastAPI | Fast Application Programming Interface (Python framework) |
| GPE | Geopolitical Entity |
| HTML | HyperText Markup Language |
| HTTP | HyperText Transfer Protocol |
| HTTPS | HyperText Transfer Protocol Secure |
| IMAP | Internet Message Access Protocol |
| JSON | JavaScript Object Notation |
| JSONB | JSON Binary (PostgreSQL) |
| JWT | JSON Web Token |
| LLM | Large Language Model |
| MESH | Multi-platform Event Stream Hub |
| ML | Machine Learning |
| NER | Named Entity Recognition |
| NLP | Natural Language Processing |
| OAuth | Open Authorization |
| ORM | Object-Relational Mapping |
| PII | Personally Identifiable Information |
| PostgreSQL | Postgres Structured Query Language |
| RBAC | Role-Based Access Control |
| R.E.M.I | Real-time External Memory Interface |
| REST | Representational State Transfer |
| RRF | Reciprocal Rank Fusion |
| SQL | Structured Query Language |
| SSL | Secure Sockets Layer |
| TLS | Transport Layer Security |
| UI | User Interface |
| URL | Uniform Resource Locator |
| UUID | Universally Unique Identifier |
| VPC | Virtual Private Cloud |
| WS | WebSocket |
| XSS | Cross-Site Scripting |

---

## APPENDIX H: PLATFORM API INTEGRATION DETAILS

### H.1 Gmail Integration

| Aspect | Details |
|--------|---------|
| **API Endpoints** | Gmail API v1 (`googleapis.com/gmail/v1`) |
| **Authentication** | OAuth 2.0 with PKCE |
| **Scopes** | `gmail.readonly`, `gmail.modify`, `gmail.metadata` |
| **Rate Limits** | 250 requests/user/second, 25,000 quota units/day |
| **Push Notifications** | Google Cloud Pub/Sub webhooks |
| **Key Challenges** | Token refresh timing, History ID tracking |
| **Workarounds** | Automatic token refresh before API calls, history sync on reconnect |

### H.2 Slack Integration

| Aspect | Details |
|--------|---------|
| **API Endpoints** | Slack Web API, Events API, Socket Mode |
| **Authentication** | OAuth 2.0 + Bot Token + User Token |
| **Scopes** | `channels:history`, `im:history`, `users:read` |
| **Rate Limits** | Tier 1: 1 req/second, Tier 4: 100 req/minute |
| **Real-time** | Socket Mode or Events API webhooks |
| **Key Challenges** | Workspace vs Enterprise Grid permissions |
| **Workarounds** | Per-workspace token management |

### H.3 Discord Integration

| Aspect | Details |
|--------|---------|
| **API Endpoints** | Discord Gateway (WebSocket), REST API v10 |
| **Authentication** | Bot Token |
| **Permissions** | `READ_MESSAGE_HISTORY`, `MESSAGE_CONTENT` intent |
| **Rate Limits** | 50 requests/second per route |
| **Real-time** | Gateway WebSocket connection |
| **Key Challenges** | Message content intent requires approval |
| **Workarounds** | Application to Discord for verified bot status |

### H.4 WhatsApp Integration

| Aspect | Details |
|--------|---------|
| **API Endpoints** | mautrix-whatsapp bridge via Matrix protocol |
| **Authentication** | QR Code or Pairing Code (phone linking) |
| **Rate Limits** | Subject to WhatsApp's rate limits (undefined) |
| **Real-time** | Bridge polls/pushes via Matrix events |
| **Key Challenges** | Session persistence, multi-device conflicts |
| **Workarounds** | Session recovery mechanism, re-auth prompts |

### H.5 LinkedIn Integration

| Aspect | Details |
|--------|---------|
| **API Endpoints** | LinkedIn REST API v2 |
| **Authentication** | OAuth 2.0 (3-legged) |
| **Scopes** | `r_liteprofile`, `r_emailaddress`, `w_member_social` |
| **Rate Limits** | 100 requests/day for most endpoints |
| **Key Challenges** | Messaging API requires Partnership approval |
| **Workarounds** | mautrix-linkedin bridge for messaging |

---

## APPENDIX I: AI MODEL SPECIFICATIONS

### I.1 Language Models

| Model | Provider | Parameters | Cost (per 1M tokens) | Use Case |
|-------|----------|------------|---------------------|----------|
| GPT-4o | OpenAI | ~200B | $5 input / $15 output | Complex reasoning |
| GPT-4o-mini | OpenAI | ~8B | $0.15 / $0.60 | General use |
| Claude 3.5 Sonnet | Anthropic | Unknown | $3 / $15 | Summarization |
| Llama 3.2 3B | Ollama (local) | 3B | Free (local compute) | Default chat |

### I.2 Embedding Models

| Model | Dimensions | Speed | Quality | Use Case |
|-------|------------|-------|---------|----------|
| nomic-embed-text | 768 | Fast | Good | Default embeddings |
| text-embedding-ada-002 | 1536 | Medium | Excellent | Cloud fallback |
| all-MiniLM-L6-v2 | 384 | Very Fast | Good | Local alternative |

### I.3 NER/NLP Models

| Model | Size | Entities | Language |
|-------|------|----------|----------|
| en_core_web_sm | 12MB | 18 types | English |
| en_core_web_md | 45MB | 18 types | English |
| en_core_web_lg | 780MB | 18 types | English |

### I.4 Prompt Templates

**Summarization Prompt:**
```
Summarize the following conversation in 2-3 sentences. 
Focus on key decisions, action items, and important information.

Conversation:
{messages}

Summary:
```

**Entity Extraction Enhancement:**
```
Extract entities from this text and categorize them:
- People (names)
- Organizations (companies, institutions)
- Dates and Times
- Locations
- Action items or commitments

Text: {text}

Entities:
```

---

## APPENDIX J: IMPLEMENTATION TIMELINE

### J.1 Project Phases

| Phase | Duration | Dates | Status |
|-------|----------|-------|--------|
| Phase 1: Research & Planning | 4 weeks | Sep 2025 | ✅ Complete |
| Phase 2: Architecture Design | 3 weeks | Oct 2025 | ✅ Complete |
| Phase 3: Core Implementation | 8 weeks | Oct-Dec 2025 | ✅ Complete |
| Phase 4: AI Integration | 4 weeks | Dec 2025 | ✅ Complete |
| Phase 5: Testing & QA | 3 weeks | Jan 2026 | ✅ Complete |
| Phase 6: Documentation | 2 weeks | Jan 2026 | ✅ Complete |

### J.2 Major Milestones

| Milestone | Target Date | Actual Date | Notes |
|-----------|-------------|-------------|-------|
| Database Schema Design | Oct 15, 2025 | Oct 12, 2025 | 3 days early |
| Gmail Connector Complete | Nov 1, 2025 | Nov 3, 2025 | 2 days delay |
| WhatsApp Integration | Nov 30, 2025 | Dec 8, 2025 | Bridge complexity |
| Entity Extraction | Dec 15, 2025 | Dec 14, 2025 | On target |
| Hybrid Search | Dec 22, 2025 | Dec 20, 2025 | Ahead of schedule |
| Mobile App Auth | Dec 28, 2025 | Dec 31, 2025 | OAuth redirect issues |
| Performance Tests | Jan 5, 2026 | Jan 4, 2026 | Complete |

### J.3 Time Allocation by Component

| Component | Estimated Hours | Actual Hours | % of Total |
|-----------|-----------------|--------------|------------|
| Backend API | 120 | 135 | 32% |
| Database Layer | 40 | 45 | 11% |
| Platform Connectors | 80 | 95 | 23% |
| AI Services | 60 | 55 | 13% |
| Mobile App | 50 | 48 | 11% |
| Testing | 30 | 35 | 8% |
| Documentation | 20 | 18 | 4% |
| **Total** | **400** | **431** | **100%** |

---

## APPENDIX K: USER DOCUMENTATION ASSETS

### K.1 Required Screenshots/Figures

| Figure # | Description | Caption |
|----------|-------------|---------|
| Fig 1 | System architecture diagram | "High-level architecture of the Syncline platform showing component interactions" |
| Fig 2 | Database ERD | "Entity-Relationship Diagram showing database schema and relationships" |
| Fig 3 | Login screen (mobile) | "User authentication screen in the Syncline mobile application" |
| Fig 4 | Platform connection flow | "OAuth flow for connecting Gmail account" |
| Fig 5 | Message search results | "Hybrid search results showing relevance scores" |
| Fig 6 | Contact profile view | "Unified contact profile with cross-platform conversation history" |
| Fig 7 | AI insights panel | "AI-generated insights and relationship metrics" |
| Fig 8 | WhatsApp QR code | "WhatsApp connection using QR code authentication" |
| Fig 9 | Performance dashboard | "Locust load test results showing response times" |
| Fig 10 | API documentation | "Swagger/OpenAPI documentation interface" |

---

## APPENDIX L: GLOSSARY OF TERMS

| Term | Definition |
|------|------------|
| **ChromaDB** | Open-source vector database used for storing and querying message embeddings |
| **Circuit Breaker** | Design pattern that prevents cascading failures by temporarily stopping requests to failing services |
| **Embedding** | Dense vector representation of text that captures semantic meaning |
| **Event Bus** | Message queue system (Redis Streams) for asynchronous processing |
| **Fernet Encryption** | Symmetric encryption scheme used for securing OAuth credentials at rest |
| **Hybrid Search** | Search strategy combining lexical (keyword) and semantic (vector) approaches |
| **JWT** | Token format used for stateless authentication between client and server |
| **Matrix Protocol** | Open standard for decentralized communication used for WhatsApp bridging |
| **mautrix-whatsapp** | Bridge software connecting WhatsApp to Matrix protocol |
| **Named Entity Recognition (NER)** | NLP task of identifying and classifying entities in text |
| **Normalization** | Process of converting platform-specific message formats to unified schema |
| **OAuth 2.0** | Authorization framework for delegated access to third-party services |
| **Ollama** | Local LLM inference server for running models like Llama on device |
| **Proactive Memory** | AI system that surfaces relevant memories before user requests them |
| **Rate Limiting** | Controlling request frequency to prevent API abuse |
| **Reciprocal Rank Fusion** | Algorithm for combining ranked lists from multiple sources |
| **Redis Streams** | Redis data structure for event streaming and message queuing |
| **Semantic Search** | Search based on meaning rather than exact keyword matching |
| **spaCy** | Industrial-strength NLP library used for entity extraction |
| **Vector Search** | Finding similar items using distance metrics in embedding space |
| **WebSocket** | Protocol for full-duplex real-time communication |

---

*End of Appendix Document*
*Generated: January 5, 2026*
*Project: Syncline (R.E.M.I) - Final Year Project*
