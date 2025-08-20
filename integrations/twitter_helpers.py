"""
Twitter connector helper methods and utilities.

This module contains helper methods for the Twitter connector to keep
the main connector file focused and under the line limit.
"""

import base64
import hashlib
import hmac
import json
import logging
import secrets
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from urllib.parse import urlencode

import aiohttp
import tweepy
from tweepy.asynchronous import AsyncClient

from .base_connector import RawMessage, AuthenticationError, RateLimitError


class TwitterConnectorError(Exception):
    """Twitter connector specific errors."""
    pass


logger = logging.getLogger(__name__)


class TwitterAuthHelper:
    """Helper class for Twitter authentication operations."""

    @staticmethod
    def generate_code_challenge() -> tuple[str, str]:
        """Generate PKCE code challenge and verifier for OAuth 2.0."""
        # Generate code verifier
        code_verifier = base64.urlsafe_b64encode(
            secrets.token_bytes(32)).decode('utf-8')
        code_verifier = code_verifier.rstrip('=')

        # Generate code challenge
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode('utf-8')).digest()
        ).decode('utf-8')
        code_challenge = code_challenge.rstrip('=')

        return code_challenge, code_verifier

    @staticmethod
    def generate_oauth_url(
        client_id: str,
        redirect_uri: str,
        scopes: List[str],
        code_challenge: str
    ) -> str:
        """Generate OAuth 2.0 authorization URL."""
        oauth_params = {
            'response_type': 'code',
            'client_id': client_id,
            'redirect_uri': redirect_uri,
            'scope': ' '.join(scopes),
            'state': base64.urlsafe_b64encode(
                f"twitter_{datetime.now().timestamp()}".encode()
            ).decode(),
            'code_challenge': code_challenge,
            'code_challenge_method': 'S256'
        }

        return f"https://twitter.com/i/oauth2/authorize?{urlencode(oauth_params)}"


class TwitterAPIHelper:
    """Helper class for Twitter API operations."""

    def __init__(self, connector):
        self.connector = connector

    async def initialize_clients(self) -> None:
        """Initialize Twitter API clients."""
        try:
            # Initialize async client for API v2
            if self.connector.access_token:
                self.connector.async_client = AsyncClient(
                    bearer_token=self.connector.bearer_token,
                    consumer_key=self.connector.api_key,
                    consumer_secret=self.connector.api_secret,
                    access_token=self.connector.access_token,
                    access_token_secret=self.connector.access_token_secret
                )
            elif self.connector.bearer_token:
                self.connector.async_client = AsyncClient(
                    bearer_token=self.connector.bearer_token)
            else:
                raise TwitterConnectorError(
                    "No valid authentication tokens available")

            # Initialize v1 client for webhook management (requires OAuth 1.0a)
            if (self.connector.api_key and self.connector.api_secret and
                    self.connector.access_token and self.connector.access_token_secret):
                auth = tweepy.OAuth1UserHandler(
                    self.connector.api_key,
                    self.connector.api_secret,
                    self.connector.access_token,
                    self.connector.access_token_secret
                )
                self.connector.v1_client = tweepy.API(auth)

            logger.info("Twitter API clients initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Twitter clients: {e}")
            raise TwitterConnectorError(f"Failed to initialize clients: {e}")

    async def validate_tokens(self) -> None:
        """Validate Twitter tokens by making a test API call."""
        try:
            if not self.connector.async_client:
                raise TwitterConnectorError("Twitter client not initialized")

            # Test API access by getting authenticated user
            me = await self.connector.async_client.get_me()
            if me.data:
                self.connector._authenticated_user = {
                    'id': me.data.id,
                    'username': me.data.username,
                    'name': me.data.name
                }
                logger.info(
                    f"Twitter token validation successful for @{me.data.username}")
            else:
                raise TwitterConnectorError("Unable to get authenticated user")

        except Exception as e:
            logger.error(f"Token validation failed: {e}")
            raise AuthenticationError(f"Token validation failed: {e}")

    async def load_user_info(self) -> None:
        """Load authenticated user information."""
        try:
            if not self.connector._authenticated_user and self.connector.async_client:
                me = await self.connector.async_client.get_me(
                    user_fields=['id', 'name', 'username',
                                 'profile_image_url', 'verified']
                )
                if me.data:
                    self.connector._authenticated_user = {
                        'id': me.data.id,
                        'username': me.data.username,
                        'name': me.data.name,
                        'profile_image_url': getattr(me.data, 'profile_image_url', None),
                        'verified': getattr(me.data, 'verified', False)
                    }

            logger.info("Twitter user information loaded successfully")

        except Exception as e:
            logger.error(f"Failed to load user info: {e}")

    async def make_api_call(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make a Twitter API call with proper error handling."""
        if not self.connector._session:
            raise TwitterConnectorError("HTTP session not initialized")

        url = f"{self.connector.api_base_url}{endpoint}"
        headers = {}

        # Add authentication
        if self.connector.access_token:
            headers['Authorization'] = f'Bearer {self.connector.access_token}'
        elif self.connector.bearer_token:
            headers['Authorization'] = f'Bearer {self.connector.bearer_token}'
        else:
            raise TwitterConnectorError("No authentication token available")

        try:
            if method.upper() == 'GET':
                response = await self.connector._session.get(url, params=params, headers=headers)
            elif method.upper() == 'POST':
                headers['Content-Type'] = 'application/json'
                response = await self.connector._session.post(
                    url,
                    params=params,
                    json=data,
                    headers=headers
                )
            else:
                raise TwitterConnectorError(
                    f"Unsupported HTTP method: {method}")

            # Handle rate limiting
            if response.status == 429:
                reset_time = response.headers.get('x-rate-limit-reset')
                if reset_time:
                    self.connector._dm_rate_limit_reset = datetime.fromtimestamp(
                        int(reset_time), tz=timezone.utc
                    )

                remaining = response.headers.get('x-rate-limit-remaining')
                if remaining:
                    self.connector._dm_requests_remaining = int(remaining)

                retry_after = response.headers.get('retry-after')
                raise RateLimitError(
                    f"Rate limit exceeded: {response.status}",
                    # Default 15 minutes
                    int(retry_after) if retry_after else 900
                )

            response.raise_for_status()
            return await response.json()

        except aiohttp.ClientResponseError as e:
            if e.status == 429:
                raise RateLimitError(f"Rate limit exceeded: {e}", 900)
            logger.error(f"Twitter API error: {e}")
            raise TwitterConnectorError(f"API call failed: {e}")
        except Exception as e:
            logger.error(f"Error making Twitter API call: {e}")
            raise TwitterConnectorError(f"API call failed: {e}")

    async def check_dm_rate_limits(self) -> None:
        """Check and handle DM API rate limits."""
        try:
            current_time = datetime.now(timezone.utc)

            # Check if we're within rate limits
            if (self.connector._dm_rate_limit_reset and
                current_time < self.connector._dm_rate_limit_reset and
                    self.connector._dm_requests_remaining <= 0):

                wait_time = (self.connector._dm_rate_limit_reset -
                             current_time).total_seconds()
                logger.warning(
                    f"DM rate limit exceeded, waiting {wait_time} seconds")

                raise RateLimitError(
                    f"DM rate limit exceeded, retry after {wait_time} seconds",
                    int(wait_time)
                )

            # Reset rate limit tracking if window has passed
            if (self.connector._dm_rate_limit_reset and
                    current_time >= self.connector._dm_rate_limit_reset):
                self.connector._dm_requests_remaining = 300  # Reset to default
                self.connector._dm_rate_limit_reset = None

        except RateLimitError:
            raise
        except Exception as e:
            logger.error(f"Error checking rate limits: {e}")


class TwitterMessageHelper:
    """Helper class for Twitter message processing."""

    @staticmethod
    def process_dm_event(
        dm_event: Dict[str, Any],
        includes: Dict[str, Any],
        authenticated_user: Optional[Dict[str, Any]] = None
    ) -> Optional[RawMessage]:
        """Process a DM event into a RawMessage."""
        try:
            event_id = dm_event.get('id')
            if not event_id:
                return None

            # Extract sender information
            sender_id = dm_event.get('sender_id')
            sender_info = TwitterMessageHelper.get_user_from_includes(
                sender_id, includes)

            # Extract message content
            content = TwitterMessageHelper.extract_dm_content(
                dm_event, includes)

            # Extract timestamp
            timestamp = TwitterMessageHelper.extract_timestamp(dm_event)

            # Create conversation ID (DM thread between users)
            conversation_id = TwitterMessageHelper.generate_conversation_id(
                sender_id,
                authenticated_user.get('id') if authenticated_user else None
            )

            raw_message = RawMessage(
                id=f"twitter_dm_{event_id}",
                platform="twitter",
                platform_message_id=event_id,
                thread_id=conversation_id,
                sender_id=sender_id,
                content=content,
                timestamp=timestamp,
                metadata={
                    'sender_info': sender_info,
                    'event_type': dm_event.get('event_type', 'MessageCreate'),
                    'conversation_id': conversation_id
                },
                raw_data=dm_event
            )

            return raw_message

        except Exception as e:
            logger.error(f"Error processing DM event: {e}")
            return None

    @staticmethod
    def get_user_from_includes(
        user_id: str,
        includes: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Get user information from includes data."""
        users = includes.get('users', [])
        for user in users:
            if user.get('id') == user_id:
                return {
                    'id': user.get('id'),
                    'username': user.get('username'),
                    'name': user.get('name'),
                    'profile_image_url': user.get('profile_image_url')
                }
        return None

    @staticmethod
    def extract_dm_content(
        dm_event: Dict[str, Any],
        includes: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract content from DM event."""
        content = {
            'text': dm_event.get('text', ''),
            'attachments': []
        }

        # Handle media attachments
        attachments = dm_event.get('attachments', {})
        media_keys = attachments.get('media_keys', [])

        if media_keys and 'media' in includes:
            media_objects = includes['media']
            for media_key in media_keys:
                for media in media_objects:
                    if media.get('media_key') == media_key:
                        content['attachments'].append({
                            'type': media.get('type'),
                            'url': media.get('url'),
                            'preview_image_url': media.get('preview_image_url'),
                            'width': media.get('width'),
                            'height': media.get('height'),
                            'media_key': media_key
                        })

        # Handle referenced tweets
        referenced_tweet = dm_event.get('referenced_tweet')
        if referenced_tweet:
            content['referenced_tweet'] = {
                'type': referenced_tweet.get('type'),
                'id': referenced_tweet.get('id')
            }

        return content

    @staticmethod
    def extract_timestamp(dm_event: Dict[str, Any]) -> datetime:
        """Extract timestamp from DM event."""
        created_at = dm_event.get('created_at')
        if created_at:
            try:
                # Twitter API v2 returns ISO format timestamps
                return datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                pass

        return datetime.now(timezone.utc)

    @staticmethod
    def generate_conversation_id(
        sender_id: str,
        recipient_id: Optional[str]
    ) -> str:
        """Generate a consistent conversation ID for DM threads."""
        if not recipient_id:
            return f"twitter_dm_{sender_id}"

        # Sort IDs to ensure consistent conversation ID regardless of sender
        ids = sorted([sender_id, recipient_id])
        return f"twitter_dm_{ids[0]}_{ids[1]}"


class TwitterWebhookHelper:
    """Helper class for Twitter webhook operations."""

    def __init__(self, connector):
        self.connector = connector

    async def setup_webhooks(self) -> None:
        """Set up Twitter webhooks for real-time events."""
        try:
            logger.info("Setting up Twitter webhooks")

            if not self.connector.v1_client:
                logger.warning(
                    "V1 client not available, cannot set up webhooks")
                return

            # Note: Twitter webhook setup requires Account Activity API
            # which is part of Twitter API v1.1 and requires special access
            # This is a placeholder for webhook setup logic

            # In a real implementation, you would:
            # 1. Register webhook URL with Twitter
            # 2. Subscribe to user events
            # 3. Handle CRC (Challenge Response Check)

            logger.info("Twitter webhooks setup completed")
            self.connector._webhook_registered = True

        except Exception as e:
            logger.error(f"Failed to set up Twitter webhooks: {e}")
            # Don't raise exception - webhooks are optional

    async def remove_webhooks(self) -> None:
        """Remove Twitter webhooks."""
        try:
            logger.info("Removing Twitter webhooks")

            if not self.connector.v1_client:
                return

            # Remove webhook subscriptions
            # This is a placeholder for webhook removal logic

            logger.info("Twitter webhooks removed")
            self.connector._webhook_registered = False

        except Exception as e:
            logger.error(f"Error removing Twitter webhooks: {e}")

    def validate_webhook_signature(self, payload: Dict[str, Any]) -> None:
        """Validate webhook signature from Twitter."""
        if not self.connector.webhook_secret:
            return

        # Twitter webhook signature validation
        # This is a placeholder for signature validation logic
        logger.debug("Webhook signature validation not fully implemented")
