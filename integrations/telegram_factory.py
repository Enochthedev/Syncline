"""
Telegram connector factory for creating and configuring Telegram connectors.

This module provides factory functions for creating Telegram connectors with
proper configuration, authentication, and integration with the event bus system.
"""

import logging
from typing import Dict, Any, Optional

from .telegram_connector import TelegramConnector
from .rate_limiter import RateLimiter
from services.event_bus import EventBus
from services.resilience.circuit_breaker import CircuitBreaker
from .token_manager import TokenManager

logger = logging.getLogger(__name__)


class TelegramConnectorFactory:
    """Factory for creating Telegram connectors."""

    @staticmethod
    async def create_connector(
        config: Dict[str, Any],
        event_bus: Optional[EventBus] = None,
        rate_limiter: Optional[RateLimiter] = None,
        circuit_breaker: Optional[CircuitBreaker] = None,
        token_manager: Optional[TokenManager] = None
    ) -> TelegramConnector:
        """
        Create a Telegram connector with the given configuration.

        Args:
            config: Telegram connector configuration
            event_bus: Event bus for message publishing
            rate_limiter: Rate limiter for API calls
            circuit_breaker: Circuit breaker for fault tolerance
            token_manager: Token manager for secure token storage

        Returns:
            Configured Telegram connector

        Raises:
            ValueError: If required configuration is missing
        """
        try:
            logger.info("Creating Telegram connector")

            # Validate required configuration
            required_fields = ['bot_token']
            missing_fields = [
                field for field in required_fields if not config.get(field)]

            if missing_fields:
                raise ValueError(
                    f"Missing required Telegram configuration: {missing_fields}")

            # Create rate limiter if not provided
            if not rate_limiter:
                rate_limiter = await TelegramConnectorFactory._create_rate_limiter(config)

            # Create circuit breaker if not provided
            if not circuit_breaker:
                circuit_breaker = await TelegramConnectorFactory._create_circuit_breaker(config)

            # Create connector
            connector = TelegramConnector(
                config=config,
                event_bus=event_bus,
                rate_limiter=rate_limiter,
                circuit_breaker=circuit_breaker,
                token_manager=token_manager
            )

            logger.info("Telegram connector created successfully")
            return connector

        except Exception as e:
            logger.error(f"Failed to create Telegram connector: {e}")
            raise

    @staticmethod
    async def _create_rate_limiter(config: Dict[str, Any]) -> RateLimiter:
        """Create rate limiter for Telegram API."""
        try:
            # Telegram Bot API rate limits:
            # - 30 messages per second to the same chat
            # - 20 messages per minute to the same group
            # - 1 message per second to different chats
            rate_limit_config = {
                'requests_per_second': config.get('rate_limit_requests_per_second', 20),
                'burst_size': config.get('rate_limit_burst_size', 30),
                'window_size': config.get('rate_limit_window_size', 60)
            }

            rate_limiter = RateLimiter(
                name="telegram_api",
                **rate_limit_config
            )

            logger.debug("Created Telegram rate limiter")
            return rate_limiter

        except Exception as e:
            logger.error(f"Failed to create Telegram rate limiter: {e}")
            raise

    @staticmethod
    async def _create_circuit_breaker(config: Dict[str, Any]) -> CircuitBreaker:
        """Create circuit breaker for Telegram API."""
        try:
            circuit_breaker_config = {
                'failure_threshold': config.get('circuit_breaker_failure_threshold', 5),
                'recovery_timeout': config.get('circuit_breaker_recovery_timeout', 60),
                'expected_exception': Exception
            }

            circuit_breaker = CircuitBreaker(
                name="telegram_api",
                **circuit_breaker_config
            )

            logger.debug("Created Telegram circuit breaker")
            return circuit_breaker

        except Exception as e:
            logger.error(f"Failed to create Telegram circuit breaker: {e}")
            raise

    @staticmethod
    def validate_config(config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and normalize Telegram connector configuration.

        Args:
            config: Raw configuration dictionary

        Returns:
            Validated and normalized configuration

        Raises:
            ValueError: If configuration is invalid
        """
        try:
            # Required fields
            if not config.get('bot_token'):
                raise ValueError("Telegram bot_token is required")

            # Normalize configuration
            normalized_config = {
                # Required
                'bot_token': config['bot_token'],

                # Optional webhook configuration
                'webhook_url': config.get('webhook_url'),
                'webhook_secret': config.get('webhook_secret'),
                'webhook_path': config.get('webhook_path', '/webhooks/telegram'),

                # Bot configuration
                'allowed_updates': config.get('allowed_updates', [
                    'message', 'edited_message', 'channel_post', 'edited_channel_post'
                ]),
                'drop_pending_updates': config.get('drop_pending_updates', True),

                # API configuration
                'max_connections': config.get('max_connections', 40),
                'read_timeout': config.get('read_timeout', 30),
                'write_timeout': config.get('write_timeout', 30),
                'connect_timeout': config.get('connect_timeout', 30),

                # Message fetching configuration
                'max_messages_per_request': config.get('max_messages_per_request', 100),
                'include_private_chats': config.get('include_private_chats', True),
                'include_group_chats': config.get('include_group_chats', True),
                'include_channels': config.get('include_channels', True),

                # Rate limiting
                'rate_limit_requests_per_second': config.get('rate_limit_requests_per_second', 20),
                'rate_limit_burst_size': config.get('rate_limit_burst_size', 30),
                'rate_limit_window_size': config.get('rate_limit_window_size', 60),

                # Circuit breaker
                'circuit_breaker_failure_threshold': config.get('circuit_breaker_failure_threshold', 5),
                'circuit_breaker_recovery_timeout': config.get('circuit_breaker_recovery_timeout', 60)
            }

            # Validate webhook configuration
            if normalized_config['webhook_url']:
                if not normalized_config['webhook_url'].startswith(('http://', 'https://')):
                    raise ValueError(
                        "Telegram webhook_url must be a valid HTTP/HTTPS URL")

            # Validate timeouts
            for timeout_field in ['read_timeout', 'write_timeout', 'connect_timeout']:
                if normalized_config[timeout_field] <= 0:
                    raise ValueError(
                        f"Telegram {timeout_field} must be positive")

            # Validate rate limiting
            if normalized_config['rate_limit_requests_per_second'] <= 0:
                raise ValueError(
                    "Telegram rate_limit_requests_per_second must be positive")

            logger.debug("Telegram configuration validated successfully")
            return normalized_config

        except Exception as e:
            logger.error(f"Telegram configuration validation failed: {e}")
            raise


async def create_telegram_connector(
    config: Dict[str, Any],
    event_bus: Optional[EventBus] = None,
    **kwargs
) -> TelegramConnector:
    """
    Convenience function to create a Telegram connector.

    Args:
        config: Telegram connector configuration
        event_bus: Event bus for message publishing
        **kwargs: Additional arguments for connector creation

    Returns:
        Configured Telegram connector
    """
    # Validate configuration
    validated_config = TelegramConnectorFactory.validate_config(config)

    # Create connector
    return await TelegramConnectorFactory.create_connector(
        config=validated_config,
        event_bus=event_bus,
        **kwargs
    )
