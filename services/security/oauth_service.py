"""
OAuth Service for Platform Authentication

Handles OAuth 2.0 flows, token management, and secure authentication
for platform connections with CSRF protection and token refresh.
"""

import asyncio
import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Any
from urllib.parse import urlencode, urlparse, parse_qs
import aiohttp

from integrations.token_manager import TokenManager, TokenInfo
from .types import OAuthConfig, OAuthState

logger = logging.getLogger(__name__)


class OAuthService:
    """
    OAuth 2.0 service for secure platform authentication.

    Provides secure OAuth flows with CSRF protection, token management,
    and automatic refresh capabilities.
    """

    def __init__(self, token_manager: TokenManager, redis_client=None):
        self.token_manager = token_manager
        self.redis_client = redis_client
        self._oauth_configs: Dict[str, OAuthConfig] = {}
        self._oauth_states: Dict[str, OAuthState] = {}

        # Initialize platform OAuth configurations
        self._initialize_oauth_configs()

    def _initialize_oauth_configs(self) -> None:
        """Initialize OAuth configurations for supported platforms."""

        self._oauth_configs = {
            "gmail": OAuthConfig(
                client_id="your-gmail-client-id",
                client_secret="your-gmail-client-secret",
                redirect_uri="https://your-app.com/oauth/callback/gmail",
                scopes=[
                    "https://www.googleapis.com/auth/gmail.readonly",
                    "https://www.googleapis.com/auth/contacts.readonly"
                ],
                auth_url="https://accounts.google.com/o/oauth2/auth",
                token_url="https://oauth2.googleapis.com/token",
                revoke_url="https://oauth2.googleapis.com/revoke"
            ),

            "slack": OAuthConfig(
                client_id="your-slack-client-id",
                client_secret="your-slack-client-secret",
                redirect_uri="https://your-app.com/oauth/callback/slack",
                scopes=[
                    "channels:read", "groups:read", "im:read", "mpim:read",
                    "channels:history", "groups:history", "im:history", "mpim:history",
                    "users:read", "users:read.email"
                ],
                auth_url="https://slack.com/oauth/v2/authorize",
                token_url="https://slack.com/api/oauth.v2.access",
                revoke_url="https://slack.com/api/auth.revoke"
            ),

            "discord": OAuthConfig(
                client_id="your-discord-client-id",
                client_secret="your-discord-client-secret",
                redirect_uri="https://your-app.com/oauth/callback/discord",
                scopes=["identify", "guilds",
                        "guilds.members.read", "messages.read"],
                auth_url="https://discord.com/api/oauth2/authorize",
                token_url="https://discord.com/api/oauth2/token",
                revoke_url="https://discord.com/api/oauth2/token/revoke"
            ),

            "twitter": OAuthConfig(
                client_id="your-twitter-client-id",
                client_secret="your-twitter-client-secret",
                redirect_uri="https://your-app.com/oauth/callback/twitter",
                scopes=["tweet.read", "users.read",
                        "dm.read", "offline.access"],
                auth_url="https://twitter.com/i/oauth2/authorize",
                token_url="https://api.twitter.com/2/oauth2/token",
                revoke_url="https://api.twitter.com/2/oauth2/revoke"
            ),

            "linkedin": OAuthConfig(
                client_id="your-linkedin-client-id",
                client_secret="your-linkedin-client-secret",
                redirect_uri="https://your-app.com/oauth/callback/linkedin",
                scopes=["r_liteprofile", "r_emailaddress", "w_member_social"],
                auth_url="https://www.linkedin.com/oauth/v2/authorization",
                token_url="https://www.linkedin.com/oauth/v2/accessToken",
                revoke_url="https://www.linkedin.com/oauth/v2/revoke"
            )
        }

    async def get_platform_oauth_config(self, platform: str) -> Optional[OAuthConfig]:
        """Get OAuth configuration for a platform."""
        return self._oauth_configs.get(platform)

    async def build_authorization_url(
        self,
        oauth_config: OAuthConfig,
        oauth_state: OAuthState
    ) -> str:
        """Build OAuth authorization URL with CSRF protection."""

        params = {
            "client_id": oauth_config.client_id,
            "redirect_uri": oauth_config.redirect_uri,
            "scope": " ".join(oauth_config.scopes),
            "response_type": "code",
            "state": oauth_state.state,
            "access_type": "offline",  # Request refresh token
            "prompt": "consent"  # Force consent to get refresh token
        }

        # Platform-specific parameters
        if oauth_state.platform == "slack":
            params["user_scope"] = "identify,channels:read,groups:read,im:read,mpim:read"
        elif oauth_state.platform == "discord":
            params["permissions"] = "0"  # No special permissions needed
        elif oauth_state.platform == "twitter":
            params["code_challenge"] = self._generate_pkce_challenge()
            params["code_challenge_method"] = "S256"

        return f"{oauth_config.auth_url}?{urlencode(params)}"

    async def store_oauth_state(self, oauth_state: OAuthState) -> None:
        """Store OAuth state for CSRF verification."""

        if self.redis_client:
            # Store in Redis with expiration
            key = f"oauth_state:{oauth_state.state}"
            value = oauth_state.model_dump_json()
            # 10 minute expiration
            await self.redis_client.setex(key, 600, value)
        else:
            # Store in memory (not recommended for production)
            self._oauth_states[oauth_state.state] = oauth_state

    async def verify_oauth_state(
        self,
        state: str,
        user_id: str,
        platform: str
    ) -> Optional[OAuthState]:
        """Verify OAuth state and prevent CSRF attacks."""

        oauth_state = None

        if self.redis_client:
            # Retrieve from Redis
            key = f"oauth_state:{state}"
            value = await self.redis_client.get(key)
            if value:
                oauth_state = OAuthState.model_validate_json(value)
        else:
            # Retrieve from memory
            oauth_state = self._oauth_states.get(state)

        if not oauth_state:
            logger.warning(f"OAuth state not found: {state}")
            return None

        # Verify state parameters
        if (oauth_state.user_id != user_id or
                oauth_state.platform != platform):
            logger.warning(f"OAuth state mismatch: {oauth_state}")
            return None

        # Check expiration (10 minutes)
        if datetime.now(timezone.utc) - oauth_state.created_at > timedelta(minutes=10):
            logger.warning(f"OAuth state expired: {state}")
            await self.cleanup_oauth_state(state)
            return None

        return oauth_state

    async def cleanup_oauth_state(self, state: str) -> None:
        """Clean up OAuth state after use."""

        if self.redis_client:
            key = f"oauth_state:{state}"
            await self.redis_client.delete(key)
        else:
            self._oauth_states.pop(state, None)

    async def exchange_code_for_tokens(
        self,
        platform: str,
        authorization_code: str,
        oauth_state: OAuthState
    ) -> TokenInfo:
        """Exchange authorization code for access and refresh tokens."""

        oauth_config = self._oauth_configs.get(platform)
        if not oauth_config:
            raise ValueError(
                f"OAuth config not found for platform: {platform}")

        async with aiohttp.ClientSession() as session:
            data = {
                "grant_type": "authorization_code",
                "client_id": oauth_config.client_id,
                "client_secret": oauth_config.client_secret,
                "redirect_uri": oauth_config.redirect_uri,
                "code": authorization_code
            }

            # Platform-specific token exchange
            if platform == "slack":
                # Slack uses different parameter names
                # Slack doesn't require this in token exchange
                data.pop("redirect_uri")
            elif platform == "twitter":
                # Twitter requires PKCE
                data["code_verifier"] = oauth_state.metadata.get(
                    "code_verifier")

            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json"
            }

            async with session.post(
                oauth_config.token_url,
                data=data,
                headers=headers
            ) as response:

                if response.status != 200:
                    error_text = await response.text()
                    logger.error(
                        f"Token exchange failed for {platform}: {error_text}")
                    raise Exception(
                        f"Token exchange failed: {response.status}")

                token_data = await response.json()

                # Handle platform-specific token responses
                access_token = token_data.get("access_token")
                refresh_token = token_data.get("refresh_token")
                expires_in = token_data.get("expires_in")
                token_type = token_data.get("token_type", "Bearer")
                scope = token_data.get("scope")

                if not access_token:
                    raise Exception("No access token received")

                # Calculate expiration time
                expires_at = None
                if expires_in:
                    expires_at = datetime.now(
                        timezone.utc) + timedelta(seconds=int(expires_in))

                return TokenInfo(
                    access_token=access_token,
                    refresh_token=refresh_token,
                    expires_at=expires_at,
                    token_type=token_type,
                    scope=scope,
                    metadata={
                        "platform": platform,
                        "user_id": oauth_state.user_id,
                        "obtained_at": datetime.now(timezone.utc).isoformat()
                    }
                )

    async def refresh_access_token(
        self,
        platform: str,
        refresh_token: str
    ) -> TokenInfo:
        """Refresh an expired access token."""

        oauth_config = self._oauth_configs.get(platform)
        if not oauth_config:
            raise ValueError(
                f"OAuth config not found for platform: {platform}")

        async with aiohttp.ClientSession() as session:
            data = {
                "grant_type": "refresh_token",
                "client_id": oauth_config.client_id,
                "client_secret": oauth_config.client_secret,
                "refresh_token": refresh_token
            }

            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json"
            }

            async with session.post(
                oauth_config.token_url,
                data=data,
                headers=headers
            ) as response:

                if response.status != 200:
                    error_text = await response.text()
                    logger.error(
                        f"Token refresh failed for {platform}: {error_text}")
                    raise Exception(f"Token refresh failed: {response.status}")

                token_data = await response.json()

                access_token = token_data.get("access_token")
                new_refresh_token = token_data.get(
                    "refresh_token", refresh_token)
                expires_in = token_data.get("expires_in")
                token_type = token_data.get("token_type", "Bearer")
                scope = token_data.get("scope")

                if not access_token:
                    raise Exception("No access token received in refresh")

                expires_at = None
                if expires_in:
                    expires_at = datetime.now(
                        timezone.utc) + timedelta(seconds=int(expires_in))

                return TokenInfo(
                    access_token=access_token,
                    refresh_token=new_refresh_token,
                    expires_at=expires_at,
                    token_type=token_type,
                    scope=scope,
                    metadata={
                        "platform": platform,
                        "refreshed_at": datetime.now(timezone.utc).isoformat()
                    }
                )

    async def revoke_token(self, platform: str, token: str) -> bool:
        """Revoke an access or refresh token."""

        oauth_config = self._oauth_configs.get(platform)
        if not oauth_config or not oauth_config.revoke_url:
            logger.warning(f"Token revocation not supported for {platform}")
            return False

        try:
            async with aiohttp.ClientSession() as session:
                data = {
                    "token": token,
                    "client_id": oauth_config.client_id,
                    "client_secret": oauth_config.client_secret
                }

                headers = {
                    "Content-Type": "application/x-www-form-urlencoded"
                }

                async with session.post(
                    oauth_config.revoke_url,
                    data=data,
                    headers=headers
                ) as response:

                    # Some platforms return 200, others return 204
                    if response.status in [200, 204]:
                        logger.info(
                            f"Token revoked successfully for {platform}")
                        return True
                    else:
                        logger.warning(
                            f"Token revocation failed for {platform}: {response.status}")
                        return False

        except Exception as e:
            logger.error(f"Error revoking token for {platform}: {e}")
            return False

    async def store_user_tokens(
        self,
        user_id: str,
        platform: str,
        token_info: TokenInfo
    ) -> None:
        """Store user tokens securely."""

        # Use the token manager to store tokens securely
        await self.token_manager.store_token(f"{user_id}_{platform}", token_info)

        logger.info(f"Stored tokens for user {user_id} on platform {platform}")

    async def get_user_tokens(
        self,
        user_id: str,
        platform: str
    ) -> Optional[TokenInfo]:
        """Retrieve user tokens with automatic refresh."""

        token_info = await self.token_manager.get_token(f"{user_id}_{platform}")

        if not token_info:
            return None

        # Check if token needs refresh
        if token_info.expires_soon() and token_info.refresh_token:
            try:
                refreshed_token = await self.refresh_access_token(
                    platform, token_info.refresh_token
                )

                # Store the refreshed token
                await self.store_user_tokens(user_id, platform, refreshed_token)

                return refreshed_token

            except Exception as e:
                logger.error(
                    f"Failed to refresh token for {user_id}/{platform}: {e}")
                # Return the existing token even if refresh failed
                return token_info

        return token_info

    async def revoke_user_tokens(self, user_id: str, platform: str) -> bool:
        """Revoke and delete user tokens."""

        token_info = await self.token_manager.get_token(f"{user_id}_{platform}")

        if not token_info:
            return True  # Already revoked/deleted

        # Revoke the access token
        revoked = await self.revoke_token(platform, token_info.access_token)

        # Also revoke refresh token if available
        if token_info.refresh_token:
            await self.revoke_token(platform, token_info.refresh_token)

        # Delete from storage
        await self.token_manager.delete_token(f"{user_id}_{platform}")

        logger.info(
            f"Revoked and deleted tokens for user {user_id} on platform {platform}")

        return revoked

    def _generate_pkce_challenge(self) -> str:
        """Generate PKCE code challenge for OAuth 2.1."""

        # Generate code verifier
        code_verifier = secrets.token_urlsafe(32)

        # Generate code challenge (SHA256 hash of verifier)
        import hashlib
        import base64

        digest = hashlib.sha256(code_verifier.encode()).digest()
        code_challenge = base64.urlsafe_b64encode(digest).decode().rstrip('=')

        return code_challenge

    async def validate_token(self, platform: str, token: str) -> bool:
        """Validate a token by making a test API call."""

        try:
            # Platform-specific token validation endpoints
            validation_urls = {
                "gmail": "https://www.googleapis.com/oauth2/v1/tokeninfo",
                "slack": "https://slack.com/api/auth.test",
                "discord": "https://discord.com/api/users/@me",
                "twitter": "https://api.twitter.com/2/users/me",
                "linkedin": "https://api.linkedin.com/v2/me"
            }

            url = validation_urls.get(platform)
            if not url:
                return False

            headers = {"Authorization": f"Bearer {token}"}

            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    return response.status == 200

        except Exception as e:
            logger.error(f"Token validation failed for {platform}: {e}")
            return False

    async def get_user_info(self, platform: str, token: str) -> Optional[Dict[str, Any]]:
        """Get user information from the platform API."""

        try:
            # Platform-specific user info endpoints
            user_info_urls = {
                "gmail": "https://www.googleapis.com/oauth2/v2/userinfo",
                "slack": "https://slack.com/api/users.identity",
                "discord": "https://discord.com/api/users/@me",
                "twitter": "https://api.twitter.com/2/users/me",
                "linkedin": "https://api.linkedin.com/v2/me"
            }

            url = user_info_urls.get(platform)
            if not url:
                return None

            headers = {"Authorization": f"Bearer {token}"}

            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        logger.error(
                            f"Failed to get user info for {platform}: {response.status}")
                        return None

        except Exception as e:
            logger.error(f"Error getting user info for {platform}: {e}")
            return None
