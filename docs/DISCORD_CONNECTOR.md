# Discord Connector

The Discord connector provides integration with Discord servers through the Discord Gateway WebSocket API and REST API. It supports real-time message ingestion, historical message fetching, and webhook handling.

## Features

- **Real-time Message Ingestion**: Uses Discord Gateway WebSocket for real-time message events
- **Historical Message Fetching**: Retrieves message history from channels with pagination
- **Bot Authentication**: Secure bot token authentication with Discord API
- **Guild Permission Handling**: Respects guild permissions and channel access
- **Rate Limiting**: Built-in rate limiting to comply with Discord API limits
- **Message Filtering**: Filters bot messages and system messages
- **Attachment Support**: Handles file attachments and embeds
- **Webhook Support**: Processes Discord webhook events

## Configuration

### Environment Variables

```bash
# Required
DISCORD_BOT_TOKEN=your_bot_token_here

# Optional
DISCORD_CLIENT_ID=your_client_id
DISCORD_CLIENT_SECRET=your_client_secret
DISCORD_WEBHOOK_SECRET=your_webhook_secret
DISCORD_INTENTS=513  # GUILDS + GUILD_MESSAGES
DISCORD_MAX_RESULTS=100
DISCORD_INCLUDE_DM_CHANNELS=true
DISCORD_MONITORED_GUILDS=guild1,guild2,guild3
DISCORD_STATUS=online
```

### Configuration Object

```python
config = {
    'bot_token': 'your_bot_token_here',
    'client_id': 'your_client_id',
    'client_secret': 'your_client_secret',
    'webhook_secret': 'your_webhook_secret',
    'intents': 513,  # GUILDS + GUILD_MESSAGES
    'max_results': 100,
    'include_dm_channels': True,
    'monitored_guilds': ['guild_123', 'guild_456'],
    'presence': {
        'status': 'online',
        'afk': False,
        'activities': [],
        'since': None
    }
}
```

## Usage

### Basic Setup

```python
from integrations.discord_factory import create_discord_connector
from services.event_bus import EventBus

# Create event bus
event_bus = EventBus(redis_client)

# Create connector from environment variables
connector = create_discord_connector_from_env(event_bus=event_bus)

# Or create with explicit configuration
config = {
    'bot_token': 'your_bot_token_here',
    'intents': 513
}
connector = create_discord_connector(config=config, event_bus=event_bus)

# Start the connector
await connector.start()
```

### Message Processing

```python
# The connector automatically publishes messages to the event bus
# Subscribe to receive processed messages
async def handle_message(event):
    message_data = event.data['message']
    print(f"New Discord message: {message_data['content']['text']}")

await event_bus.subscribe('messages.raw', handle_message)
```

### Historical Message Fetching

```python
# Fetch historical messages
messages = await connector.fetch_historical_messages(limit=50)

for message in messages:
    print(f"Message from {message.sender_id}: {message.content['text']}")
```

## Discord Bot Setup

### 1. Create Discord Application

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application"
3. Give your application a name
4. Go to the "Bot" section
5. Click "Add Bot"
6. Copy the bot token (this is your `DISCORD_BOT_TOKEN`)

### 2. Configure Bot Permissions

Required permissions:
- Read Messages/View Channels
- Read Message History
- Send Messages (if needed for responses)

### 3. Invite Bot to Server

1. Go to OAuth2 > URL Generator
2. Select "bot" scope
3. Select required permissions
4. Use the generated URL to invite the bot to your server

### 4. Configure Intents

The connector uses these intents by default:
- `GUILDS` (1): Access to guild information
- `GUILD_MESSAGES` (512): Access to guild messages

Total default intents: 513

For DM support, you may also need:
- `DIRECT_MESSAGES` (4096)

## Message Format

Discord messages are normalized to the standard MESH format:

```python
{
    'id': 'discord_123456789',
    'platform': 'discord',
    'platform_message_id': '123456789',
    'thread_id': 'channel_id',
    'sender_id': 'user_id',
    'content': {
        'text': 'Message content',
        'attachments': [
            {
                'id': 'attachment_id',
                'filename': 'image.png',
                'size': 1024,
                'url': 'https://cdn.discord.com/...',
                'content_type': 'image/png'
            }
        ],
        'embeds': [
            {
                'title': 'Embed Title',
                'description': 'Embed Description'
            }
        ]
    },
    'timestamp': '2024-01-15T10:30:00Z',
    'raw_data': { /* Original Discord message data */ }
}
```

## Rate Limiting

The Discord connector implements rate limiting to comply with Discord's API limits:

- **Global Rate Limit**: 50 requests per second
- **Per-Route Rate Limits**: Automatically handled based on response headers
- **Burst Support**: Allows short bursts of requests
- **Exponential Backoff**: Automatic retry with increasing delays

## Error Handling

The connector handles various error scenarios:

- **Authentication Errors**: Invalid bot token, insufficient permissions
- **Rate Limiting**: Automatic retry with proper delays
- **Network Errors**: Connection failures, timeouts
- **Gateway Errors**: WebSocket disconnections, reconnection logic
- **API Errors**: Invalid requests, server errors

## Monitoring

The connector provides health check capabilities:

```python
# Check connector health
health = await connector.health_check()
print(f"Status: {health.status}")
print(f"Uptime: {health.uptime_seconds}s")
print(f"Error count: {health.error_count}")
```

## Limitations

- **Bot Account Required**: Requires a Discord bot account, not user account
- **Guild Access**: Can only access guilds where the bot is a member
- **Message History**: Limited by Discord's message history retention
- **Rate Limits**: Subject to Discord's API rate limits
- **Permissions**: Respects Discord's permission system

## Troubleshooting

### Common Issues

1. **Authentication Failed**
   - Verify bot token is correct
   - Ensure bot has necessary permissions
   - Check if bot is added to the target guild

2. **No Messages Received**
   - Verify bot has "Read Messages" permission
   - Check if intents are properly configured
   - Ensure bot is in the channels you want to monitor

3. **Rate Limiting**
   - The connector handles rate limiting automatically
   - If you see frequent rate limit warnings, consider reducing request frequency

4. **Gateway Connection Issues**
   - Check network connectivity
   - Verify Discord Gateway is accessible
   - Monitor for reconnection attempts in logs

### Debug Logging

Enable debug logging to troubleshoot issues:

```python
import logging
logging.getLogger('integrations.discord_connector').setLevel(logging.DEBUG)
```

## Security Considerations

- **Bot Token Security**: Keep bot tokens secure and never commit them to version control
- **Webhook Validation**: Use webhook secrets to validate incoming webhooks
- **Permission Principle**: Grant minimum necessary permissions to the bot
- **Data Privacy**: Be mindful of message content and user privacy
- **Audit Logging**: Monitor bot activity and API usage

## API Reference

### DiscordConnector

Main connector class for Discord integration.

#### Methods

- `authenticate()`: Authenticate with Discord API
- `start_real_time_ingestion()`: Start real-time message processing
- `stop_real_time_ingestion()`: Stop real-time processing
- `fetch_historical_messages(cursor, limit)`: Fetch historical messages
- `handle_webhook(payload)`: Process webhook events
- `health_check()`: Check connector health

### DiscordConnectorFactory

Factory for creating Discord connectors.

#### Methods

- `create_connector(config, event_bus, rate_limiter, token_manager)`: Create connector
- `create_from_env(event_bus, rate_limiter, token_manager)`: Create from environment
- `validate_config(config)`: Validate configuration

## Examples

See the `tests/test_discord_integration.py` file for comprehensive examples of using the Discord connector in various scenarios.