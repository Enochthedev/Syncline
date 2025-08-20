"""
Slack connector factory for creating and configuring Slack connectors.

This module provides factory functions for creating Slack connectors
with proper configuration and dependencies.
"""

import logging
from typing import Dict, Any, Optional

from .slack_connector import SlackConnector
from .rate_limiter import RateLimiter, RateLimitConfig
from .token_manager import TokenManager
from services.event_bus import EventBus
from config.config import settings

logger = logging.getLogger(__name__)


class SlackConnectorFactory:
    """Factory for creating Slack connectors with proper configuration."""

    @staticmethod
    def create_connector(
        event_bus: Optional[EventBus] = None,
        token_manager: Optional[TokenManager] = None,
        rate_limiter: Optional[RateLimiter] = None,
        custom_config: Optional[Dict[str, Any]] = None
    ) -> SlackConnector:
        """
        Create a Slack connector with configuration from settings.

        Args:
            event_bus: Event bus for publishing messages
            token_manager: Token manager for OAuth tokens
            rate_limiter: Rate limiter for API calls
            custom_config: Custom configuration overrides

        Returns:
            Configured SlackConnector instance
        """
        try:
            logger.info("Creating Slack connector")

            # Build configuration from settings
            config = {
                'client_id': settings.SLACK_CLIENT_ID,
                'client_secret': settings.SLACK_CLIENT_SECRET,
                'signing_secret': settings.SLACK_SIGNING_SECRET,
                'app_token': settings.SLACK_APP_TOKEN,
                'bot_token': settings.SLACK_BOT_TOKEN,
                'user_token': settings.SLACK_USER_TOKEN,
                'scopes': settings.SLACK_SCOPES.split() if settings.SLACK_SCOPES else [],
                'redirect_uri': settings.SLACK_REDIRECT_URI,
                'webhook_endpoint': settings.SLACK_WEBHOOK_ENDPOINT,
                'socket_mode_enabled': settings.SLACK_SOCKET_MODE_ENABLED,
                'events_api_enabled': settings.SLACK_EVENTS_API_ENABLED,
                'max_results': settings.SLACK_MAX_RESULTS,
                'include_private_channels': settings.SLACK_INCLUDE_PRIVATE_CHANNELS,
                'include_direct_messages': settings.SLACK_INCLUDE_DIRECT_MESSAGES
            }

            # Apply custom configuration overrides
            if custom_config:
                config.update(custom_config)

            # Create rate limiter if not provided
            if not rate_limiter:
                rate_limit_config = RateLimitConfig(
                    # Slack API rate limits (50 per minute = ~1 per second)
                    requests_per_second=1.0,
                    burst_size=10,
                    window_size_seconds=60
                )
                rate_limiter = RateLimiter(rate_limit_config)

            # Create connector
            connector = SlackConnector(
                config=config,
                event_bus=event_bus,
                rate_limiter=rate_limiter,
                token_manager=token_manager
            )

            logger.info("Slack connector created successfully")
            return connector

        except Exception as e:
            logger.error(f"Failed to create Slack connector: {e}")
            raise

    @staticmethod
    def validate_config() -> bool:
        """
        Validate Slack configuration.

        Returns:
            True if configuration is valid, False otherwise
        """
        try:
            # Check required configuration
            if not settings.SLACK_CLIENT_ID:
                logger.error("SLACK_CLIENT_ID is required")
                return False

            if not settings.SLACK_CLIENT_SECRET:
                logger.error("SLACK_CLIENT_SECRET is required")
                return False

            # Check if we have at least one authentication method
            has_bot_token = bool(settings.SLACK_BOT_TOKEN)
            has_oauth_config = bool(
                settings.SLACK_CLIENT_ID and settings.SLACK_CLIENT_SECRET)

            if not (has_bot_token or has_oauth_config):
                logger.error(
                    "Either SLACK_BOT_TOKEN or OAuth configuration is required")
                return False

            # Validate Socket Mode configuration
            if settings.SLACK_SOCKET_MODE_ENABLED and not settings.SLACK_APP_TOKEN:
                logger.warning(
                    "Socket Mode enabled but SLACK_APP_TOKEN not provided")

            logger.info("Slack configuration validation passed")
            return True

        except Exception as e:
            logger.error(f"Slack configuration validation failed: {e}")
            return False

    @staticmethod
    def get_oauth_url() -> str:
        """
        Generate OAuth authorization URL for Slack.

        Returns:
            OAuth authorization URL
        """
        from urllib.parse import urlencode

        if not settings.SLACK_CLIENT_ID:
            raise ValueError("SLACK_CLIENT_ID is required for OAuth URL")

        oauth_params = {
            'client_id': settings.SLACK_CLIENT_ID,
            'scope': settings.SLACK_SCOPES,
            'redirect_uri': settings.SLACK_REDIRECT_URI,
            'response_type': 'code'
        }

        return f"https://slack.com/oauth/v2/authorize?{urlencode(oauth_params)}"

    @staticmethod
    def create_test_connector() -> SlackConnector:
        """
        Create a Slack connector for testing purposes.

        Returns:
            SlackConnector configured for testing
        """
        test_config = {
            'client_id': 'test_client_id',
            'client_secret': 'test_client_secret',
            'signing_secret': 'test_signing_secret',
            'app_token': 'xapp-test-token',
            'bot_token': 'xoxb-test-bot-token',
            'scopes': ['channels:history', 'chat:write'],
            'redirect_uri': 'http://localhost:8000/slack/oauth/callback',
            'socket_mode_enabled': False,  # Disable for testing
            'events_api_enabled': True,
            'max_results': 50
        }

        return SlackConnector(config=test_config)
