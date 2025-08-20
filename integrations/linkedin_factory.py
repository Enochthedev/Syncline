"""
LinkedIn connector factory for Matrix bridge integration.

This module provides factory functions for creating and configuring
LinkedIn connectors via the Matrix bridge hub.
"""

import logging
from typing import Dict, Any, Optional

from .matrix_bridge_hub.hub import MatrixBridgeHub
from .matrix_bridge_hub.types import BridgeType, BridgeConfig, AuthMethod
from services.event_bus import EventBus

logger = logging.getLogger(__name__)


class LinkedInConnectorFactory:
    """Factory for creating LinkedIn connectors via Matrix bridge."""

    @staticmethod
    def create_linkedin_connector(
        config: Dict[str, Any],
        event_bus: Optional[EventBus] = None
    ) -> MatrixBridgeHub:
        """
        Create a LinkedIn connector using Matrix bridge hub.

        Args:
            config: LinkedIn connector configuration
            event_bus: Event bus for message publishing

        Returns:
            Configured MatrixBridgeHub with LinkedIn bridge
        """
        try:
            # Extract LinkedIn-specific configuration
            linkedin_config = config.get('linkedin', {})

            # Build Matrix bridge hub configuration
            hub_config = {
                'homeserver_url': config.get('homeserver_url', 'https://matrix.org'),
                'access_token': config.get('access_token'),
                'user_id': config.get('user_id'),
                'device_id': config.get('device_id', 'MESH_LINKEDIN_HUB'),
                'bridges': {
                    'linkedin': {
                        'enabled': linkedin_config.get('enabled', True),
                        'executable_path': linkedin_config.get(
                            'executable_path', 'mautrix-linkedin'
                        ),
                        'config_path': linkedin_config.get(
                            'config_path', './bridges/linkedin/config.yaml'
                        ),
                        'database_path': linkedin_config.get(
                            'database_path', './bridges/linkedin/linkedin.db'
                        ),
                        'environment': linkedin_config.get('environment', {}),
                        'extra_args': linkedin_config.get('extra_args', [])
                    }
                }
            }

            # Create Matrix bridge hub
            hub = MatrixBridgeHub(hub_config, event_bus=event_bus)

            logger.info("LinkedIn connector created via Matrix bridge hub")
            return hub

        except Exception as e:
            logger.error(f"Failed to create LinkedIn connector: {e}")
            raise

    @staticmethod
    def create_linkedin_bridge_config(
        homeserver_url: str,
        access_token: str,
        user_id: str,
        linkedin_config: Dict[str, Any]
    ) -> BridgeConfig:
        """
        Create LinkedIn bridge configuration.

        Args:
            homeserver_url: Matrix homeserver URL
            access_token: Matrix access token
            user_id: Matrix user ID
            linkedin_config: LinkedIn-specific configuration

        Returns:
            BridgeConfig for LinkedIn
        """
        return BridgeConfig(
            bridge_type=BridgeType.LINKEDIN,
            bridge_name='mautrix-linkedin',
            executable_path=linkedin_config.get(
                'executable_path', 'mautrix-linkedin'
            ),
            config_path=linkedin_config.get(
                'config_path', './bridges/linkedin/config.yaml'
            ),
            database_path=linkedin_config.get(
                'database_path', './bridges/linkedin/linkedin.db'
            ),
            homeserver_url=homeserver_url,
            access_token=access_token,
            user_id=user_id,
            device_id=linkedin_config.get('device_id', 'MESH_LINKEDIN'),
            enabled=linkedin_config.get('enabled', True),
            auto_restart=linkedin_config.get('auto_restart', True),
            restart_delay=linkedin_config.get('restart_delay', 5),
            max_restart_attempts=linkedin_config.get(
                'max_restart_attempts', 3),
            environment=linkedin_config.get('environment', {}),
            extra_args=linkedin_config.get('extra_args', []),
            auth_method=AuthMethod.OAUTH
        )

    @staticmethod
    def get_default_linkedin_config() -> Dict[str, Any]:
        """
        Get default LinkedIn connector configuration.

        Returns:
            Default configuration dictionary
        """
        return {
            'enabled': True,
            'executable_path': 'mautrix-linkedin',
            'config_path': './bridges/linkedin/config.yaml',
            'database_path': './bridges/linkedin/linkedin.db',
            'auto_restart': True,
            'restart_delay': 5,
            'max_restart_attempts': 3,
            'environment': {
                'LINKEDIN_LOG_LEVEL': 'INFO'
            },
            'extra_args': [],
            'professional_features': {
                'extract_job_titles': True,
                'extract_company_info': True,
                'extract_industry_context': True,
                'track_professional_relationships': True,
                'identify_business_opportunities': True
            },
            'rate_limiting': {
                'messages_per_hour': 100,
                'api_calls_per_minute': 20
            },
            'oauth_config': {
                'client_id': None,  # To be provided by user
                'client_secret': None,  # To be provided by user
                'redirect_uri': 'http://localhost:8000/linkedin/oauth/callback',
                'scope': ['r_messaging', 'w_messaging', 'r_basicprofile', 'r_contactinfo']
            }
        }

    @staticmethod
    def validate_linkedin_config(config: Dict[str, Any]) -> bool:
        """
        Validate LinkedIn connector configuration.

        Args:
            config: Configuration to validate

        Returns:
            True if configuration is valid

        Raises:
            ValueError: If configuration is invalid
        """
        required_fields = ['homeserver_url', 'access_token', 'user_id']

        for field in required_fields:
            if not config.get(field):
                raise ValueError(f"Required field missing: {field}")

        linkedin_config = config.get('linkedin', {})

        # Validate OAuth configuration if provided
        oauth_config = linkedin_config.get('oauth_config', {})
        if oauth_config:
            if oauth_config.get('client_id') and not oauth_config.get('client_secret'):
                raise ValueError(
                    "LinkedIn OAuth client_secret required when client_id is provided")

        # Validate paths
        executable_path = linkedin_config.get('executable_path')
        if executable_path and not isinstance(executable_path, str):
            raise ValueError("executable_path must be a string")

        config_path = linkedin_config.get('config_path')
        if config_path and not isinstance(config_path, str):
            raise ValueError("config_path must be a string")

        return True


def create_linkedin_connector(
    config: Dict[str, Any],
    event_bus: Optional[EventBus] = None
) -> MatrixBridgeHub:
    """
    Convenience function to create LinkedIn connector.

    Args:
        config: LinkedIn connector configuration
        event_bus: Event bus for message publishing

    Returns:
        Configured MatrixBridgeHub with LinkedIn bridge
    """
    return LinkedInConnectorFactory.create_linkedin_connector(config, event_bus)


def get_linkedin_config_template() -> Dict[str, Any]:
    """
    Get LinkedIn configuration template.

    Returns:
        Configuration template with placeholders
    """
    return {
        'homeserver_url': 'https://your-matrix-server.com',
        'access_token': 'your_matrix_access_token',
        'user_id': '@your_user:your-matrix-server.com',
        'device_id': 'MESH_LINKEDIN_HUB',
        'linkedin': LinkedInConnectorFactory.get_default_linkedin_config()
    }
