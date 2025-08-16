# MESH Ingestion System - API Reference

## Base URL
- **Development**: `http://localhost:8000`
- **Production**: `https://your-domain.com`

## Authentication
Most endpoints require authentication. The system supports:
- API Keys (for service-to-service)
- OAuth 2.0 (for user access)
- Webhook signatures (for platform callbacks)

## Response Format
All API responses follow this structure:
```json
{
  "success": true,
  "data": { ... },
  "error": null,
  "timestamp": "2025-01-15T10:30:00Z",
  "request_id": "req_123456789"
}
```

Error responses:
```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid request parameters",
    "details": { ... }
  },
  "timestamp": "2025-01-15T10:30:00Z",
  "request_id": "req_123456789"
}
```

## Endpoints

### System Health & Status

#### `GET /health`
Basic health check endpoint.

**Response**:
```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "timestamp": "2025-01-15T10:30:00Z",
    "version": "1.0.0"
  }
}
```

**Status Codes**:
- `200`: System is healthy
- `503`: System is unhealthy

---

#### `GET /status`
Detailed system status including all components.

**Response**:
```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "components": {
      "database": {
        "status": "healthy",
        "response_time_ms": 12,
        "connections": {
          "active": 5,
          "idle": 15,
          "max": 20
        }
      },
      "redis": {
        "status": "healthy",
        "response_time_ms": 3,
        "memory_usage": "45MB",
        "connected_clients": 8
      },
      "event_bus": {
        "status": "healthy",
        "streams": {
          "messages.raw": {
            "length": 1250,
            "consumers": 2
          },
          "messages.normalized": {
            "length": 890,
            "consumers": 3
          }
        }
      }
    },
    "metrics": {
      "messages_processed_24h": 15420,
      "error_rate_24h": 0.02,
      "avg_processing_time_ms": 145
    }
  }
}
```

---

### Platform Management

#### `GET /platforms`
List all supported platforms and their status.

**Response**:
```json
{
  "success": true,
  "data": {
    "platforms": [
      {
        "name": "gmail",
        "display_name": "Gmail",
        "status": "active",
        "capabilities": [
          "real_time_ingestion",
          "historical_fetch",
          "webhook_support"
        ],
        "last_activity": "2025-01-15T10:29:45Z",
        "messages_today": 1250
      },
      {
        "name": "slack",
        "display_name": "Slack",
        "status": "planned",
        "capabilities": [],
        "last_activity": null,
        "messages_today": 0
      }
    ]
  }
}
```

---

#### `GET /platforms/{platform}/status`
Get detailed status for a specific platform.

**Parameters**:
- `platform` (path): Platform identifier (e.g., "gmail", "slack")

**Response**:
```json
{
  "success": true,
  "data": {
    "platform": "gmail",
    "status": "healthy",
    "connector": {
      "status": "running",
      "uptime_seconds": 86400,
      "last_check": "2025-01-15T10:29:45Z",
      "error_count": 2,
      "restart_count": 0
    },
    "authentication": {
      "status": "valid",
      "expires_at": "2025-01-16T10:30:00Z",
      "scopes": [
        "https://www.googleapis.com/auth/gmail.readonly"
      ]
    },
    "metrics": {
      "messages_processed": 1250,
      "messages_failed": 2,
      "avg_processing_time_ms": 120,
      "rate_limit_hits": 0
    },
    "real_time": {
      "webhook_active": true,
      "last_webhook": "2025-01-15T10:28:30Z",
      "push_notifications": "enabled"
    }
  }
}
```

---

### Message Operations

#### `GET /messages`
Query messages with optional filters.

**Query Parameters**:
- `platform` (optional): Filter by platform
- `thread_id` (optional): Filter by thread
- `sender_id` (optional): Filter by sender
- `start_date` (optional): Start date (ISO 8601)
- `end_date` (optional): End date (ISO 8601)
- `limit` (optional): Number of results (default: 50, max: 1000)
- `offset` (optional): Pagination offset (default: 0)
- `sort` (optional): Sort field (default: "timestamp")
- `order` (optional): Sort order ("asc" or "desc", default: "desc")

**Example Request**:
```
GET /messages?platform=gmail&limit=10&start_date=2025-01-15T00:00:00Z
```

**Response**:
```json
{
  "success": true,
  "data": {
    "messages": [
      {
        "id": "msg_123456789",
        "platform": "gmail",
        "platform_message_id": "gmail_msg_abc123",
        "thread_id": "thread_xyz789",
        "sender": {
          "id": "sender_456",
          "display_name": "John Doe",
          "email": "john@example.com"
        },
        "content": {
          "text": "Hello, this is a test message.",
          "html": "<p>Hello, this is a test message.</p>",
          "primary_format": "text"
        },
        "attachments": [],
        "timestamp": "2025-01-15T10:25:00Z",
        "created_at": "2025-01-15T10:25:30Z"
      }
    ],
    "pagination": {
      "total": 1250,
      "limit": 10,
      "offset": 0,
      "has_more": true
    }
  }
}
```

---

#### `GET /messages/{id}`
Get a specific message by ID.

**Parameters**:
- `id` (path): Message ID

**Response**:
```json
{
  "success": true,
  "data": {
    "message": {
      "id": "msg_123456789",
      "platform": "gmail",
      "platform_message_id": "gmail_msg_abc123",
      "thread_id": "thread_xyz789",
      "sender": {
        "id": "sender_456",
        "display_name": "John Doe",
        "email": "john@example.com",
        "avatar_url": "https://example.com/avatar.jpg"
      },
      "recipients": [
        {
          "id": "recipient_789",
          "display_name": "Jane Smith",
          "email": "jane@example.com"
        }
      ],
      "content": {
        "text": "Hello, this is a test message with attachment.",
        "html": "<p>Hello, this is a test message with attachment.</p>",
        "primary_format": "text"
      },
      "attachments": [
        {
          "id": "att_123",
          "filename": "document.pdf",
          "mime_type": "application/pdf",
          "file_size": 12345,
          "attachment_type": "document",
          "storage_url": "https://storage.example.com/att_123"
        }
      ],
      "timestamp": "2025-01-15T10:25:00Z",
      "metadata": {
        "labels": ["INBOX", "IMPORTANT"],
        "thread_length": 5
      },
      "entities": [
        {
          "type": "person",
          "value": "John Doe",
          "confidence": 0.95
        }
      ],
      "created_at": "2025-01-15T10:25:30Z",
      "updated_at": "2025-01-15T10:25:30Z"
    }
  }
}
```

---

#### `POST /messages/search`
Advanced message search with complex filters.

**Request Body**:
```json
{
  "query": {
    "text": "project update",
    "platforms": ["gmail", "slack"],
    "date_range": {
      "start": "2025-01-01T00:00:00Z",
      "end": "2025-01-15T23:59:59Z"
    },
    "senders": ["john@example.com"],
    "has_attachments": true,
    "entity_filters": [
      {
        "type": "organization",
        "value": "Acme Corp"
      }
    ]
  },
  "options": {
    "limit": 50,
    "offset": 0,
    "sort": "relevance",
    "include_content": true,
    "include_entities": true
  }
}
```

**Response**:
```json
{
  "success": true,
  "data": {
    "results": [
      {
        "message": { /* message object */ },
        "relevance_score": 0.95,
        "highlights": {
          "content": ["<mark>project update</mark> for Q1"],
          "entities": ["<mark>Acme Corp</mark>"]
        }
      }
    ],
    "pagination": {
      "total": 25,
      "limit": 50,
      "offset": 0,
      "has_more": false
    },
    "facets": {
      "platforms": {
        "gmail": 15,
        "slack": 10
      },
      "senders": {
        "john@example.com": 12,
        "jane@example.com": 8
      }
    }
  }
}
```

---

### Webhook Endpoints

#### `POST /webhooks/gmail`
Gmail push notification webhook endpoint.

**Headers**:
- `Content-Type: application/json`
- `X-Goog-Channel-ID`: Channel ID from subscription
- `X-Goog-Channel-Token`: Verification token
- `X-Goog-Resource-State`: Resource state (sync, exists, not_exists)

**Request Body**:
```json
{
  "message": {
    "data": "eyJoaXN0b3J5SWQiOiAiMTIzNDUifQ==",
    "messageId": "msg_123456789",
    "publishTime": "2025-01-15T10:30:00Z"
  },
  "subscription": "projects/your-project/subscriptions/gmail-push"
}
```

**Response**:
```json
{
  "success": true,
  "data": {
    "processed": true,
    "history_id": "12345",
    "queued_for_processing": true
  }
}
```

**Status Codes**:
- `200`: Webhook processed successfully
- `400`: Invalid webhook payload
- `401`: Invalid webhook signature
- `500`: Processing error

---

### Thread Operations

#### `GET /threads/{thread_id}`
Get all messages in a thread.

**Parameters**:
- `thread_id` (path): Thread identifier
- `platform` (query, optional): Filter by platform

**Response**:
```json
{
  "success": true,
  "data": {
    "thread": {
      "id": "thread_xyz789",
      "title": "Project Discussion",
      "participants": [
        {
          "id": "user_123",
          "display_name": "John Doe",
          "email": "john@example.com"
        }
      ],
      "message_count": 5,
      "last_message_at": "2025-01-15T10:30:00Z",
      "platforms": ["gmail"],
      "messages": [
        { /* message objects */ }
      ]
    }
  }
}
```

---

## Error Codes

| Code | Description |
|------|-------------|
| `VALIDATION_ERROR` | Request validation failed |
| `AUTHENTICATION_ERROR` | Authentication required or failed |
| `AUTHORIZATION_ERROR` | Insufficient permissions |
| `NOT_FOUND` | Resource not found |
| `RATE_LIMIT_EXCEEDED` | Too many requests |
| `PLATFORM_ERROR` | Platform-specific error |
| `PROCESSING_ERROR` | Message processing failed |
| `WEBHOOK_ERROR` | Webhook processing failed |
| `INTERNAL_ERROR` | Internal server error |

## Rate Limits

| Endpoint Category | Limit | Window |
|------------------|-------|---------|
| Health/Status | 100 req/min | Per IP |
| Message Queries | 1000 req/hour | Per API key |
| Search | 100 req/hour | Per API key |
| Webhooks | No limit | - |

## Webhooks

### Security
All webhooks are verified using:
- HMAC-SHA256 signatures
- Timestamp validation (5-minute window)
- IP allowlisting (optional)

### Retry Policy
Failed webhook deliveries are retried with exponential backoff:
- Initial retry: 1 second
- Maximum retry: 300 seconds
- Maximum attempts: 5
- Backoff multiplier: 2.0

### Webhook Events
Currently supported webhook events:
- `message.received` - New message ingested
- `message.processed` - Message fully processed
- `thread.updated` - Thread metadata updated
- `platform.connected` - Platform connector activated
- `platform.disconnected` - Platform connector deactivated

---

**Last Updated**: January 15, 2025  
**API Version**: 1.0.0

For implementation examples, see `/docs/examples/`.