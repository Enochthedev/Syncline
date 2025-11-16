"""
Platform Integrations Package

This package contains all platform connector implementations for the R.E.M.I backend.

Available Connectors:
- GmailConnector: Gmail integration with OAuth 2.0 and push notifications
- SlackConnector: Slack integration with OAuth 2.0 and webhooks
- DiscordConnector: Discord integration with OAuth 2.0 and gateway
- WhatsAppConnector: WhatsApp integration via Mautrix bridge
- TwitterConnector: Twitter/X integration with OAuth 1.0a/2.0
- TelegramConnector: Telegram integration with Bot API

All connectors inherit from BaseConnector and provide:
- OAuth authentication and token management
- Rate limiting and circuit breaker patterns
- Health monitoring
- Platform-specific API methods
"""

from integrations.base_connector import (
    BaseConnector,
    ConnectorStatus,
    HealthStatus,
    ConnectorHealth,
    ConnectorException,
    ConnectionError,
    AuthenticationError,
    RateLimitError,
    CircuitBreakerOpenError,
)

from integrations.gmail_connector import GmailConnector
from integrations.slack_connector import SlackConnector
from integrations.discord_connector import DiscordConnector
from integrations.whatsapp_connector import WhatsAppConnector
from integrations.twitter_connector import TwitterConnector
from integrations.telegram_connector import TelegramConnector

from integrations.token_manager import TokenManager, create_token_manager
from integrations.rate_limiter import RateLimiter, get_rate_limiter


__all__ = [
    # Base classes
    "BaseConnector",
    "ConnectorStatus",
    "HealthStatus",
    "ConnectorHealth",
    
    # Exceptions
    "ConnectorException",
    "ConnectionError",
    "AuthenticationError",
    "RateLimitError",
    "CircuitBreakerOpenError",
    
    # Platform connectors
    "GmailConnector",
    "SlackConnector",
    "DiscordConnector",
    "WhatsAppConnector",
    "TwitterConnector",
    "TelegramConnector",
    
    # Utilities
    "TokenManager",
    "create_token_manager",
    "RateLimiter",
    "get_rate_limiter",
]
