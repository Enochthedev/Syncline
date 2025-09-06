# Slack Connector Documentation

## Overview

The Slack connector provides comprehensive integration with Slack workspaces, supporting both real-time message ingestion and historical data fetching. It implements OAuth 2.0 authentication, Socket Mode for real-time events, and the Events API for webhook-based processing.

## Features

### Authentication
- **OAuth 2.0**: Complete OAuth flow for workspace authorization
- **Bot Token**: Direct bot token authentication for development
- **Token Management**: Automatic token refresh and validation

### Real-time Processing
- **Socket Mode**: WebSocket-based real-time event processing
- **Events API**: Webhook-based event handling with signature validation
- **Message Filtering**: Automatic filtering of bot messages and unwanted subtypes
- **Reconnection Logic**: Automatic reconnection with exponential backoff

### Data Ingestion
- **Historical Messages**: Fetch message history from all channels and DMs
- **Channel Management**: Automatic discovery and caching of channels and users
- **File Attachments**: Support for file attachments and rich content
- **Pagination**: Cursor-based pagination for large datasets

### Event Processing
- **Message Events**: Real-time processing of new messages
- **Channel Events**: Handling of channel creation, deletion, and updates
- **User Events**: Processing of user changes and team joins
- **Queue Management**: Asynchronous message processing with error handling

## Configuration

### Environment Variables

```bash
# Required
SLACK_CLIENT_ID=your_client_id
SLACK_CLIENT_SECRET=your_client_secret

# Optional - for Socket Mode
SLACK_APP_TOKEN=xapp-your-app-token

# Optional - for direct bot token auth
SLACK_BOT_TOKEN=xoxb-your-bot-token

# Optional - for webhook validation
SLACK_SIGNING_SECRET=your_signing_secret

# Configuration
SLACK_SCOPES="channels:history channels:read chat:write users:read"
SLACK_REDIRECT_URI="http://localhost:8000/slack/oauth/callback"
SLACK_SOCKET_MODE_ENABLED=true
SLACK_EVENTS_API_ENABLED=true
SLACK_MAX_RESULTS=200
SLACK_INCLUDE_PRIVATE_CHANNELS=true
SLACK_INCLUDE_DIRECT_MESSAGES=true
```

### Required Slack App Permissions

#### Bot Token Scopes
- `channels:history` - Read message history from public channels
- `channels:read` - View basic information about public channels
- `groups:history` - Read message history from private channels
- `groups:read` - View basic information about private channels
- `im:history` - Read message history from direct messages
- `im:read` - View basic information about direct messages
- `mpim:history` - Read message history from group direct messages
- `mpim:read` - View basic information about group direct messages
- `users:read` - View people in the workspace
- `users:read.email` - View email addresses of people in the workspace
- `team:read` - View the workspace name and other basic team information
- `chat:write` - Send messages (optional, for future features)

#### Event Subscriptions (for Events API)
- `message.channels` - Messages posted to public channels
- `message.groups` - Messages posted to private channels
- `message.im` - Messages posted to direct message channels
- `message.mpim` - Messages posted to group direct message channels

## Usage

### Basic Setup

```python
from integrations import SlackConnectorFactory
from services.event_bus import EventBus

# Create event bus
event_bus = EventBus()

# Create connector using factory
connector = SlackConnectorFactory.create_connector(event_bus=event_bus)

# Start the connector
await connector.start()
```

### Custom Configuration

```python
from integrations import SlackConnector

config = {
    'client_id': 'your_client_id',
    'client_secret': 'your_client_secret',
    'bot_token': 'xoxb-your-bot-token',
    'socket_mode_enabled': True,
    'events_api_enabled': True,
    'max_results': 100
}

connector = SlackConnector(config=config, event_bus=event_bus)
```

### Fetching Historical Messages

```python
# Fetch recent messages
messages = await connector.fetch_historical_messages(limit=100)

# Fetch with pagination
messages = await connector.fetch_historical_messages(cursor="next_page_token", limit=50)
```

### Handling Webhooks

```python
# In your FastAPI app
@app.post("/webhooks/slack")
async def slack_webhook(request: Request):
    payload = await request.json()
    result = await connector.handle_webhook(payload)
    
    # Return challenge for URL verification
    if result:
        return {"challenge": result}
    
    return {"status": "ok"}
```

## Architecture

### Socket Mode Flow
1. Connector requests Socket Mode URL from Slack API
2. WebSocket connection established with automatic reconnection
3. Events received and acknowledged immediately
4. Messages queued for asynchronous processing
5. Processed messages published to event bus

### Events API Flow
1. Slack sends webhook to configured endpoint
2. Webhook signature validated (if signing secret provided)
3. URL verification challenge handled automatically
4. Events processed and published to event bus

### Message Processing Pipeline
1. Raw Slack message received
2. Message normalized to unified schema
3. Content extracted and attachments processed
4. Bot messages and unwanted subtypes filtered
5. Normalized message published to event bus

## Error Handling

### Connection Errors
- Automatic reconnection with exponential backoff
- Circuit breaker pattern for API failures
- Dead letter queue for failed message processing

### Authentication Errors
- Automatic token refresh when possible
- Clear error messages for configuration issues
- Graceful degradation when tokens expire

### Rate Limiting
- Respect Slack API rate limits
- Automatic backoff and retry logic
- Configurable rate limiting parameters

## Testing

### Unit Tests
```bash
pytest tests/test_slack_connector.py -v
```

### Integration Tests
```bash
pytest tests/test_slack_integration.py -v
```

### Factory Tests
```bash
pytest tests/test_slack_integration.py::TestSlackConnectorFactory -v
```

## Monitoring

### Health Checks
The connector provides health check endpoints that verify:
- API connectivity
- Token validity
- Socket Mode connection status
- Message processing queue health

### Metrics
Key metrics tracked:
- Messages processed per minute
- API call success/failure rates
- Connection uptime
- Queue depth and processing latency

## Troubleshooting

### Common Issues

1. **Socket Mode not connecting**
   - Verify `SLACK_APP_TOKEN` is set and valid
   - Check that Socket Mode is enabled in Slack app settings
   - Ensure app has required permissions

2. **Webhook events not received**
   - Verify webhook URL is publicly accessible
   - Check `SLACK_SIGNING_SECRET` configuration
   - Ensure Events API is enabled and subscribed to correct events

3. **Authentication failures**
   - Verify OAuth credentials are correct
   - Check that bot token has required scopes
   - Ensure redirect URI matches app configuration

4. **Missing messages**
   - Check rate limiting configuration
   - Verify all required permissions are granted
   - Review message filtering logic for bot messages

### Debug Mode
Enable debug logging to troubleshoot issues:

```python
import logging
logging.getLogger('integrations.slack_connector').setLevel(logging.DEBUG)
```

## Security Considerations

- Store tokens securely using the token manager
- Validate webhook signatures to prevent spoofing
- Use HTTPS for all webhook endpoints
- Implement proper access controls for sensitive operations
- Regular token rotation and monitoring

## Future Enhancements

- Support for Slack Connect (external workspaces)
- Message threading and reply handling
- Rich message formatting and blocks
- File upload and sharing capabilities
- Slack Workflow integration
- Advanced search and filtering options