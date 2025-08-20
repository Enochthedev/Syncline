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

# Platform connectors
from .gmail_connector import GmailConnector
from .slack_connector import SlackConnector
from .discord_connector import DiscordConnector
from .twitter_connector import TwitterConnector
from .telegram_connector import TelegramConnector
from .yahoo_connector import YahooConnector

# Matrix bridge hub
from .matrix_bridge_hub import MatrixBridgeHub, BridgeManager, MatrixAuthManager

# WhatsApp integration
from .whatsapp_integration_service import WhatsAppIntegrationService, WhatsAppPreferences, SyncTier

# Connector factories
from .gmail_factory import GmailConnectorFactory
from .slack_factory import SlackConnectorFactory
from .discord_factory import DiscordConnectorFactory
from .twitter_factory import TwitterConnectorFactory
from .telegram_factory import TelegramConnectorFactory
from .linkedin_factory import LinkedInConnectorFactory
from .yahoo_factory import YahooConnectorFactory

# Experimental connectors
from .experimental import (
    ExperimentalConnector,
    ExperimentalFramework,
    ExperimentalStatus,
    ExperimentalCapabilities,
    TikTokConnector,
    SnapchatConnector,
    UnsupportedFeatureError,
    APILimitationError
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

    # Platform connectors
    'GmailConnector',
    'SlackConnector',
    'DiscordConnector',
    'TwitterConnector',
    'TelegramConnector',
    'YahooConnector',

    # Matrix bridge hub
    'MatrixBridgeHub',
    'BridgeManager',
    'MatrixAuthManager',

    # WhatsApp integration
    'WhatsAppIntegrationService',
    'WhatsAppPreferences',
    'SyncTier',

    # Connector factories
    'GmailConnectorFactory',
    'SlackConnectorFactory',
    'DiscordConnectorFactory',
    'TwitterConnectorFactory',
    'TelegramConnectorFactory',
    'LinkedInConnectorFactory',
    'YahooConnectorFactory',

    # Experimental connectors
    'ExperimentalConnector',
    'ExperimentalFramework',
    'ExperimentalStatus',
    'ExperimentalCapabilities',
    'TikTokConnector',
    'SnapchatConnector',
    'UnsupportedFeatureError',
    'APILimitationError',
]
