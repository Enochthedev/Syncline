"""
Gmail-specific token refresh handler for OAuth 2.0 credentials.

This module provides Gmail-specific token management and refresh capabilities
that integrate with the base token management system.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from .base_connector import TokenInfo
from .token_manager import TokenRefreshHandler, TokenRefreshError

logger = logging.getLogger(__name__)


class GmailTokenRefreshHandler(TokenRefreshHandler):
    """
    Gmail-specific token refresh handler for OAuth 2.0 credentials.

    Handles Google OAuth 2.0 token refresh using the Google Auth library
    and integrates with the MESH token management system.
    """

    def __init__(
        self,
        credentials_file: str,
        scopes: list[str],
        redirect_uri: Optional[str] = None
    ):
        """
        Initialize Gmail token refresh handler.

        Args:
            credentials_file: Path to Google OAuth 2.0 credentials file
            scopes: List of OAuth scopes required
            redirect_uri: Optional redirect URI for OAuth flow
        """
        self.credentials_file = credentials_file
        self.scopes = scopes
        self.redirect_uri = redirect_uri

    async def refresh_token(self, platform: str, current_token: TokenInfo) -> TokenInfo:
        """
        Refresh Gmail OAuth 2.0 token.

        Args:
            platform: Platform identifier (should be 'gmail')
            current_token: Current token information

        Returns:
            New token information with refreshed credentials

        Raises:
            TokenRefreshError: If token refresh fails
        """
        try:
            logger.info(f"Refreshing Gmail token for platform: {platform}")

            # Convert TokenInfo to Google Credentials
            google_creds = self._token_info_to_credentials(current_token)

            if not google_creds.refresh_token:
                raise TokenRefreshError("No refresh token available for Gmail")

            # Refresh the credentials
            google_creds.refresh(Request())

            # Convert back to TokenInfo
            new_token = self._credentials_to_token_info(google_creds)

            logger.info("Gmail token refreshed successfully")
            return new_token

        except Exception as e:
            logger.error(f"Failed to refresh Gmail token: {e}")
            raise TokenRefreshError(f"Gmail token refresh failed: {e}")

    def _token_info_to_credentials(self, token_info: TokenInfo) -> Credentials:
        """
        Convert TokenInfo to Google Credentials object.

        Args:
            token_info: MESH token information

        Returns:
            Google OAuth 2.0 credentials
        """
        # Extract Google-specific metadata
        metadata = token_info.metadata or {}

        return Credentials(
            token=token_info.access_token,
            refresh_token=token_info.refresh_token,
            token_uri=metadata.get(
                'token_uri', 'https://oauth2.googleapis.com/token'),
            client_id=metadata.get('client_id'),
            client_secret=metadata.get('client_secret'),
            scopes=self.scopes,
            expiry=token_info.expires_at
        )

    def _credentials_to_token_info(self, credentials: Credentials) -> TokenInfo:
        """
        Convert Google Credentials to TokenInfo.

        Args:
            credentials: Google OAuth 2.0 credentials

        Returns:
            MESH token information
        """
        return TokenInfo(
            access_token=credentials.token,
            refresh_token=credentials.refresh_token,
            expires_at=credentials.expiry,
            token_type="Bearer",
            scope=" ".join(credentials.scopes) if credentials.scopes else None,
            metadata={
                'token_uri': credentials.token_uri,
                'client_id': credentials.client_id,
                'client_secret': credentials.client_secret,
                'scopes': credentials.scopes
            }
        )

    async def create_initial_token(
        self,
        client_id: str,
        client_secret: str,
        authorization_code: str
    ) -> TokenInfo:
        """
        Create initial token from authorization code.

        Args:
            client_id: OAuth 2.0 client ID
            client_secret: OAuth 2.0 client secret
            authorization_code: Authorization code from OAuth flow

        Returns:
            Initial token information

        Raises:
            TokenRefreshError: If token creation fails
        """
        try:
            logger.info("Creating initial Gmail token from authorization code")

            # Create flow from client secrets
            flow = InstalledAppFlow.from_client_secrets_file(
                self.credentials_file,
                scopes=self.scopes
            )

            if self.redirect_uri:
                flow.redirect_uri = self.redirect_uri

            # Exchange authorization code for credentials
            credentials = flow.fetch_token(code=authorization_code)

            # Convert to TokenInfo
            google_creds = Credentials(
                token=credentials['access_token'],
                refresh_token=credentials.get('refresh_token'),
                token_uri=credentials.get(
                    'token_uri', 'https://oauth2.googleapis.com/token'),
                client_id=flow.client_config['client_id'],
                client_secret=flow.client_config['client_secret'],
                scopes=self.scopes
            )

            token_info = self._credentials_to_token_info(google_creds)

            logger.info("Initial Gmail token created successfully")
            return token_info

        except Exception as e:
            logger.error(f"Failed to create initial Gmail token: {e}")
            raise TokenRefreshError(f"Initial token creation failed: {e}")

    async def revoke_token(self, token_info: TokenInfo) -> bool:
        """
        Revoke Gmail OAuth 2.0 token.

        Args:
            token_info: Token information to revoke

        Returns:
            True if revocation was successful
        """
        try:
            logger.info("Revoking Gmail token")

            google_creds = self._token_info_to_credentials(token_info)

            # Revoke the credentials
            google_creds.revoke(Request())

            logger.info("Gmail token revoked successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to revoke Gmail token: {e}")
            return False

    def get_authorization_url(self) -> tuple[str, str]:
        """
        Get authorization URL for OAuth 2.0 flow.

        Returns:
            Tuple of (authorization_url, state)
        """
        try:
            flow = InstalledAppFlow.from_client_secrets_file(
                self.credentials_file,
                scopes=self.scopes
            )

            if self.redirect_uri:
                flow.redirect_uri = self.redirect_uri

            auth_url, state = flow.authorization_url(
                access_type='offline',
                include_granted_scopes='true'
            )

            return auth_url, state

        except Exception as e:
            logger.error(f"Failed to get Gmail authorization URL: {e}")
            raise TokenRefreshError(
                f"Authorization URL generation failed: {e}")

    def validate_token_scopes(self, token_info: TokenInfo) -> bool:
        """
        Validate that token has required scopes.

        Args:
            token_info: Token information to validate

        Returns:
            True if token has all required scopes
        """
        if not token_info.scope:
            return False

        token_scopes = set(token_info.scope.split())
        required_scopes = set(self.scopes)

        return required_scopes.issubset(token_scopes)

    def get_token_info(self, token_info: TokenInfo) -> Dict[str, Any]:
        """
        Get detailed token information for debugging.

        Args:
            token_info: Token information

        Returns:
            Dictionary with token details (sensitive data excluded)
        """
        return {
            'platform': 'gmail',
            'has_access_token': bool(token_info.access_token),
            'has_refresh_token': bool(token_info.refresh_token),
            'expires_at': token_info.expires_at.isoformat() if token_info.expires_at else None,
            'is_expired': token_info.is_expired(),
            'expires_soon': token_info.expires_soon(),
            'scopes': token_info.scope.split() if token_info.scope else [],
            'token_type': token_info.token_type,
            'metadata_keys': list(token_info.metadata.keys()) if token_info.metadata else []
        }


class GmailTokenValidator:
    """
    Utility class for validating Gmail tokens and credentials.
    """

    @staticmethod
    def validate_credentials_file(credentials_file: str) -> bool:
        """
        Validate that credentials file exists and has required structure.

        Args:
            credentials_file: Path to credentials file

        Returns:
            True if credentials file is valid
        """
        try:
            import json
            import os

            if not os.path.exists(credentials_file):
                logger.error(f"Credentials file not found: {credentials_file}")
                return False

            with open(credentials_file, 'r') as f:
                creds_data = json.load(f)

            # Check for required fields
            if 'installed' not in creds_data and 'web' not in creds_data:
                logger.error("Invalid credentials file format")
                return False

            client_config = creds_data.get(
                'installed') or creds_data.get('web')
            required_fields = ['client_id',
                               'client_secret', 'auth_uri', 'token_uri']

            for field in required_fields:
                if field not in client_config:
                    logger.error(
                        f"Missing required field in credentials: {field}")
                    return False

            return True

        except Exception as e:
            logger.error(f"Error validating credentials file: {e}")
            return False

    @staticmethod
    def validate_scopes(scopes: list[str]) -> bool:
        """
        Validate that scopes are valid Gmail scopes.

        Args:
            scopes: List of OAuth scopes

        Returns:
            True if all scopes are valid
        """
        valid_gmail_scopes = {
            'https://www.googleapis.com/auth/gmail.readonly',
            'https://www.googleapis.com/auth/gmail.modify',
            'https://www.googleapis.com/auth/gmail.compose',
            'https://www.googleapis.com/auth/gmail.send',
            'https://www.googleapis.com/auth/gmail.labels',
            'https://www.googleapis.com/auth/gmail.metadata',
            'https://www.googleapis.com/auth/gmail.settings.basic',
            'https://www.googleapis.com/auth/gmail.settings.sharing'
        }

        for scope in scopes:
            if scope not in valid_gmail_scopes:
                logger.warning(f"Unknown Gmail scope: {scope}")
                # Don't return False for unknown scopes, just warn

        return True
