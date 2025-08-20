"""
Factory for creating Matrix bridge hub instances.
"""

import logging
from typing import Dict, Any, Optional

from .matrix_bridge_hub import MatrixBridgeHub
from services.event_bus import EventBus
from config.config import settings

logger = logging.getLogger(__name__)


class MatrixBridgeHubFactory:
    """
    Factory for creating and configuring Matrix bridge hub instances.

    Handles configuration validation and provides pre-configured instances
    based on environment settings.
    """

    @staticmethod
    def create_hub(
        config: Optional[Dict[str, Any]] = None,
        event_bus: Optional[EventBus] = None
    ) -> MatrixBridgeHub:
        """
        Create a Matrix bridge hub instance.

        Args:
            config: Optional configuration override
            event_bus: Event bus instance for message publishing

        Returns:
            Configured MatrixBridgeHub instance
        """
        try:
            # Use provided config or build from settings
            if config is None:
                config = MatrixBridgeHubFactory._build_config_from_settings()

            # Validate required configuration
            MatrixBridgeHubFactory._validate_config(config)

            # Create hub instance
            hub = MatrixBridgeHub(config, event_bus=event_bus)

            logger.info("Matrix bridge hub created successfully")
            return hub

        except Exception as e:
            logger.error(f"Failed to create Matrix bridge hub: {e}")
            raise

    @staticmethod
    def _build_config_from_settings() -> Dict[str, Any]:
        """Build configuration from application settings."""
        config = {
            'homeserver_url': settings.MATRIX_HOMESERVER_URL,
            'access_token': settings.MATRIX_ACCESS_TOKEN,
            'user_id': settings.MATRIX_USER_ID,
            'device_id': settings.MATRIX_DEVICE_ID,
            'bridges': {}
        }

        # WhatsApp bridge configuration
        if settings.WHATSAPP_BRIDGE_ENABLED:
            config['bridges']['whatsapp'] = {
                'enabled': True,
                'executable_path': settings.WHATSAPP_BRIDGE_EXECUTABLE,
                'config_path': settings.WHATSAPP_BRIDGE_CONFIG_PATH,
                'database_path': settings.WHATSAPP_BRIDGE_DATABASE_PATH,
                'environment': {
                    'LOG_LEVEL': 'INFO' if not settings.DEBUG else 'DEBUG'
                }
            }

        # Instagram bridge configuration
        if settings.INSTAGRAM_BRIDGE_ENABLED:
            config['bridges']['instagram'] = {
                'enabled': True,
                'executable_path': settings.INSTAGRAM_BRIDGE_EXECUTABLE,
                'config_path': settings.INSTAGRAM_BRIDGE_CONFIG_PATH,
                'database_path': settings.INSTAGRAM_BRIDGE_DATABASE_PATH,
                'environment': {
                    'LOG_LEVEL': 'INFO' if not settings.DEBUG else 'DEBUG',
                    'META_MODE': 'instagram'
                }
            }

        return config

    @staticmethod
    def _validate_config(config: Dict[str, Any]) -> None:
        """Validate Matrix bridge hub configuration."""
        required_fields = ['homeserver_url', 'access_token', 'user_id']

        for field in required_fields:
            if not config.get(field):
                raise ValueError(
                    f"Missing required Matrix configuration: {field}")

        # Validate homeserver URL format
        homeserver_url = config['homeserver_url']
        if not (homeserver_url.startswith('http://') or homeserver_url.startswith('https://')):
            raise ValueError(
                "Matrix homeserver URL must start with http:// or https://")

        # Validate user ID format
        user_id = config['user_id']
        if not (user_id.startswith('@') and ':' in user_id):
            raise ValueError(
                "Matrix user ID must be in format @username:domain")

        # Validate bridge configurations
        bridges = config.get('bridges', {})
        for bridge_name, bridge_config in bridges.items():
            if bridge_config.get('enabled', False):
                if not bridge_config.get('executable_path'):
                    raise ValueError(
                        f"Missing executable_path for {bridge_name} bridge")
                if not bridge_config.get('config_path'):
                    raise ValueError(
                        f"Missing config_path for {bridge_name} bridge")
                if not bridge_config.get('database_path'):
                    raise ValueError(
                        f"Missing database_path for {bridge_name} bridge")

    @staticmethod
    def create_whatsapp_only_hub(
        homeserver_url: str,
        access_token: str,
        user_id: str,
        event_bus: Optional[EventBus] = None
    ) -> MatrixBridgeHub:
        """
        Create a Matrix bridge hub with only WhatsApp bridge enabled.

        Args:
            homeserver_url: Matrix homeserver URL
            access_token: Matrix access token
            user_id: Matrix user ID
            event_bus: Event bus instance

        Returns:
            MatrixBridgeHub with WhatsApp bridge only
        """
        config = {
            'homeserver_url': homeserver_url,
            'access_token': access_token,
            'user_id': user_id,
            'device_id': 'MESH_WHATSAPP_BRIDGE',
            'bridges': {
                'whatsapp': {
                    'enabled': True,
                    'executable_path': 'mautrix-whatsapp',
                    'config_path': './bridges/whatsapp/config.yaml',
                    'database_path': './bridges/whatsapp/whatsapp.db',
                    'environment': {'LOG_LEVEL': 'INFO'}
                }
            }
        }

        return MatrixBridgeHubFactory.create_hub(config, event_bus)

    @staticmethod
    def create_instagram_only_hub(
        homeserver_url: str,
        access_token: str,
        user_id: str,
        event_bus: Optional[EventBus] = None
    ) -> MatrixBridgeHub:
        """
        Create a Matrix bridge hub with only Instagram bridge enabled.

        Args:
            homeserver_url: Matrix homeserver URL
            access_token: Matrix access token
            user_id: Matrix user ID
            event_bus: Event bus instance

        Returns:
            MatrixBridgeHub with Instagram bridge only
        """
        config = {
            'homeserver_url': homeserver_url,
            'access_token': access_token,
            'user_id': user_id,
            'device_id': 'MESH_INSTAGRAM_BRIDGE',
            'bridges': {
                'instagram': {
                    'enabled': True,
                    'executable_path': 'mautrix-meta',
                    'config_path': './bridges/instagram/config.yaml',
                    'database_path': './bridges/instagram/meta.db',
                    'environment': {
                        'LOG_LEVEL': 'INFO',
                        'META_MODE': 'instagram'
                    }
                }
            }
        }

        return MatrixBridgeHubFactory.create_hub(config, event_bus)

    @staticmethod
    def create_multi_bridge_hub(
        homeserver_url: str,
        access_token: str,
        user_id: str,
        enabled_bridges: list = None,
        event_bus: Optional[EventBus] = None
    ) -> MatrixBridgeHub:
        """
        Create a Matrix bridge hub with multiple bridges enabled.

        Args:
            homeserver_url: Matrix homeserver URL
            access_token: Matrix access token
            user_id: Matrix user ID
            enabled_bridges: List of bridge names to enable (default: all)
            event_bus: Event bus instance

        Returns:
            MatrixBridgeHub with specified bridges
        """
        if enabled_bridges is None:
            enabled_bridges = ['whatsapp', 'instagram']

        config = {
            'homeserver_url': homeserver_url,
            'access_token': access_token,
            'user_id': user_id,
            'device_id': 'MESH_MULTI_BRIDGE',
            'bridges': {}
        }

        # Add WhatsApp bridge if requested
        if 'whatsapp' in enabled_bridges:
            config['bridges']['whatsapp'] = {
                'enabled': True,
                'executable_path': 'mautrix-whatsapp',
                'config_path': './bridges/whatsapp/config.yaml',
                'database_path': './bridges/whatsapp/whatsapp.db',
                'environment': {'LOG_LEVEL': 'INFO'}
            }

        # Add Instagram bridge if requested
        if 'instagram' in enabled_bridges:
            config['bridges']['instagram'] = {
                'enabled': True,
                'executable_path': 'mautrix-meta',
                'config_path': './bridges/instagram/config.yaml',
                'database_path': './bridges/instagram/meta.db',
                'environment': {
                    'LOG_LEVEL': 'INFO',
                    'META_MODE': 'instagram'
                }
            }

        return MatrixBridgeHubFactory.create_hub(config, event_bus)
