"""
MESH Integrations Package

This package provides the base connector framework and utilities for
integrating with various messaging platforms.
"""

from .base_connector import (
    BaseConnector,
    ConnectorHealth,
    ConnectorStatus,
    RawMessage,
    TokenInfo,
    AuthenticationError,
    RateLimitError,
    CircuitBreakerError
)

from .connector_manager import (
    ConnectorManager,
    ConnectorConfig,
    ConnectorStats,
    ManagerStatus
)

from .rate_limiter import (
    RateLimiter,
    CircuitBreaker,
    ExponentialBackoff,
    AdaptiveRateLimiter,
    RateLimitConfig,
    CircuitBreakerConfig,
    CircuitBreakerState
)

from .token_manager import (
    TokenManager,
    TokenStorage,
    EncryptedFileTokenStorage,
    RedisTokenStorage,
    TokenRefreshHandler,
    OAuth2RefreshHandler,
    TokenStorageError,
    TokenRefreshError
)

__all__ = [
    # Base connector
    'BaseConnector',
    'ConnectorHealth',
    'ConnectorStatus',
    'RawMessage',
    'TokenInfo',
    'AuthenticationError',
    'RateLimitError',
    'CircuitBreakerError',

    # Connector manager
    'ConnectorManager',
    'ConnectorConfig',
    'ConnectorStats',
    'ManagerStatus',

    # Rate limiting
    'RateLimiter',
    'CircuitBreaker',
    'ExponentialBackoff',
    'AdaptiveRateLimiter',
    'RateLimitConfig',
    'CircuitBreakerConfig',
    'CircuitBreakerState',

    # Token management
    'TokenManager',
    'TokenStorage',
    'EncryptedFileTokenStorage',
    'RedisTokenStorage',
    'TokenRefreshHandler',
    'OAuth2RefreshHandler',
    'TokenStorageError',
    'TokenRefreshError',
]
