# MESH Resilience and Error Handling Guide

This guide covers the comprehensive resilience and error handling features implemented in the MESH ingestion system, including Dead Letter Queue (DLQ), circuit breakers, retry handlers, and graceful degradation strategies.

## Overview

The MESH system implements multiple layers of resilience to handle various failure scenarios:

1. **Dead Letter Queue (DLQ)** - Handles failed message processing with retry mechanisms
2. **Circuit Breaker** - Prevents cascading failures by temporarily blocking requests to failing services
3. **Retry Handler** - Implements sophisticated retry logic with exponential backoff
4. **Graceful Degradation** - Provides fallback mechanisms and service health monitoring

## Dead Letter Queue (DLQ)

The DLQ system captures failed messages and provides automatic retry mechanisms with poison message detection.

### Features

- **Automatic Retry**: Failed messages are automatically retried with exponential backoff
- **Poison Message Detection**: Messages that consistently fail are marked as poison
- **Statistics and Monitoring**: Comprehensive metrics for DLQ operations
- **Configurable Retry Policies**: Customizable retry attempts and delays

### Usage

```python
from services.resilience import DeadLetterQueue, get_dead_letter_queue

# Get global DLQ instance
dlq = await get_dead_letter_queue()

# Add a failed message
message_id = await dlq.add_message(
    event={'id': 'event-123', 'data': 'message data'},
    error=Exception("Processing failed"),
    max_retries=3
)

# Start automatic retry processor
async def message_handler(event):
    # Process the event
    return "processed"

await dlq.start_retry_processor(message_handler, check_interval=60.0)

# Get statistics
stats = await dlq.get_statistics()
print(f"Pending messages: {stats['pending_count']}")
```

### Configuration

```python
dlq = DeadLetterQueue(
    dlq_key_prefix="dlq",
    retry_delay_base=60.0,      # Base delay in seconds
    max_retry_delay=3600.0,     # Maximum delay in seconds
    poison_threshold=5          # Poison message threshold
)
```

## Circuit Breaker

Circuit breakers prevent cascading failures by monitoring service health and temporarily blocking requests to failing services.

### States

- **CLOSED**: Normal operation, requests pass through
- **OPEN**: Service is failing, requests are blocked
- **HALF_OPEN**: Testing if service has recovered

### Features

- **Automatic State Transitions**: Based on failure thresholds and recovery timeouts
- **Timeout Protection**: Prevents long-running operations from blocking
- **Statistics Tracking**: Detailed metrics on requests, failures, and state changes
- **Manual Control**: Force open/close or reset circuit breakers

### Usage

```python
from services.resilience import CircuitBreaker, CircuitBreakerConfig, get_circuit_breaker

# Create circuit breaker configuration
config = CircuitBreakerConfig(
    failure_threshold=5,        # Open after 5 failures
    recovery_timeout_seconds=60, # Wait 60s before testing recovery
    success_threshold=3,        # Close after 3 successes in half-open
    timeout_seconds=30.0        # Timeout individual operations
)

# Get circuit breaker
cb = await get_circuit_breaker("my_service", config)

# Use circuit breaker
try:
    result = await cb.call(my_service_function, arg1, arg2)
    print(f"Success: {result}")
except CircuitBreakerError:
    print("Circuit breaker is open - service unavailable")
```

### Decorator Usage

```python
from services.resilience import circuit_breaker

@circuit_breaker("api_service", config)
async def call_external_api():
    # This function is protected by circuit breaker
    return await external_api_call()
```

## Retry Handler

The retry handler implements sophisticated retry logic with multiple backoff strategies and jitter options.

### Features

- **Multiple Backoff Policies**: Exponential, linear, fixed delay, or immediate
- **Jitter Support**: Reduces thundering herd problems
- **Exception Filtering**: Configure retryable vs non-retryable exceptions
- **Timeout Support**: Per-attempt and total timeouts
- **Statistics Tracking**: Detailed retry attempt metrics

### Usage

```python
from services.resilience import RetryHandler, RetryConfig, RetryPolicy, JitterType

# Create retry configuration
config = RetryConfig(
    max_attempts=5,
    initial_delay=1.0,
    max_delay=60.0,
    multiplier=2.0,
    jitter_type=JitterType.FULL,
    policy=RetryPolicy.EXPONENTIAL_BACKOFF,
    retryable_exceptions=(ConnectionError, TimeoutError),
    non_retryable_exceptions=(ValueError, KeyError),
    timeout_per_attempt=30.0,
    total_timeout=300.0
)

# Get retry handler
handler = await get_retry_handler("network_operations", config)

# Execute with retry
try:
    result = await handler.execute(unreliable_function, arg1, arg2)
    print(f"Success: {result}")
except MaxAttemptsExceededError as e:
    print(f"All retry attempts failed: {e.last_exception}")
```

### Predefined Configurations

```python
from services.resilience import NETWORK_RETRY_CONFIG, DATABASE_RETRY_CONFIG, API_RETRY_CONFIG

# Use predefined configurations for common scenarios
network_handler = await get_retry_handler("network", NETWORK_RETRY_CONFIG)
db_handler = await get_retry_handler("database", DATABASE_RETRY_CONFIG)
api_handler = await get_retry_handler("api", API_RETRY_CONFIG)
```

### Decorator Usage

```python
from services.resilience import retry

@retry("database_operations", DATABASE_RETRY_CONFIG)
async def database_query():
    # This function will be retried on failure
    return await db.execute("SELECT * FROM table")
```

## Graceful Degradation

The graceful degradation manager provides fallback mechanisms and service health monitoring to maintain functionality during partial failures.

### Features

- **Service Health Monitoring**: Track service status and degradation levels
- **Fallback Handlers**: Custom fallback implementations for failed services
- **Caching**: Cache successful results for fallback use
- **Automatic Health Checks**: Periodic health monitoring
- **Degradation Levels**: Multiple levels of service degradation

### Usage

```python
from services.resilience import GracefulDegradationManager, get_graceful_degradation_manager

# Get degradation manager
manager = await get_graceful_degradation_manager()

# Register service with fallback
async def fallback_handler(*args, **kwargs):
    return {"status": "degraded", "data": "cached_response"}

await manager.register_service(
    "external_service",
    health_check=lambda: check_service_health(),
    fallback_handler=fallback_handler
)

# Execute with fallback support
result = await manager.execute_with_fallback(
    "external_service",
    primary_function,
    cache_key="operation_123",
    arg1, arg2
)
```

### Service Status Levels

- **HEALTHY**: Service is fully operational
- **DEGRADED**: Service has minor issues but is functional
- **UNHEALTHY**: Service has major issues
- **OFFLINE**: Service is completely unavailable

### Degradation Levels

- **NONE**: Full functionality available
- **MINOR**: Some features disabled
- **MAJOR**: Core features only
- **CRITICAL**: Emergency mode only

## Integration with Existing Components

### Event Bus Integration

The event bus automatically uses the DLQ for failed message processing:

```python
# Failed messages are automatically added to DLQ
# No additional configuration required
```

### Base Connector Integration

Base connectors automatically use circuit breakers and retry handlers:

```python
from integrations.base_connector import BaseConnector

class MyConnector(BaseConnector):
    async def fetch_data(self):
        # _make_request automatically uses circuit breaker and retry logic
        response = await self._make_request("GET", "https://api.example.com/data")
        return await response.json()
```

## Monitoring and Metrics

### Circuit Breaker Metrics

```python
stats = circuit_breaker.get_stats()
print(f"State: {stats.state}")
print(f"Total requests: {stats.total_requests}")
print(f"Failure rate: {stats.failure_rate:.2%}")
print(f"Uptime: {stats.uptime_seconds}s")
```

### Retry Handler Metrics

```python
stats = retry_handler.get_stats()
print(f"Total attempts: {stats.total_attempts}")
print(f"Success rate: {stats.successful_attempts / stats.total_attempts:.2%}")
print(f"Average delay: {stats.total_delay / len(stats.attempts):.2f}s")
```

### DLQ Metrics

```python
stats = await dlq.get_statistics()
print(f"Pending: {stats['pending_count']}")
print(f"Retrying: {stats['retrying_count']}")
print(f"Poison: {stats['poison_count']}")
print(f"Resolved: {stats['resolved_count']}")
```

### Service Health Metrics

```python
health = await manager.get_service_health("my_service")
print(f"Status: {health.status}")
print(f"Degradation level: {health.degradation_level}")
print(f"Error count: {health.error_count}")
print(f"Last error: {health.last_error}")
```

## Best Practices

### Circuit Breaker Configuration

- Set failure thresholds based on expected error rates (typically 5-10 failures)
- Use recovery timeouts that allow services time to recover (30-60 seconds)
- Monitor circuit breaker state changes and alerts

### Retry Configuration

- Use exponential backoff with jitter to avoid thundering herd
- Set reasonable maximum delays (30-60 seconds)
- Configure exception types carefully - don't retry permanent failures
- Set total timeouts to prevent indefinite retries

### DLQ Management

- Monitor poison message rates - high rates indicate systemic issues
- Implement alerting for DLQ queue sizes
- Regularly clean up old resolved messages
- Review poison messages for patterns

### Graceful Degradation

- Implement meaningful fallback responses
- Cache successful results for fallback use
- Monitor service health trends
- Test degradation scenarios regularly

## Error Handling Patterns

### Layered Resilience

Combine multiple resilience patterns for maximum protection:

```python
# Layer 1: Circuit breaker prevents cascading failures
# Layer 2: Retry handler manages transient failures
# Layer 3: Graceful degradation provides fallbacks
# Layer 4: DLQ captures permanent failures

result = await circuit_breaker.call(
    lambda: retry_handler.execute(
        lambda: degradation_manager.execute_with_fallback(
            "service_name",
            primary_function,
            cache_key="operation_key"
        )
    )
)
```

### Exception Classification

```python
# Transient errors - should be retried
TRANSIENT_ERRORS = (
    ConnectionError,
    TimeoutError,
    aiohttp.ClientConnectorError,
    aiohttp.ServerTimeoutError
)

# Permanent errors - should not be retried
PERMANENT_ERRORS = (
    ValueError,
    KeyError,
    AuthenticationError,
    PermissionError
)

# Rate limit errors - special handling
RATE_LIMIT_ERRORS = (
    RateLimitError,
    aiohttp.ClientResponseError  # when status == 429
)
```

## Testing Resilience

### Unit Testing

```python
@pytest.mark.asyncio
async def test_circuit_breaker_opens_on_failures():
    cb = CircuitBreaker(CircuitBreakerConfig(failure_threshold=2), "test")
    
    # Cause failures
    for _ in range(2):
        with pytest.raises(ValueError):
            await cb.call(lambda: exec('raise ValueError("error")'))
    
    # Circuit breaker should be open
    assert cb.state == CircuitBreakerState.OPEN
```

### Integration Testing

```python
@pytest.mark.asyncio
async def test_full_resilience_stack():
    # Test all resilience components working together
    # See tests/test_resilience_integration.py for examples
```

### Chaos Engineering

```python
@pytest.mark.asyncio
async def test_chaos_resilience():
    # Introduce random failures and verify system resilience
    # See tests/test_resilience_chaos_engineering.py for examples
```

## Configuration Examples

### Production Configuration

```python
# Circuit breaker for external APIs
API_CIRCUIT_BREAKER_CONFIG = CircuitBreakerConfig(
    failure_threshold=5,
    recovery_timeout_seconds=60,
    success_threshold=3,
    timeout_seconds=30.0
)

# Retry for network operations
NETWORK_RETRY_CONFIG = RetryConfig(
    max_attempts=5,
    initial_delay=1.0,
    max_delay=30.0,
    multiplier=2.0,
    jitter_type=JitterType.FULL,
    policy=RetryPolicy.EXPONENTIAL_BACKOFF,
    retryable_exceptions=(ConnectionError, TimeoutError),
    timeout_per_attempt=30.0,
    total_timeout=300.0
)

# DLQ configuration
DLQ_CONFIG = {
    'retry_delay_base': 60.0,
    'max_retry_delay': 3600.0,
    'poison_threshold': 5
}
```

### Development Configuration

```python
# Faster timeouts for development
DEV_CIRCUIT_BREAKER_CONFIG = CircuitBreakerConfig(
    failure_threshold=3,
    recovery_timeout_seconds=10,
    success_threshold=2,
    timeout_seconds=10.0
)

DEV_RETRY_CONFIG = RetryConfig(
    max_attempts=3,
    initial_delay=0.5,
    max_delay=5.0,
    multiplier=2.0,
    jitter_type=JitterType.NONE,  # Predictable for testing
    total_timeout=30.0
)
```

## Troubleshooting

### Common Issues

1. **Circuit Breaker Stuck Open**
   - Check if underlying service has recovered
   - Verify recovery timeout is appropriate
   - Consider manual reset if needed

2. **Excessive Retries**
   - Review retry configuration
   - Check if errors are actually retryable
   - Monitor total timeout settings

3. **DLQ Queue Growing**
   - Investigate poison message patterns
   - Check if retry handlers are working
   - Review error types and frequencies

4. **Degraded Performance**
   - Monitor fallback usage rates
   - Check cache hit rates
   - Review service health trends

### Debugging

Enable detailed logging for resilience components:

```python
import logging

# Enable debug logging for resilience
logging.getLogger('services.resilience').setLevel(logging.DEBUG)
```

### Metrics and Alerting

Set up monitoring for:
- Circuit breaker state changes
- High retry rates
- DLQ queue sizes
- Service degradation events
- Fallback usage rates

## Conclusion

The MESH resilience system provides comprehensive error handling and fault tolerance through multiple layers of protection. By combining DLQ, circuit breakers, retry handlers, and graceful degradation, the system can handle various failure scenarios while maintaining functionality and preventing cascading failures.

Regular monitoring, testing, and tuning of resilience configurations ensure optimal system reliability and performance.