"""
Discord connector factory for creating and configuring Discord connectors.
"""

import logging
from typing import Dict, Any, Optional

from .discord_connector import DiscordConnector
from .rate_limiter import RateLimiter
from .token_manager import TokenManager
from services.event_bus import EventBus

logger = logging.getLogger(__name__)


class DiscordConnectorFactory:
    """Factory for creating Discord connectors."""

    @staticmethod
    def create_connector(
        config: Dict[str, Any],
        event_bus: Optional[EventBus] = None,
        rate_limiter: Optional[RateLimiter] = None,
        token_manager: Optional[TokenManager] = None
    ) -> DiscordConnector:
        """Create a Discord connector with the given configuration."""
        try:
            logger.info("Creating Discord connector")

            # Validate required configuration
            required_fields = ['bot_token']
            missing_fields = [
                field for field in required_fields if not config.get(field)]

            if missing_fields:
                raise ValueError(
                    f"Missing required Discord configuration fields: {missing_fields}")

            # Create rate limiter if not provided
            if not rate_limiter:
                from .rate_limiter import RateLimitConfig
                rate_config = RateLimitConfig(
                    requests_per_second=50.0,  # Discord global rate limit
                    burst_size=10,
                    window_size_seconds=1
                )
                rate_limiter = RateLimiter(rate_config)

            # Create connector
            connector = DiscordConnector(
                config=config,
                event_bus=event_bus,
                rate_limiter=rate_limiter,
                token_manager=token_manager
            )

            logger.info("Discord connector created successfully")
            return connector

        except Exception as e:
            logger.error(f"Failed to create Discord connector: {e}")
            raise

    @staticmethod
    def create_from_env(
        event_bus: Optional[EventBus] = None,
        rate_limiter: Optional[RateLimiter] = None,
        token_manager: Optional[TokenManager] = None
    ) -> DiscordConnector:
        """Create a Discord connector from environment variables."""
        import os

        try:
            logger.info(
                "Creating Discord connector from environment variables")

            # Parse monitored guilds
            monitored_guilds_str = os.getenv('DISCORD_MONITORED_GUILDS', '')
            monitored_guilds = []
            if monitored_guilds_str:
                monitored_guilds = [guild.strip()
                                    for guild in monitored_guilds_str.split(',')]

            config = {
                'bot_token': os.getenv('DISCORD_BOT_TOKEN'),
                'client_id': os.getenv('DISCORD_CLIENT_ID'),
                'client_secret': os.getenv('DISCORD_CLIENT_SECRET'),
                'webhook_secret': os.getenv('DISCORD_WEBHOOK_SECRET'),
                'intents': int(os.getenv('DISCORD_INTENTS', '513')),
                'max_results': int(os.getenv('DISCORD_MAX_RESULTS', '100')),
                'include_dm_channels': os.getenv('DISCORD_INCLUDE_DM_CHANNELS', 'true').lower() == 'true',
                'monitored_guilds': monitored_guilds,
                'presence': {
                    'status': os.getenv('DISCORD_STATUS', 'online'),
                    'afk': False,
                    'activities': [],
                    'since': None
                }
            }

            return DiscordConnectorFactory.create_connector(
                config=config,
                event_bus=event_bus,
                rate_limiter=rate_limiter,
                token_manager=token_manager
            )

        except Exception as e:
            logger.error(
                f"Failed to create Discord connector from environment: {e}")
            raise


def create_discord_connector(
    config: Dict[str, Any],
    event_bus: Optional[EventBus] = None,
    rate_limiter: Optional[RateLimiter] = None,
    token_manager: Optional[TokenManager] = None
) -> DiscordConnector:
    """Convenience function to create a Discord connector."""
    return DiscordConnectorFactory.create_connector(
        config=config,
        event_bus=event_bus,
        rate_limiter=rate_limiter,
        token_manager=token_manager
    )


def create_discord_connector_from_env(
    event_bus: Optional[EventBus] = None,
    rate_limiter: Optional[RateLimiter] = None,
    token_manager: Optional[TokenManager] = None
) -> DiscordConnector:
    """Convenience function to create a Discord connector from environment variables."""
    return DiscordConnectorFactory.create_from_env(
        event_bus=event_bus,
        rate_limiter=rate_limiter,
        token_manager=token_manager
    )
