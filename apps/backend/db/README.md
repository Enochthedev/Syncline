# Database Layer Documentation

## Overview

The database layer provides the foundation for the R.E.M.I backend rebuild with:
- SQLAlchemy async ORM with PostgreSQL
- UUID primary keys for all models
- Automatic timestamp tracking
- Alembic migrations support
- Comprehensive relationship management

## Structure

```
db/
├── __init__.py              # Package exports
├── base.py                  # Base model with UUID and timestamps
├── session.py               # Async session management
├── alembic/                 # Migration configuration
│   ├── env.py              # Alembic environment
│   ├── script.py.mako      # Migration template
│   └── versions/           # Migration files
└── models/                  # Database models
    ├── __init__.py         # Model exports
    ├── user.py             # User authentication
    ├── platform_connection.py  # OAuth connections
    ├── raw_message.py      # Unprocessed messages
    ├── message.py          # Normalized messages
    ├── contact.py          # Unified contacts
    ├── thread.py           # Conversation threads
    ├── participant.py      # Platform identities
    ├── attachment.py       # File attachments
    ├── entity.py           # Extracted entities
    ├── summary.py          # AI summaries
    └── embedding.py        # Vector embeddings
```

## Models

### Core Models (Task 2.2)

#### User
- System users with authentication
- Email and username (unique)
- Password hashing support
- Active/superuser flags

#### PlatformConnection
- OAuth connections to platforms
- Encrypted credentials (JSONB)
- Connection status tracking
- Last sync timestamp
- Supported platforms: Gmail, Slack, Discord, WhatsApp, Twitter, Telegram

#### RawMessage
- Unprocessed messages from platforms
- Original platform data (JSONB)
- Processing status flag
- Unique per connection + platform message ID

#### Message
- Normalized messages in unified schema
- Platform-agnostic content structure
- Thread grouping support
- Sender tracking
- Metadata preservation

### Relationship Models (Task 2.3)

#### Contact
- Unified identity across platforms
- Multiple emails and phones
- Platform-specific identities (JSONB)
- Custom metadata support

#### Thread
- Conversation grouping
- Platform-specific thread IDs
- Participant tracking
- Message statistics

#### Participant
- Platform-specific user identities
- Linkable to unified contacts
- Name, email, phone fields
- Platform metadata

#### Attachment
- File attachments for messages
- MIME type and size tracking
- Storage path management
- Original platform URL

### AI Models (Task 2.4)

#### Entity
- Named entity extraction results
- Entity type and text
- Confidence scores
- Position and context metadata

#### Summary
- AI-generated summaries
- Multiple summary types
- Thread association
- Generation metadata

#### Embedding
- Vector embeddings for semantic search
- 768-dimensional vectors (nomic-embed-text)
- Model tracking
- One-to-one with messages

## Database Session Management

### Usage in FastAPI

```python
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from db import get_db

@app.get("/items")
async def get_items(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Item))
    return result.scalars().all()
```

### Direct Session Usage

```python
from db import get_session

async with get_session() as session:
    result = await session.execute(query)
    await session.commit()
```

## Alembic Migrations

### Generate Migration

```bash
cd apps/backend
alembic revision --autogenerate -m "Description of changes"
```

### Apply Migrations

```bash
# Upgrade to latest
alembic upgrade head

# Downgrade one version
alembic downgrade -1

# Check current version
alembic current
```

## Configuration

Database configuration is managed through `config/config.py` using Pydantic Settings:

- `DATABASE_URL`: PostgreSQL connection string
- `DB_POOL_SIZE`: Connection pool size (default: 20)
- `DB_MAX_OVERFLOW`: Max overflow connections (default: 30)
- `DB_POOL_PRE_PING`: Test connections before use (default: True)

## Key Features

### UUID Primary Keys
All models use UUID v4 for primary keys, enabling distributed system compatibility.

### Automatic Timestamps
All models include `created_at` and `updated_at` timestamps with automatic management.

### JSONB Support
Flexible metadata storage using PostgreSQL JSONB for platform-specific data.

### Relationship Management
Comprehensive relationships with cascade deletes and proper foreign key constraints.

### Async Support
Full async/await support throughout the database layer for high performance.

## Next Steps

1. **Optional**: Generate initial migration with `alembic revision --autogenerate`
2. Set up event bus infrastructure (Task 3)
3. Implement FastAPI application foundation (Task 4)
4. Create platform connectors (Tasks 5-7)

## Requirements Satisfied

- ✅ 7.2: PostgreSQL with SQLAlchemy async ORM
- ✅ 1.2: Secure credential storage with encryption support
- ✅ 2.1: Message collection data structures
- ✅ 3.1: Unified message schema
- ✅ 4.1, 4.2: Contact and thread models
- ✅ 3.4: Attachment support
- ✅ 5.2, 5.3, 5.4: AI processing models (entities, summaries, embeddings)
