"""
Gmail connector factory for creating and configuring Gmail connectors.

This module provides factory functions for creating Gmail connectors
with proper configuration and dependencies.
"""

import logging
from typing import Dict, Any, Optional

from .gmail_connector import GmailConnector
from .rate_limiter import RateLimiter, RateLimitConfig
from .token_manager import TokenManager
from services.event_bus import EventBus
from config.config import settings

logger = logging.getLogger(__name__)


class GmailConnectorFactory:
    """Factory for creating Gmail connectors with proper configuration."""

    @staticmethod
    def create_connector(
        event_bus: Optional[EventBus] = None,
        token_manager: Optional[TokenManager] = None,
        rate_limiter: Optional[RateLimiter] = None,
        custom_config: Optional[Dict[str, Any]] = None
    ) -> GmailConnector:
        """
        Create a Gmail connector with configuration from settings.

        Args:
            event_bus: Event bus for publishing messages
            token_manager: Token manager for OAuth tokens
            rate_limiter: Rate limiter for API calls
            custom_config: Custom configuration overrides

        Returns:
            Configured GmailConnector instance
        """
        try:
            logger.info("Creating Gmail connector")

            # Build configuration from settings
            config = {
                'scopes': settings.GMAIL_SCOPES.split() if settings.GMAIL_SCOPES else [],
                'credentials_file': settings.GMAIL_CREDENTIALS_FILE,
                'token_file': settings.GMAIL_TOKEN_FILE,
                'webhook_endpoint': settings.GMAIL_WEBHOOK_ENDPOINT,
                'webhook_secret': settings.GMAIL_WEBHOOK_SECRET,
                'topic_name': settings.GMAIL_TOPIC_NAME,
                'max_results': settings.GMAIL_MAX_RESULTS,
                'include_spam_trash': settings.GMAIL_INCLUDE_SPAM_TRASH
            }

            # Apply custom configuration overrides
            if custom_config:
                config.update(custom_config)

            # Create rate limiter if not provided
            if not rate_limiter:
                rate_limit_config = RateLimitConfig(
                    # Gmail API rate limits (250 per minute = ~4 per second)
                    requests_per_second=4.0,
                    burst_size=25,
                    window_size_seconds=60
                )
                rate_limiter = RateLimiter(rate_limit_config)

            # Create connector
            connector = GmailConnector(
                config=config,
                event_bus=event_bus,
                rate_limiter=rate_limiter,
                token_manager=token_manager
            )

            logger.info("Gmail connector created successfully")
            return connector

        except Exception as e:
            logger.error(f"Failed to create Gmail connector: {e}")
            raise

    @staticmethod
    def validate_config() -> bool:
        """
        Validate Gmail configuration.

        Returns:
            True if configuration is valid, False otherwise
        """
        try:
            # Check required configuration
            if not settings.GMAIL_CREDENTIALS_FILE:
                logger.error("GMAIL_CREDENTIALS_FILE is required")
                return False

            # Check if credentials file exists
            import os
            if not os.path.exists(settings.GMAIL_CREDENTIALS_FILE):
                logger.error(
                    f"Gmail credentials file not found: {settings.GMAIL_CREDENTIALS_FILE}")
                return False

            logger.info("Gmail configuration validation passed")
            return True

        except Exception as e:
            logger.error(f"Gmail configuration validation failed: {e}")
            return False

    @staticmethod
    def create_test_connector() -> GmailConnector:
        """
        Create a Gmail connector for testing purposes.

        Returns:
            GmailConnector configured for testing
        """
        test_config = {
            'scopes': ['https://www.googleapis.com/auth/gmail.readonly'],
            'credentials_file': 'test_credentials.json',
            'token_file': 'test_token.json',
            'webhook_endpoint': '/webhooks/gmail',
            'max_results': 50,
            'include_spam_trash': False
        }

        return GmailConnector(config=test_config)
