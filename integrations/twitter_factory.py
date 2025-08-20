"""
Twitter connector factory for creating and configuring Twitter connectors.

This module provides factory functions for creating Twitter connectors
with proper configuration and dependency injection.
"""

import logging
from typing import Dict, Any, Optional

from .twitter_connector import TwitterConnector
from services.event_bus import EventBus
from integrations.rate_limiter import RateLimiter
from integrations.token_manager import TokenManager

logger = logging.getLogger(__name__)


class TwitterConnectorFactory:
    """Factory for creating Twitter connectors."""

    @staticmethod
    def create_connector(
        config: Dict[str, Any],
        event_bus: Optional[EventBus] = None,
        rate_limiter: Optional[RateLimiter] = None,
        token_manager: Optional[TokenManager] = None
    ) -> TwitterConnector:
        """
        Create a Twitter connector with the given configuration.

        Args:
            config: Twitter connector configuration
            event_bus: Event bus for message publishing
            rate_limiter: Rate limiter for API calls
            token_manager: Token manager for OAuth tokens

        Returns:
            Configured Twitter connector
        """
        try:
            logger.info("Creating Twitter connector")

            # Validate required configuration
            required_fields = ['client_id', 'client_secret']
            missing_fields = [
                field for field in required_fields if not config.get(field)]

            if missing_fields:
                raise ValueError(
                    f"Missing required Twitter configuration: {missing_fields}")

            # Create rate limiter if not provided
            if not rate_limiter:
                rate_limiter = TwitterConnectorFactory._create_rate_limiter(
                    config)

            # Create connector
            connector = TwitterConnector(
                config=config,
                event_bus=event_bus,
                rate_limiter=rate_limiter,
                token_manager=token_manager
            )

            logger.info("Twitter connector created successfully")
            return connector

        except Exception as e:
            logger.error(f"Failed to create Twitter connector: {e}")
            raise

    @staticmethod
    def _create_rate_limiter(config: Dict[str, Any]) -> RateLimiter:
        """Create a rate limiter for Twitter API calls."""
        # Twitter API v2 rate limits
        # DM events: 300 requests per 15 minutes
        # User lookup: 300 requests per 15 minutes
        # Tweet lookup: 300 requests per 15 minutes

        from integrations.rate_limiter import RateLimitConfig

        # Twitter API v2 rate limits: 300 requests per 15 minutes = 0.33 requests per second
        rate_limit_config = RateLimitConfig(
            requests_per_second=config.get(
                'rate_limit_requests_per_second', 0.33),
            burst_size=config.get('rate_limit_burst', 10),
            window_size_seconds=config.get(
                'rate_limit_window', 900)  # 15 minutes
        )

        return RateLimiter(config=rate_limit_config)

    @staticmethod
    def create_test_connector(
        access_token: Optional[str] = None,
        bearer_token: Optional[str] = None
    ) -> TwitterConnector:
        """
        Create a Twitter connector for testing purposes.

        Args:
            access_token: OAuth access token for testing
            bearer_token: Bearer token for testing

        Returns:
            Test Twitter connector
        """
        test_config = {
            'client_id': 'test_client_id',
            'client_secret': 'test_client_secret',
            'api_key': 'test_api_key',
            'api_secret': 'test_api_secret',
            'bearer_token': bearer_token or 'test_bearer_token',
            'access_token': access_token,
            'webhook_secret': 'test_webhook_secret',
            'max_results': 50,
            'rate_limit_requests': 100,
            'rate_limit_window': 300  # 5 minutes for testing
        }

        return TwitterConnectorFactory.create_connector(test_config)

    @staticmethod
    def validate_config(config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and normalize Twitter connector configuration.

        Args:
            config: Raw configuration dictionary

        Returns:
            Validated and normalized configuration

        Raises:
            ValueError: If configuration is invalid
        """
        validated_config = config.copy()

        # Required fields
        required_fields = ['client_id', 'client_secret']
        for field in required_fields:
            if not validated_config.get(field):
                raise ValueError(f"Missing required field: {field}")

        # Optional fields with defaults
        defaults = {
            'scopes': ['dm.read', 'dm.write', 'tweet.read', 'users.read', 'offline.access'],
            'redirect_uri': 'http://localhost:8000/twitter/oauth/callback',
            'webhook_endpoint': '/webhooks/twitter',
            'environment_name': 'development',
            'max_results': 100,
            'include_referenced_tweets': True,
            'rate_limit_requests': 300,
            'rate_limit_window': 900,
            'rate_limit_burst': 10
        }

        for key, default_value in defaults.items():
            if key not in validated_config:
                validated_config[key] = default_value

        # Validate scopes
        valid_scopes = {
            'dm.read', 'dm.write', 'tweet.read', 'tweet.write',
            'users.read', 'follows.read', 'follows.write',
            'offline.access', 'space.read', 'mute.read', 'mute.write',
            'like.read', 'like.write', 'list.read', 'list.write'
        }

        invalid_scopes = set(validated_config['scopes']) - valid_scopes
        if invalid_scopes:
            logger.warning(
                f"Invalid Twitter scopes detected: {invalid_scopes}")

        # Validate numeric fields
        numeric_fields = ['max_results', 'rate_limit_requests',
                          'rate_limit_window', 'rate_limit_burst']
        for field in numeric_fields:
            if field in validated_config:
                try:
                    validated_config[field] = int(validated_config[field])
                    if validated_config[field] <= 0:
                        raise ValueError(f"{field} must be positive")
                except (ValueError, TypeError):
                    raise ValueError(
                        f"Invalid {field}: must be a positive integer")

        # Validate max_results limits
        if validated_config['max_results'] > 100:
            logger.warning("max_results > 100 may hit Twitter API limits")
            validated_config['max_results'] = 100

        return validated_config


def create_twitter_connector(
    config: Dict[str, Any],
    event_bus: Optional[EventBus] = None,
    rate_limiter: Optional[RateLimiter] = None,
    token_manager: Optional[TokenManager] = None
) -> TwitterConnector:
    """
    Convenience function to create a Twitter connector.

    Args:
        config: Twitter connector configuration
        event_bus: Event bus for message publishing
        rate_limiter: Rate limiter for API calls
        token_manager: Token manager for OAuth tokens

    Returns:
        Configured Twitter connector
    """
    return TwitterConnectorFactory.create_connector(
        config=config,
        event_bus=event_bus,
        rate_limiter=rate_limiter,
        token_manager=token_manager
    )
