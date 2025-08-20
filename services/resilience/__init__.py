"""
Resilience and error handling services for the MESH system.

This package provides Dead Letter Queue (DLQ), circuit breaker patterns,
retry logic, and graceful degradation strategies.
"""

from .dead_letter_queue import (
    DeadLetterQueue,
    DLQMessage,
    DLQError,
    DLQMessageStatus,
    get_dead_letter_queue,
    initialize_dlq,
    dlq_context
)
from .circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerState,
    CircuitBreakerConfig,
    CircuitBreakerError,
    CircuitBreakerManager,
    get_circuit_breaker,
    circuit_breaker_context,
    circuit_breaker
)
from .retry_handler import (
    RetryHandler,
    RetryConfig,
    RetryError,
    RetryPolicy,
    JitterType,
    RetryManager,
    get_retry_handler,
    retry_context,
    retry,
    NETWORK_RETRY_CONFIG,
    DATABASE_RETRY_CONFIG,
    API_RETRY_CONFIG
)
from .graceful_degradation import (
    GracefulDegradationManager,
    ServiceStatus,
    DegradationLevel,
    ServiceHealth,
    FallbackConfig,
    get_graceful_degradation_manager,
    graceful_degradation_context,
    with_graceful_degradation
)

__all__ = [
    # Dead Letter Queue
    'DeadLetterQueue',
    'DLQMessage',
    'DLQError',
    'DLQMessageStatus',
    'get_dead_letter_queue',
    'initialize_dlq',
    'dlq_context',

    # Circuit Breaker
    'CircuitBreaker',
    'CircuitBreakerState',
    'CircuitBreakerConfig',
    'CircuitBreakerError',
    'CircuitBreakerManager',
    'get_circuit_breaker',
    'circuit_breaker_context',
    'circuit_breaker',

    # Retry Handler
    'RetryHandler',
    'RetryConfig',
    'RetryError',
    'RetryPolicy',
    'JitterType',
    'RetryManager',
    'get_retry_handler',
    'retry_context',
    'retry',
    'NETWORK_RETRY_CONFIG',
    'DATABASE_RETRY_CONFIG',
    'API_RETRY_CONFIG',

    # Graceful Degradation
    'GracefulDegradationManager',
    'ServiceStatus',
    'DegradationLevel',
    'ServiceHealth',
    'FallbackConfig',
    'get_graceful_degradation_manager',
    'graceful_degradation_context',
    'with_graceful_degradation'
]
