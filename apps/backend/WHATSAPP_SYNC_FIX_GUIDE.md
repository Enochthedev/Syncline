# WhatsApp Message Sync - Enhanced Version

## Overview

This guide documents the enhanced WhatsApp integration with comprehensive fixes for message syncing issues.

## Problems Fixed

### 1. **Bridge Response Timeouts**
**Problem:** Bridge commands (QR code, pairing code) would timeout after only 5 attempts with 1-second delays.

**Solution:**
- Increased to 15 attempts with progressive delays (1s → 3s)
- Better response parsing to distinguish between different message types
- Enhanced logging for debugging

**Files:**
- `integrations/whatsapp_connector_enhanced.py`

### 2. **Room Discovery Timing Issues**
**Problem:** After login, rooms wouldn't appear because the bridge hadn't finished creating them yet.

**Solution:**
- Added retry logic for room discovery with exponential backoff
- Automatic trigger of bridge sync commands before room discovery
- Wait periods after sync commands to let bridge process (5s instead of 3s)

**Files:**
- `services/whatsapp_sync_enhanced.py`
- `integrations/whatsapp_connector_enhanced.py`

### 3. **No Retry Logic for Failed Syncs**
**Problem:** If message sync failed, it would just log the error and give up.

**Solution:**
- Implemented comprehensive retry system with configurable parameters:
  - Max retries: 5 (configurable)
  - Exponential backoff: 1s → 30s
  - Jitter to prevent thundering herd
- Detailed statistics tracking for diagnostics

**Files:**
- `services/whatsapp_sync_enhanced.py`

### 4. **Race Conditions in Sync**
**Problem:** Multiple sync operations could run simultaneously, causing duplicates and conflicts.

**Solution:**
- Added per-connection locks to prevent concurrent syncs
- Track last sync time to prevent too-frequent syncs
- Coordination between background sync and manual sync

**Files:**
- `services/whatsapp_sync_enhanced.py`

### 5. **Insufficient Diagnostics**
**Problem:** Hard to debug why syncing wasn't working.

**Solution:**
- Created comprehensive diagnostic tool that tests:
  - Configuration
  - Database connectivity
  - Bridge connectivity
  - Bridge status
  - Room discovery
  - Message fetching
  - Database sync
- Detailed logging with prefixes ([BRIDGE], [SYNC], [ROOMS])
- Statistics tracking (messages/second, duration, error counts)

**Files:**
- `scripts/test_whatsapp_sync_enhanced.py`
- `api/routes/whatsapp/messaging_enhanced.py`

## Architecture

### Enhanced Components

```
┌─────────────────────────────────────────────────────────────┐
│                     Enhanced WhatsApp Stack                  │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌────────────────────────────────────────────────────┐    │
│  │    EnhancedMatrixWhatsAppClient                    │    │
│  │    - 15 retry attempts (vs 5)                      │    │
│  │    - Progressive delays (1s → 3s)                  │    │
│  │    - Better response parsing                        │    │
│  │    - Detailed logging with prefixes                │    │
│  └────────────────────────────────────────────────────┘    │
│                           ↓                                   │
│  ┌────────────────────────────────────────────────────┐    │
│  │    EnhancedWhatsAppConnector                       │    │
│  │    - Better sync_all_chats with longer waits      │    │
│  │    - Enhanced room discovery                        │    │
│  │    - Improved error handling                        │    │
│  └────────────────────────────────────────────────────┘    │
│                           ↓                                   │
│  ┌────────────────────────────────────────────────────┐    │
│  │    EnhancedWhatsAppMessageSyncService              │    │
│  │    - Retry queue with exponential backoff          │    │
│  │    - Per-connection locks (prevent duplicates)     │    │
│  │    - Statistics tracking                            │    │
│  │    - Sync coordination                              │    │
│  └────────────────────────────────────────────────────┘    │
│                           ↓                                   │
│  ┌────────────────────────────────────────────────────┐    │
│  │    Enhanced API Routes                              │    │
│  │    - /sync/enhanced (with retry)                   │    │
│  │    - /diagnostics (health check)                   │    │
│  │    - /rooms/discover (force discovery)             │    │
│  │    - /bridge/sync (manual bridge sync)             │    │
│  └────────────────────────────────────────────────────┘    │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

## Usage Guide

### 1. Using Enhanced Sync Service

```python
from services.whatsapp_sync_enhanced import get_enhanced_whatsapp_sync_service

sync_service = get_enhanced_whatsapp_sync_service()

# Sync with automatic retries
result = await sync_service.sync_messages_for_connection(
    db,
    connection_id,
    limit=100,
    force=False  # Set to True to force sync even if recently synced
)

# Check result
if result["success"]:
    print(f"Synced {result['total_messages_synced']} messages")
    print(f"Statistics: {result['stats']}")
else:
    print(f"Sync failed: {result['error']}")
```

### 2. Using Enhanced Connector

```python
from integrations.whatsapp_connector_enhanced import EnhancedWhatsAppConnector

connector = EnhancedWhatsAppConnector(
    connection_id=connection_id,
    credentials=credentials
)

await connector.connect()

# Sync with better reliability
sync_result = await connector.sync_all_chats()

# Discover rooms with retry
rooms = await connector.get_rooms()

await connector.disconnect()
```

### 3. Running Diagnostics

#### Via Script
```bash
cd apps/backend
python scripts/test_whatsapp_sync_enhanced.py --connection-id <uuid>
```

#### Via API
```bash
curl -X GET "http://localhost:8000/api/whatsapp/<connection_id>/diagnostics" \
  -H "Authorization: Bearer <token>"
```

### 4. Enhanced API Endpoints

#### Sync Messages with Retry
```http
POST /api/whatsapp/{connection_id}/sync/enhanced
{
  "limit": 100,
  "force": false
}
```

**Response:**
```json
{
  "connection_id": "...",
  "success": true,
  "total_rooms": 15,
  "total_messages_synced": 234,
  "stats": {
    "sync_attempts": 1,
    "successful_syncs": 1,
    "messages_per_second": 12.5,
    "duration_seconds": 18.7
  }
}
```

#### Get Sync Status
```http
GET /api/whatsapp/{connection_id}/sync/status
```

**Response:**
```json
{
  "connection_id": "...",
  "last_sync_at": "2025-12-31T10:30:00Z",
  "time_since_last_sync": 120.5,
  "is_syncing": false
}
```

#### Discover Rooms
```http
POST /api/whatsapp/{connection_id}/rooms/discover
```

**Response:**
```json
{
  "connection_id": "...",
  "success": true,
  "room_count": 15,
  "rooms": [
    {
      "room_id": "!abc123:localhost",
      "name": "Mom",
      "is_group": false
    }
  ]
}
```

#### Run Diagnostics
```http
GET /api/whatsapp/{connection_id}/diagnostics
```

**Response:**
```json
{
  "connection_id": "...",
  "tests": [
    {
      "test": "bridge_connectivity",
      "success": true,
      "details": {"user_id": "@syncline:localhost"}
    },
    {
      "test": "bridge_status",
      "success": true,
      "details": {
        "connected": true,
        "logged_in": true,
        "phone": "+1234567890"
      }
    }
  ],
  "summary": {
    "total_tests": 4,
    "passed": 4,
    "failed": 0
  }
}
```

## Configuration

### Retry Configuration

```python
from services.whatsapp_sync_enhanced import RetryConfig, EnhancedWhatsAppMessageSyncService

# Custom retry config
retry_config = RetryConfig(
    max_retries=5,           # Maximum number of retry attempts
    initial_delay=1.0,       # Initial delay in seconds
    max_delay=30.0,          # Maximum delay in seconds
    exponential_base=2.0,    # Exponential backoff multiplier
    jitter=True              # Add randomness to prevent thundering herd
)

sync_service = EnhancedWhatsAppMessageSyncService(retry_config=retry_config)
```

### Environment Variables

Ensure these are set in your `.env` file:

```env
# Matrix/WhatsApp Bridge Configuration
MATRIX_HOMESERVER_URL=http://localhost:8008
MATRIX_ACCESS_TOKEN=<your_token>
MATRIX_USER_ID=@syncline:localhost
WHATSAPP_BRIDGE_BOT_ID=@whatsappbot:localhost

# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost/dbname
```

## Troubleshooting

### Issue: No rooms found after login

**Symptoms:**
- User successfully scans QR code
- Bridge shows logged in
- But no chat rooms appear

**Solution:**
1. Run diagnostics:
   ```bash
   python scripts/test_whatsapp_sync_enhanced.py --connection-id <id>
   ```

2. Check if bridge needs sync:
   ```http
   POST /api/whatsapp/{connection_id}/bridge/sync
   ```

3. Force room discovery:
   ```http
   POST /api/whatsapp/{connection_id}/rooms/discover
   ```

### Issue: Messages not syncing

**Symptoms:**
- Rooms appear but no messages

**Solution:**
1. Check if logged in:
   ```http
   GET /api/whatsapp/{connection_id}/login/status
   ```

2. Trigger manual sync with retry:
   ```http
   POST /api/whatsapp/{connection_id}/sync/enhanced
   ```

3. Check sync statistics:
   ```http
   GET /api/whatsapp/{connection_id}/sync/status
   ```

### Issue: Bridge timeouts

**Symptoms:**
- QR code requests timeout
- Bridge commands fail

**Solution:**
- The enhanced version already has longer timeouts (15 attempts vs 5)
- Check bridge logs:
  ```bash
  docker logs syncline-whatsapp-bridge
  ```
- Restart bridge if needed:
  ```bash
  docker-compose restart whatsapp-bridge
  ```

## Migration from Old Version

### Option 1: Use Enhanced Endpoints (Recommended)

Update your frontend to use new enhanced endpoints:

```javascript
// Old
POST /api/whatsapp/{id}/sync

// New (with retry)
POST /api/whatsapp/{id}/sync/enhanced
```

### Option 2: Replace Old Service

In your existing routes, replace the old service:

```python
# Old
from services.whatsapp_message_sync import get_whatsapp_sync_service

# New
from services.whatsapp_sync_enhanced import get_enhanced_whatsapp_sync_service

# Usage is the same
sync_service = get_enhanced_whatsapp_sync_service()
```

### Option 3: Update Connector Only

Just use the enhanced connector in your session manager:

```python
# In whatsapp_session_manager.py
from integrations.whatsapp_connector_enhanced import EnhancedWhatsAppConnector

def _get_connector(self, connection: PlatformConnection) -> WhatsAppConnector:
    # ... credentials setup ...

    return EnhancedWhatsAppConnector(  # Changed from WhatsAppConnector
        connection_id=connection.id,
        credentials=credentials,
    )
```

## Performance Improvements

### Metrics

Enhanced version includes built-in performance tracking:

```python
result = await sync_service.sync_messages_for_connection(...)

stats = result["stats"]
print(f"Messages per second: {stats['messages_per_second']}")
print(f"Total duration: {stats['duration_seconds']}s")
print(f"Sync attempts: {stats['sync_attempts']}")
```

### Optimization Tips

1. **Limit message count for background sync:**
   ```python
   # Background sync - fetch recent messages only
   result = await sync_service.sync_messages_for_connection(db, conn_id, limit=20)

   # Manual sync - fetch more messages
   result = await sync_service.sync_messages_for_connection(db, conn_id, limit=100)
   ```

2. **Avoid duplicate syncs:**
   - The service automatically prevents concurrent syncs per connection
   - Check `is_syncing` before triggering manual sync:
   ```python
   stats = sync_service.get_sync_stats(connection_id)
   if not stats["is_syncing"]:
       await sync_service.sync_messages_for_connection(...)
   ```

3. **Use force sparingly:**
   - Only use `force=True` when you know you need it
   - Normal syncs respect last sync time and won't duplicate work

## Logging

The enhanced version uses detailed logging prefixes:

```
[BRIDGE] - Bridge communication (commands, responses)
[SYNC] - Sync operations (contacts, groups, appstate)
[ROOMS] - Room discovery and management
[STATUS] - Status checks and health monitoring
```

To see detailed logs:

```python
import logging

# Enable debug logging for WhatsApp components
logging.getLogger("integrations.whatsapp_connector_enhanced").setLevel(logging.DEBUG)
logging.getLogger("services.whatsapp_sync_enhanced").setLevel(logging.DEBUG)
```

## Best Practices

1. **Always check login status before sync:**
   ```python
   status = await session_manager.check_login_status(db, connection_id)
   if status["logged_in"]:
       await sync_service.sync_messages_for_connection(...)
   ```

2. **Use diagnostics for troubleshooting:**
   - Run diagnostic endpoint first when user reports issues
   - Check specific test failures to identify root cause

3. **Monitor sync statistics:**
   - Track `messages_per_second` to identify performance issues
   - Monitor `sync_attempts` to catch frequent retries

4. **Implement proper error handling:**
   ```python
   result = await sync_service.sync_messages_for_connection(...)

   if not result["success"]:
       # Log detailed error
       logger.error(f"Sync failed: {result['error']}")
       logger.error(f"Stats: {result['stats']}")

       # Check specific errors
       stats = result["stats"]
       if "connection" in result["error"].lower():
           # Bridge connection issue
           ...
       elif stats["sync_attempts"] >= 5:
           # Max retries reached
           ...
   ```

## Testing

### Manual Testing

1. **Test QR Login:**
   ```bash
   curl -X GET "http://localhost:8000/api/whatsapp/{id}/login"
   # Should return QR code even if bridge is slow
   ```

2. **Test Room Discovery:**
   ```bash
   curl -X POST "http://localhost:8000/api/whatsapp/{id}/rooms/discover"
   # Should trigger sync and wait for rooms
   ```

3. **Test Enhanced Sync:**
   ```bash
   curl -X POST "http://localhost:8000/api/whatsapp/{id}/sync/enhanced" \
     -H "Content-Type: application/json" \
     -d '{"limit": 50, "force": false}'
   # Should retry on failures
   ```

### Automated Testing

Run the diagnostic script:

```bash
python scripts/test_whatsapp_sync_enhanced.py --connection-id <id>
```

This will:
- Test all components
- Generate detailed report
- Save results to JSON file

## Support

If you encounter issues:

1. Run diagnostics first
2. Check logs with proper prefixes
3. Review the detailed statistics in sync results
4. Check bridge logs: `docker logs syncline-whatsapp-bridge`

## Summary

The enhanced WhatsApp integration provides:

✅ **Better Reliability** - Automatic retries with exponential backoff
✅ **Improved Discovery** - Smart room discovery with waits and retries
✅ **Comprehensive Diagnostics** - Detailed testing and monitoring
✅ **Better Logging** - Prefixed logs for easier debugging
✅ **Performance Tracking** - Built-in statistics and metrics
✅ **Race Condition Prevention** - Per-connection locks
✅ **Enhanced Error Handling** - Detailed error messages with context

Use the enhanced version for production-ready WhatsApp message syncing!
