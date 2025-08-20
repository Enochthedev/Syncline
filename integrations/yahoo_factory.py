"""
Yahoo Mail connector factory for MESH ingestion system.
"""

import logging
from typing import Dict, Any, Optional

from .yahoo_connector import YahooConnector, YahooCredentials
from .base_connector import BaseConnector
from services.event_bus import EventBus
from config.config import Settings

logger = logging.getLogger(__name__)


class YahooConnectorFactory:
    """Factory for creating Yahoo Mail connectors."""

    def __init__(self, event_bus: EventBus, settings: Settings):
        self.event_bus = event_bus
        self.settings = settings

    async def create_connector(self, credentials: Dict[str, Any]) -> Optional[YahooConnector]:
        """
        Create a Yahoo Mail connector with the provided credentials.

        Args:
            credentials: Dictionary containing Yahoo Mail credentials
                - email: Yahoo email address
                - app_password: Yahoo app-specific password
                - imap_server: IMAP server (optional, defaults to imap.mail.yahoo.com)
                - imap_port: IMAP port (optional, defaults to 993)

        Returns:
            YahooConnector instance if successful, None otherwise
        """
        try:
            # Validate required credentials
            required_fields = ["email", "app_password"]
            for field in required_fields:
                if field not in credentials:
                    logger.error(f"Missing required Yahoo credential: {field}")
                    return None

            # Create credentials object
            yahoo_creds = YahooCredentials(
                email=credentials["email"],
                app_password=credentials["app_password"],
                imap_server=credentials.get(
                    "imap_server", "imap.mail.yahoo.com"),
                imap_port=credentials.get("imap_port", 993)
            )

            # Create connector
            connector = YahooConnector(
                yahoo_creds, self.event_bus, self.settings)

            # Test authentication
            auth_success = await connector.authenticate(credentials)
            if not auth_success:
                logger.error("Yahoo Mail authentication failed")
                return None

            logger.info(
                f"Yahoo Mail connector created successfully for {yahoo_creds.email}")
            return connector

        except Exception as e:
            logger.error(f"Failed to create Yahoo Mail connector: {e}")
            return None

    def get_required_credentials(self) -> Dict[str, str]:
        """Get the required credential fields for Yahoo Mail."""
        return {
            "email": "Yahoo email address",
            "app_password": "Yahoo app-specific password (not regular password)",
            "imap_server": "IMAP server (optional, defaults to imap.mail.yahoo.com)",
            "imap_port": "IMAP port (optional, defaults to 993)"
        }

    def get_setup_instructions(self) -> str:
        """Get setup instructions for Yahoo Mail integration."""
        return """
        Yahoo Mail Setup Instructions:
        
        1. Enable 2-factor authentication on your Yahoo account
        2. Generate an app-specific password:
           - Go to Yahoo Account Security settings
           - Click "Generate app password"
           - Select "Other app" and enter "MESH System"
           - Copy the generated password
        3. Use your Yahoo email and the app password (not your regular password)
        
        Note: Yahoo Mail uses IMAP polling instead of real-time webhooks.
        Messages will be checked every 30 seconds by default.
        """
