"""
Factory for creating and configuring Gmail connector instances.

This module provides factory functions and utilities for creating
properly configured Gmail connector instances with all dependencies.
"""

import logging
from typing import Dict, Any, Optional

from config.config import settings
from services.event_bus import get_event_bus
from .gmail_connector import GmailConnector
from .gmail_token_handler import GmailTokenRefreshHandler, GmailTokenValidator
from .token_manager import TokenManager, EncryptedFileTokenStorage
from .rate_limiter import RateLimiter, CircuitBreaker, RateLimitConfig, CircuitBreakerConfig
from .connector_manager import ConnectorConfig

logger = logging.getLogger(__name__)


async def create_gmail_connector(
    config: Optional[Dict[str, Any]] = None,
    token_manager: Optional[TokenManager] = None,
    event_bus=None
) -> GmailConnector:
    """
    Create a fully configured Gmail connector instance.

    Args:
        config: Optional configuration override
        token_manager: Optional token manager instance
        event_bus: Optional event bus instance

    Returns:
        Configured Gmail connector instance
    """
    # Use default configuration if not provided
    if config is None:
        config = get_default_gmail_config()

    # Validate configuration
    if not validate_gmail_config(config):
        raise ValueError("Invalid Gmail configuration")

    # Get event bus if not provided
    if event_bus is None:
        event_bus = await get_event_bus()

    # Create rate limiter
    rate_limiter = RateLimiter(RateLimitConfig(
        requests_per_second=config.get('rate_limit_rps', 10.0),
        burst_size=config.get('rate_limit_burst', 20),
        window_size_seconds=config.get('rate_limit_window', 60)
    ))

    # Create circuit breaker
    circuit_breaker = CircuitBreaker(CircuitBreakerConfig(
        failure_threshold=config.get('circuit_breaker_threshold', 5),
        recovery_timeout_seconds=config.get('circuit_breaker_timeout', 60),
        success_threshold=config.get('circuit_breaker_success', 3)
    ))

    # Create Gmail connector
    connector = GmailConnector(
        config=config,
        event_bus=event_bus,
        rate_limiter=rate_limiter,
        circuit_breaker=circuit_breaker,
        token_manager=token_manager
    )

    logger.info("Gmail connector created successfully")
    return connector


def get_default_gmail_config() -> Dict[str, Any]:
    """
    Get default Gmail connector configuration from settings.

    Returns:
        Default configuration dictionary
    """
    return {
        'scopes': settings.GMAIL_SCOPES.split(),
        'credentials_file': settings.GMAIL_CREDENTIALS_FILE,
        'token_file': settings.GMAIL_TOKEN_FILE,
        'webhook_endpoint': settings.GMAIL_WEBHOOK_ENDPOINT,
        'webhook_secret': settings.GMAIL_WEBHOOK_SECRET,
        'topic_name': settings.GMAIL_TOPIC_NAME,
        'max_results': settings.GMAIL_MAX_RESULTS,
        'include_spam_trash': settings.GMAIL_INCLUDE_SPAM_TRASH,

        # Rate limiting configuration
        'rate_limit_rps': 10.0,  # Gmail API allows 250 quota units per user per second
        'rate_limit_burst': 20,
        'rate_limit_window': 60,

        # Circuit breaker configuration
        'circuit_breaker_threshold': 5,
        'circuit_breaker_timeout': 60,
        'circuit_breaker_success': 3,

        # Health check configuration
        'health_check_interval': 60,
        'restart_on_failure': True,
        'max_restart_attempts': 3,
        'restart_delay': 30
    }


def validate_gmail_config(config: Dict[str, Any]) -> bool:
    """
    Validate Gmail connector configuration.

    Args:
        config: Configuration dictionary to validate

    Returns:
        True if configuration is valid
    """
    try:
        # Check required fields
        required_fields = ['scopes', 'credentials_file']
        for field in required_fields:
            if field not in config:
                logger.error(f"Missing required Gmail config field: {field}")
                return False

        # Validate scopes
        scopes = config['scopes']
        if not isinstance(scopes, list) or not scopes:
            logger.error("Gmail scopes must be a non-empty list")
            return False

        if not GmailTokenValidator.validate_scopes(scopes):
            logger.error("Invalid Gmail scopes")
            return False

        # Validate credentials file
        credentials_file = config['credentials_file']
        if not GmailTokenValidator.validate_credentials_file(credentials_file):
            logger.error("Invalid Gmail credentials file")
            return False

        # Validate numeric configurations
        numeric_fields = {
            'max_results': (1, 500),
            'rate_limit_rps': (0.1, 100.0),
            'rate_limit_burst': (1, 1000),
            'circuit_breaker_threshold': (1, 100),
            'circuit_breaker_timeout': (1, 3600),
            'health_check_interval': (10, 3600)
        }

        for field, (min_val, max_val) in numeric_fields.items():
            if field in config:
                value = config[field]
                if not isinstance(value, (int, float)) or not (min_val <= value <= max_val):
                    logger.error(
                        f"Invalid Gmail config value for {field}: {value}")
                    return False

        logger.info("Gmail configuration validation passed")
        return True

    except Exception as e:
        logger.error(f"Error validating Gmail configuration: {e}")
        return False


def create_gmail_token_manager(
    storage_dir: str = ".tokens",
    encryption_key: Optional[str] = None
) -> TokenManager:
    """
    Create a token manager configured for Gmail.

    Args:
        storage_dir: Directory for storing encrypted tokens
        encryption_key: Optional encryption key

    Returns:
        Configured token manager
    """
    # Create encrypted file storage
    storage = EncryptedFileTokenStorage(
        storage_dir=storage_dir,
        encryption_key=encryption_key
    )

    # Create token manager
    token_manager = TokenManager(storage=storage)

    # Register Gmail token refresh handler
    gmail_config = get_default_gmail_config()
    refresh_handler = GmailTokenRefreshHandler(
        credentials_file=gmail_config['credentials_file'],
        scopes=gmail_config['scopes']
    )

    token_manager.register_refresh_handler('gmail', refresh_handler)

    logger.info("Gmail token manager created successfully")
    return token_manager


def create_gmail_connector_config() -> ConnectorConfig:
    """
    Create connector configuration for Gmail.

    Returns:
        Connector configuration for use with ConnectorManager
    """
    gmail_config = get_default_gmail_config()

    return ConnectorConfig(
        platform='gmail',
        enabled=True,
        rate_limit=RateLimitConfig(
            requests_per_second=gmail_config['rate_limit_rps'],
            burst_size=gmail_config['rate_limit_burst'],
            window_size_seconds=gmail_config['rate_limit_window']
        ),
        circuit_breaker=CircuitBreakerConfig(
            failure_threshold=gmail_config['circuit_breaker_threshold'],
            recovery_timeout_seconds=gmail_config['circuit_breaker_timeout'],
            success_threshold=gmail_config['circuit_breaker_success']
        ),
        health_check_interval=gmail_config['health_check_interval'],
        restart_on_failure=gmail_config['restart_on_failure'],
        max_restart_attempts=gmail_config['max_restart_attempts'],
        restart_delay=gmail_config['restart_delay'],
        config=gmail_config
    )


async def setup_gmail_integration(
    connector_manager=None,
    token_manager: Optional[TokenManager] = None
) -> GmailConnector:
    """
    Set up complete Gmail integration with connector manager.

    Args:
        connector_manager: Optional connector manager instance
        token_manager: Optional token manager instance

    Returns:
        Configured and registered Gmail connector
    """
    try:
        logger.info("Setting up Gmail integration")

        # Create token manager if not provided
        if token_manager is None:
            token_manager = create_gmail_token_manager()

        # Create Gmail connector
        gmail_connector = await create_gmail_connector(
            token_manager=token_manager
        )

        # Register with connector manager if provided
        if connector_manager:
            connector_config = create_gmail_connector_config()
            await connector_manager.register_connector(
                gmail_connector,
                connector_config
            )
            logger.info("Gmail connector registered with connector manager")

        logger.info("Gmail integration setup completed successfully")
        return gmail_connector

    except Exception as e:
        logger.error(f"Failed to setup Gmail integration: {e}")
        raise


def get_gmail_webhook_config() -> Dict[str, Any]:
    """
    Get Gmail webhook configuration for web server setup.

    Returns:
        Webhook configuration dictionary
    """
    return {
        'endpoint': settings.GMAIL_WEBHOOK_ENDPOINT,
        'secret': settings.GMAIL_WEBHOOK_SECRET,
        'topic_name': settings.GMAIL_TOPIC_NAME,
        'methods': ['POST'],
        'content_type': 'application/json'
    }


def create_gmail_test_config() -> Dict[str, Any]:
    """
    Create Gmail configuration for testing.

    Returns:
        Test configuration dictionary
    """
    config = get_default_gmail_config()

    # Override with test-specific settings
    config.update({
        'credentials_file': 'tests/fixtures/test_credentials.json',
        'token_file': 'tests/fixtures/test_token.json',
        'webhook_secret': 'test_secret',
        'topic_name': 'projects/test-project/topics/gmail-test',
        'max_results': 10,
        'rate_limit_rps': 100.0,  # Higher rate for testing
        'circuit_breaker_threshold': 10,
        'health_check_interval': 10
    })

    return config
