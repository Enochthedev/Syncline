# WebSocket API Documentation

## Overview

The R.E.M.I WebSocket API provides real-time communication capabilities for the MESH Ingestion System. It enables real-time notifications, search result streaming, proactive nudge delivery, and live conversation updates.

## Features

### ✅ Implemented Features

- **Real-time Connection Management**: WebSocket connection lifecycle with authentication
- **Search Result Streaming**: Stream search results in real-time with batching
- **Live Conversation Updates**: Real-time message and thread updates
- **Proactive Nudge Delivery**: AI-powered nudges delivered via WebSocket
- **System Notifications**: Broadcast and targeted system notifications
- **Connection Authentication**: Token-based authentication for WebSocket connections
- **Topic Subscriptions**: Subscribe to specific topics for targeted updates
- **Health Monitoring**: Health checks and connection statistics
- **Error Handling**: Comprehensive error handling and recovery

## Architecture

### Components

1. **WebSocketManager** (`api/websocket/manager.py`)
   - Manages WebSocket connections and lifecycle
   - Handles authentication and authorization
   - Manages subscriptions and message routing
   - Provides connection statistics and health monitoring

2. **WebSocketHandlers** (`api/websocket/handlers.py`)
   - Handles different types of WebSocket messages
   - Coordinates with search and memory agents
   - Manages event listeners for real-time updates

3. **SearchStreamHandler** (`api/websocket/search_handler.py`)
   - Handles real-time search result streaming
   - Batches results for optimal performance
   - Integrates with HybridSearchAgent

4. **EventHandler** (`api/websocket/event_handler.py`)
   - Handles conversation updates and notifications
   - Integrates with event bus for real-time updates
   - Manages nudge delivery

## API Endpoints

### WebSocket Endpoint

```
ws://localhost:8000/api/v1/ws/connect
```

### HTTP Endpoints

- `GET /api/v1/ws/test` - WebSocket test page with JavaScript client
- `GET /api/v1/ws/stats` - WebSocket connection statistics
- `GET /api/v1/ws/health` - WebSocket service health check

## Message Types

### Connection Management

- `connect` - Connection established
- `disconnect` - Connection closed
- `ping` / `pong` - Keep-alive messages
- `error` - Error notifications

### Authentication

- `auth_request` - Authentication request
- `auth_success` - Authentication successful
- `auth_failure` - Authentication failed

### Search Streaming

- `search_start` - Start search stream
- `search_result` - Individual search result
- `search_complete` - Search completed
- `search_error` - Search error

### Conversation Updates

- `message_received` - New message received
- `message_updated` - Message updated
- `thread_updated` - Thread updated
- `participant_updated` - Participant updated

### Proactive Nudges

- `nudge_delivery` - Nudge delivered to user
- `nudge_acknowledged` - Nudge acknowledged by user

### System Notifications

- `system_notification` - System notification
- `status_update` - System status update

## Usage Examples

### JavaScript Client

```javascript
// Connect to WebSocket
const ws = new WebSocket('ws://localhost:8000/api/v1/ws/connect');

// Handle connection
ws.onopen = function(event) {
    console.log('Connected to WebSocket');
    
    // Authenticate
    ws.send(JSON.stringify({
        type: 'auth_request',
        data: {
            user_id: 'your_user_id',
            token: 'your_auth_token'
        }
    }));
};

// Handle messages
ws.onmessage = function(event) {
    const message = JSON.parse(event.data);
    console.log('Received:', message);
    
    switch(message.type) {
        case 'auth_success':
            console.log('Authenticated successfully');
            break;
        case 'search_result':
            console.log('Search result:', message.data);
            break;
        case 'nudge_delivery':
            console.log('Nudge received:', message.data.nudge);
            break;
        case 'system_notification':
            console.log('Notification:', message.data);
            break;
    }
};

// Start search stream
function startSearch(query) {
    ws.send(JSON.stringify({
        type: 'search_start',
        data: {
            query: query,
            limit: 50,
            stream_results: true,
            include_suggestions: true
        }
    }));
}

// Acknowledge nudge
function acknowledgeNudge(nudgeId) {
    ws.send(JSON.stringify({
        type: 'nudge_acknowledged',
        data: {
            nudge_id: nudgeId
        }
    }));
}
```

### Python Client

```python
import asyncio
import json
import websockets

async def websocket_client():
    uri = "ws://localhost:8000/api/v1/ws/connect"
    
    async with websockets.connect(uri) as websocket:
        # Authenticate
        auth_message = {
            "type": "auth_request",
            "data": {
                "user_id": "your_user_id",
                "token": "your_auth_token"
            }
        }
        await websocket.send(json.dumps(auth_message))
        
        # Listen for messages
        async for message in websocket:
            data = json.loads(message)
            print(f"Received: {data['type']}")
            
            if data['type'] == 'auth_success':
                # Start search after authentication
                search_message = {
                    "type": "search_start",
                    "data": {
                        "query": "test search",
                        "limit": 20
                    }
                }
                await websocket.send(json.dumps(search_message))

# Run client
asyncio.run(websocket_client())
```

## Message Formats

### Authentication Request

```json
{
    "type": "auth_request",
    "data": {
        "user_id": "user123",
        "token": "auth_token_here",
        "client_info": {
            "user_agent": "Mozilla/5.0...",
            "timestamp": "2024-01-01T00:00:00Z"
        }
    }
}
```

### Search Stream Request

```json
{
    "type": "search_start",
    "data": {
        "query": "search query",
        "limit": 50,
        "stream_results": true,
        "include_suggestions": true,
        "filters": {
            "platforms": ["gmail", "slack"],
            "date_from": "2024-01-01T00:00:00Z",
            "date_to": "2024-01-31T23:59:59Z"
        }
    },
    "correlation_id": "search_123"
}
```

### Search Result

```json
{
    "type": "search_result",
    "data": {
        "result": {
            "id": "msg_123",
            "type": "message",
            "title": "Email Subject",
            "content": "Email content...",
            "platform": "gmail",
            "timestamp": "2024-01-01T10:00:00Z",
            "ranking": {
                "combined_score": 0.95
            }
        },
        "batch_index": 0,
        "total_batches": 5,
        "is_final": false
    },
    "correlation_id": "search_123"
}
```

### Nudge Delivery

```json
{
    "type": "nudge_delivery",
    "data": {
        "nudge": {
            "id": "nudge_123",
            "type": "deadline_reminder",
            "priority": "high",
            "title": "Deadline Reminder",
            "message": "Don't forget about the meeting tomorrow!",
            "confidence_score": 0.9
        },
        "requires_acknowledgment": true,
        "expires_at": "2024-01-02T00:00:00Z"
    }
}
```

### System Notification

```json
{
    "type": "system_notification",
    "data": {
        "level": "info",
        "title": "System Update",
        "message": "The system has been updated successfully",
        "action_url": "/updates",
        "action_text": "View Details",
        "auto_dismiss": true,
        "dismiss_after": 5000
    }
}
```

## Subscriptions

Users can subscribe to specific topics to receive targeted updates:

- `user:{user_id}` - User-specific messages
- `thread:{thread_id}` - Thread-specific updates
- `platform:{platform}` - Platform-specific updates
- `nudges:{user_id}` - User-specific nudges

## Error Handling

The WebSocket API includes comprehensive error handling:

- Connection errors are logged and connections are cleaned up
- Authentication failures are reported with specific error codes
- Search errors are handled gracefully with error messages
- Stale connections are automatically cleaned up

## Performance Considerations

- **Batching**: Search results are streamed in batches to prevent overwhelming clients
- **Connection Pooling**: Efficient connection management with automatic cleanup
- **Message Queuing**: Messages are queued for delivery with proper acknowledgment
- **Health Monitoring**: Regular health checks ensure system reliability

## Security

- **Token Authentication**: All connections require valid authentication tokens
- **User Isolation**: Messages are only sent to authorized users
- **Input Validation**: All incoming messages are validated
- **Rate Limiting**: Built-in protection against abuse

## Testing

The WebSocket API includes comprehensive tests:

- Unit tests for all components (`tests/test_websocket_api.py`)
- Integration tests for endpoints (`tests/test_websocket_endpoint.py`)
- Demo script for manual testing (`examples/websocket_demo.py`)
- Test page for browser testing (`/api/v1/ws/test`)

## Monitoring

### Statistics Available

- Active connections count
- Authenticated connections count
- Total messages sent/received
- Connection errors
- Authentication failures
- Subscription counts

### Health Checks

- WebSocket manager health
- Handler component health
- Search agent status
- Memory agent status

## Integration

The WebSocket API integrates with:

- **Event Bus**: Listens for real-time events
- **Search Agent**: Streams search results
- **Memory Agent**: Delivers proactive nudges
- **Authentication System**: Validates user tokens
- **Database**: Stores connection metadata

## Future Enhancements

Potential future improvements:

- Message persistence for offline users
- Advanced subscription filtering
- WebSocket compression
- Metrics and analytics
- Load balancing for multiple instances
- Custom message types for specific use cases

## Troubleshooting

### Common Issues

1. **Connection Refused**: Ensure the server is running and WebSocket endpoint is accessible
2. **Authentication Failed**: Verify token validity and user permissions
3. **No Messages Received**: Check subscription topics and user authentication
4. **Search Not Working**: Verify search agent is initialized and running

### Debug Mode

Enable debug logging to see detailed WebSocket activity:

```python
import logging
logging.getLogger('api.websocket').setLevel(logging.DEBUG)
```

## Requirements Satisfied

This implementation satisfies the following requirements from the specification:

- **Requirement 2.1**: Real-time message ingestion with minimal latency
- **Requirement 6.1**: Proactive nudge delivery with contextual reminders
- **Requirement 6.4**: Intelligent follow-up nudges with timing awareness

The WebSocket API provides a robust foundation for real-time communication in the R.E.M.I system, enabling responsive user experiences and proactive AI assistance.