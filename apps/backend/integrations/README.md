# Platform Integration Framework

This module provides the base framework for connecting to external communication platforms.

## Components

### BaseConnector (`base_connector.py`)

Abstract base class for all platform connectors with:

- **Connection Lifecycle Management**: Connect, disconnect, and refresh token operations
- **Health Monitoring**: Real-time health checks with status tracking
- **Circuit Breaker Pattern**: Automatic fault tolerance with configurable thresholds
- **Rate Limiting Support**: Built-in rate limit checking
- **Standardized Error Handling**: Custom exceptions for different failure scenarios

#### Key Features

- **Status Tracking**: Monitors connector state (CONNECTED, DISCONNECTED, FAILED, etc.)
- **Circuit Breaker**: Opens after consecutive failures, attempts recovery after timeout
- **Health Checks**: Provides detailed health information including error history
- **Thread-Safe**: Uses asyncio locks for concurrent operations

#### Usage Example

```python
from integrations import BaseConnector, ConnectorStatus

class MyPlatformConnector(BaseConnector):
    @property
    def platform_name(self) -> str:
        return "myplatform"
    
    async def _connect(self) -> None:
        # Platform-specific connection logic
        pass
    
    async def _disconnect(self) -> None:
        # Platform-specific disconnection logic
        pass
    
    async def _refresh_token(self) -> Dict[str, Any]:
        # Platform-specific token refresh
        return new_credentials
    
    async def _check_health(self) -> Dict[str, Any]:
        # Platform-specific health check
        return {"status": "ok"}

# Use the connector
connector = MyPlatformConnector(
    connection_id=uuid4(),
    credentials={"access_token": "..."},
    rate_limit_per_minute=60,
    circuit_breaker_threshold=5,
    circuit_breaker_timeout=60,
)

await connector.connect()
health = await connector.health_check()
await connector.disconnect()
```

### TokenManager (`token_manager.py`)

Secure credential storage and management with:

- **AES-256 Encryption**: Credentials encrypted at rest using Fernet
- **Automatic Token Refresh**: Detects expiring tokens and triggers refresh
- **Thread-Safe Operations**: Safe for concurrent access
- **Database Integration**: Stores encrypted credentials in PostgreSQL

#### Key Features

- **Encryption**: Uses PBKDF2HMAC to derive encryption keys from application secret
- **Token Lifecycle**: Tracks token expiration and refresh timing
- **Standardized Format**: Creates consistent credential dictionaries
- **Error Handling**: Custom exceptions for encryption and token errors

#### Usage Example

```python
from integrations import TokenManager, create_token_manager

# Create token manager
token_manager = create_token_manager(db_session)

# Store credentials
credentials = token_manager.create_credentials_dict(
    access_token="access_token_here",
    refresh_token="refresh_token_here",
    expires_in=3600,
    scope="read write",
)
await token_manager.store_credentials(connection_id, credentials)

# Retrieve credentials
creds = await token_manager.get_credentials(connection_id)

# Check if refresh needed
if await token_manager.needs_refresh(connection_id):
    # Trigger refresh in connector
    pass

# Update after refresh
await token_manager.update_token(connection_id, new_credentials)
```

### RateLimiter (`rate_limiter.py`)

Token bucket rate limiter with:

- **Multiple Time Windows**: Per-minute, per-hour, and per-day limits
- **Burst Capacity**: Allows short bursts of requests
- **Automatic Token Refill**: Tokens replenish over time
- **Platform-Specific Configs**: Pre-configured limits for each platform

#### Key Features

- **Token Bucket Algorithm**: Smooth rate limiting with burst support
- **Async/Await**: Non-blocking rate limit checks
- **Configurable**: Customize limits per platform
- **State Tracking**: Monitor current rate limit status

#### Usage Example

```python
from integrations import get_rate_limiter, RateLimiter, RateLimitConfig

# Get platform-specific rate limiter
limiter = get_rate_limiter("gmail")

# Check if request can proceed
if await limiter.acquire(wait=False):
    # Make API request
    pass
else:
    # Rate limited, wait or queue request
    pass

# Or wait for token availability
await limiter.acquire(wait=True)  # Blocks until token available

# Check current state
state = await limiter.get_state()
print(f"Tokens available: {state.tokens_available}")
print(f"Requests this minute: {state.requests_this_minute}")
```

#### Platform Rate Limits

Pre-configured limits for:
- **Gmail**: 250 req/min, 1B req/day
- **Slack**: 60 req/min
- **Discord**: 50 req/min
- **WhatsApp**: 80 req/min, 1000 req/hour
- **Twitter**: 15 req/min, 180 req/hour
- **Telegram**: 30 req/min

## Exception Hierarchy

```
Exception
├── ConnectorException (base)
│   ├── ConnectionError
│   ├── AuthenticationError
│   ├── RateLimitError
│   └── CircuitBreakerOpenError
└── TokenManagerError (base)
    ├── EncryptionError
    ├── TokenRefreshError
    └── TokenNotFoundError
```

## Status Enums

### ConnectorStatus
- `DISCONNECTED`: Not connected to platform
- `CONNECTING`: Connection in progress
- `CONNECTED`: Successfully connected
- `RECONNECTING`: Attempting to reconnect
- `FAILED`: Connection failed
- `RATE_LIMITED`: Rate limit exceeded
- `CIRCUIT_OPEN`: Circuit breaker is open

### HealthStatus
- `HEALTHY`: Connector is fully operational
- `DEGRADED`: Connector is operational but with issues
- `UNHEALTHY`: Connector is not operational
- `UNKNOWN`: Health status cannot be determined

## Design Patterns

### Circuit Breaker Pattern

The circuit breaker prevents cascading failures by:
1. **Closed State**: Normal operation, requests pass through
2. **Open State**: After threshold failures, requests are blocked
3. **Half-Open State**: After timeout, allows test requests
4. **Recovery**: Successful requests close the circuit

### Token Bucket Algorithm

Rate limiting uses token bucket:
1. Bucket starts with burst_size tokens
2. Tokens refill at requests_per_minute rate
3. Each request consumes one token
4. When empty, requests wait for refill

### Encryption at Rest

Credentials are encrypted using:
1. PBKDF2HMAC derives key from application secret
2. Fernet (AES-256) encrypts credential JSON
3. Base64 encoding for storage
4. Automatic decryption on retrieval

## Requirements Satisfied

This implementation satisfies the following requirements:

- **Requirement 1.1**: Platform connection interface
- **Requirement 1.2**: Secure credential storage
- **Requirement 1.3**: Automatic token refresh
- **Requirement 2.3**: Rate limiting support
- **Requirement 6.1**: Independent stage testing
- **Requirement 10.1**: Encryption at rest

## Next Steps

To implement a platform connector:

1. Subclass `BaseConnector`
2. Implement abstract methods (`_connect`, `_disconnect`, etc.)
3. Use `TokenManager` for credential storage
4. Use `RateLimiter` for API rate limiting
5. Handle platform-specific errors appropriately

See the Gmail connector implementation for a complete example.
