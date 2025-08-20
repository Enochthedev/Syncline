"""
Twitter/X connector with OAuth 2.0 authentication for Twitter API v2.

This module provides Twitter/X integration with OAuth 2.0 authentication,
direct message fetching with proper rate limiting, real-time DM processing
using Twitter webhooks, and historical DM retrieval with cursor-based pagination.
"""

import asyncio
import base64
import hashlib
import hmac
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Union
from urllib.parse import urlencode, parse_qs

import aiohttp
import tweepy
from tweepy.asynchronous import AsyncClient

from .base_connector import BaseConnector, RawMessage, AuthenticationError, RateLimitError
from services.event_bus import EventBus, Event, EventType
from services.message_schema import Platform, RawMessage as SchemaRawMessage
from .twitter_helpers import TwitterAuthHelper, TwitterAPIHelper, TwitterMessageHelper, TwitterWebhookHelper

logger = logging.getLogger(__name__)


class TwitterConnectorError(Exception):
    """Twitter connector specific errors."""
    pass


class TwitterWebhookError(Exception):
    """Twitter webhook processing errors."""
    pass


class TwitterConnector(BaseConnector):
    """
    Twitter/X connector with OAuth 2.0 authentication and real-time capabilities.

    Provides Twitter API v2 integration with OAuth 2.0 authentication,
    direct message fetching with proper rate limiting, real-time DM processing
    using Twitter webhooks, and historical DM retrieval with cursor-based pagination.
    """

    def __init__(
        self,
        config: Dict[str, Any],
        event_bus: Optional[EventBus] = None,
        **kwargs
    ):
        super().__init__("twitter", config, **kwargs)

        self.event_bus = event_bus

        # Twitter API v2 configuration
        self.client_id = config.get('client_id')
        self.client_secret = config.get('client_secret')
        self.api_key = config.get('api_key')  # Consumer Key
        self.api_secret = config.get('api_secret')  # Consumer Secret
        self.bearer_token = config.get('bearer_token')

        # OAuth tokens
        self.access_token: Optional[str] = None
        self.access_token_secret: Optional[str] = None
        self.refresh_token: Optional[str] = None

        # OAuth 2.0 configuration
        self.scopes = config.get('scopes', [
            'dm.read',
            'dm.write',
            'tweet.read',
            'users.read',
            'offline.access'  # For refresh tokens
        ])
        self.redirect_uri = config.get(
            'redirect_uri', 'http://localhost:8000/twitter/oauth/callback'
        )

        # Webhook configuration
        self.webhook_endpoint = config.get(
            'webhook_endpoint', '/webhooks/twitter')
        self.webhook_secret = config.get('webhook_secret')
        self.webhook_url = config.get('webhook_url')
        self.environment_name = config.get('environment_name', 'development')

        # API configuration
        self.api_base_url = "https://api.twitter.com/2"
        self.max_results = config.get('max_results', 100)
        self.include_referenced_tweets = config.get(
            'include_referenced_tweets', True)

        # Twitter API clients
        self.async_client: Optional[AsyncClient] = None
        self.v1_client: Optional[tweepy.API] = None  # For webhook management

        # Real-time processing
        self._processing_queue: asyncio.Queue = asyncio.Queue()
        self._processor_task: Optional[asyncio.Task] = None
        self._webhook_registered = False

        # Rate limiting tracking
        self._dm_rate_limit_reset: Optional[datetime] = None
        self._dm_requests_remaining = 300  # Default limit

        # User information cache
        self._user_cache: Dict[str, Dict[str, Any]] = {}
        self._authenticated_user: Optional[Dict[str, Any]] = None

    async def authenticate(self) -> None:
        """Authenticate with Twitter using OAuth 2.0."""
        try:
            logger.info("Starting Twitter OAuth 2.0 authentication")

            if not self.client_id or not self.client_secret:
                raise AuthenticationError(
                    "Twitter client_id and client_secret are required for OAuth 2.0"
                )

            # Check if we have existing tokens
            if self.token_manager:
                token_info = await self.token_manager.get_token(self.platform)
                if token_info and not token_info.is_expired():
                    self.access_token = token_info.access_token
                    self.refresh_token = token_info.refresh_token
                    logger.info("Using existing Twitter tokens")
                    await self._initialize_clients()
                    await self._validate_tokens()
                    return

            # If no valid tokens, start OAuth flow
            await self._start_oauth_flow()

        except Exception as e:
            logger.error(f"Twitter authentication failed: {e}")
            raise AuthenticationError(f"Twitter authentication failed: {e}")

    async def start_real_time_ingestion(self) -> None:
        """Start real-time message ingestion using Twitter webhooks."""
        try:
            logger.info("Starting Twitter real-time ingestion")

            # Load authenticated user information
            await self._load_user_info()

            # Start message processor
            self._processor_task = asyncio.create_task(
                self._process_message_queue()
            )

            # Set up webhooks if configured
            if self.webhook_url and self.webhook_secret:
                await self._setup_webhooks()

            logger.info("Twitter real-time ingestion started successfully")

        except Exception as e:
            logger.error(f"Failed to start Twitter real-time ingestion: {e}")
            raise TwitterConnectorError(
                f"Failed to start real-time ingestion: {e}"
            )

    async def stop_real_time_ingestion(self) -> None:
        """Stop real-time message ingestion."""
        try:
            logger.info("Stopping Twitter real-time ingestion")

            # Remove webhooks
            if self._webhook_registered:
                await self._remove_webhooks()

            # Stop processor task
            if self._processor_task:
                self._processor_task.cancel()
                try:
                    await self._processor_task
                except asyncio.CancelledError:
                    pass
                self._processor_task = None

            logger.info("Twitter real-time ingestion stopped")

        except Exception as e:
            logger.error(f"Error stopping Twitter real-time ingestion: {e}")

    async def fetch_historical_messages(
        self,
        cursor: Optional[str] = None,
        limit: int = 100
    ) -> List[RawMessage]:
        """
        Fetch historical direct messages with cursor-based pagination.

        Args:
            cursor: Pagination token for next page (None for first page)
            limit: Maximum number of messages to fetch

        Returns:
            List of raw messages
        """
        try:
            logger.debug(
                f"Fetching historical Twitter DMs (cursor: {cursor}, limit: {limit})"
            )

            if not self.async_client:
                raise TwitterConnectorError("Twitter client not initialized")

            # Check rate limits before making request
            await self._check_dm_rate_limits()

            # Fetch direct message events
            params = {
                'max_results': min(limit, self.max_results),
                'dm_event.fields': 'id,text,created_at,sender_id,referenced_tweet,attachments',
                'user.fields': 'id,name,username,profile_image_url',
                'expansions': 'sender_id,referenced_tweet_id,attachments.media_keys'
            }

            if cursor:
                params['pagination_token'] = cursor

            # Use the async client to fetch DM events
            response = await self._make_twitter_api_call(
                'GET',
                '/2/dm_events',
                params=params
            )

            if not response.get('data'):
                logger.debug("No DM events found")
                return []

            dm_events = response['data']
            includes = response.get('includes', {})

            # Process DM events into raw messages
            raw_messages = []
            for dm_event in dm_events:
                try:
                    raw_message = await self._process_dm_event(dm_event, includes)
                    if raw_message:
                        raw_messages.append(raw_message)
                except Exception as e:
                    logger.error(
                        f"Error processing DM event {dm_event.get('id')}: {e}")
                    continue

            logger.info(f"Fetched {len(raw_messages)} Twitter DMs")
            return raw_messages

        except Exception as e:
            logger.error(f"Error fetching Twitter messages: {e}")
            raise TwitterConnectorError(f"Error fetching messages: {e}")

    async def handle_webhook(self, payload: Dict[str, Any]) -> None:
        """
        Handle incoming Twitter webhook payload.

        Args:
            payload: Webhook payload from Twitter
        """
        try:
            logger.debug("Processing Twitter webhook payload")

            # Validate webhook signature
            if self.webhook_secret:
                await self._validate_webhook_signature(payload)

            # Handle different webhook event types
            if 'direct_message_events' in payload:
                dm_events = payload['direct_message_events']
                for dm_event in dm_events:
                    await self._processing_queue.put({
                        'type': 'direct_message',
                        'event': dm_event,
                        'timestamp': datetime.now(timezone.utc)
                    })

            # Handle user events (follows, blocks, etc.)
            if 'user_event' in payload:
                user_event = payload['user_event']
                logger.debug(f"Received user event: {user_event.get('type')}")

            # Handle tweet events if configured
            if 'tweet_create_events' in payload:
                tweet_events = payload['tweet_create_events']
                logger.debug(f"Received {len(tweet_events)} tweet events")

        except Exception as e:
            logger.error(f"Error handling Twitter webhook: {e}")
            raise TwitterWebhookError(f"Webhook processing failed: {e}")

    async def _start_oauth_flow(self) -> None:
        """Start OAuth 2.0 flow for Twitter authentication."""
        try:
            # Generate PKCE challenge
            code_challenge, code_verifier = TwitterAuthHelper.generate_code_challenge()
            self._code_verifier = code_verifier

            # Generate OAuth URL
            oauth_url = TwitterAuthHelper.generate_oauth_url(
                self.client_id,
                self.redirect_uri,
                self.scopes,
                code_challenge
            )

            logger.info(
                f"Please visit this URL to authorize the app: {oauth_url}")

            # In a real implementation, you would:
            # 1. Open the URL in a browser or provide it to the user
            # 2. Handle the callback with the authorization code
            # 3. Exchange the code for tokens
            # For now, we'll assume tokens are provided via configuration

            raise AuthenticationError(
                "OAuth flow not fully implemented. Please provide access_token in configuration."
            )

        except Exception as e:
            logger.error(f"OAuth flow failed: {e}")
            raise AuthenticationError(f"OAuth flow failed: {e}")

    async def _initialize_clients(self) -> None:
        """Initialize Twitter API clients."""
        helper = TwitterAPIHelper(self)
        await helper.initialize_clients()

    async def _validate_tokens(self) -> None:
        """Validate Twitter tokens by making a test API call."""
        helper = TwitterAPIHelper(self)
        await helper.validate_tokens()

    async def _load_user_info(self) -> None:
        """Load authenticated user information."""
        helper = TwitterAPIHelper(self)
        await helper.load_user_info()

    async def _setup_webhooks(self) -> None:
        """Set up Twitter webhooks for real-time events."""
        helper = TwitterWebhookHelper(self)
        await helper.setup_webhooks()

    async def _remove_webhooks(self) -> None:
        """Remove Twitter webhooks."""
        helper = TwitterWebhookHelper(self)
        await helper.remove_webhooks()

    async def _validate_webhook_signature(self, payload: Dict[str, Any]) -> None:
        """Validate webhook signature from Twitter."""
        helper = TwitterWebhookHelper(self)
        helper.validate_webhook_signature(payload)

    async def _check_dm_rate_limits(self) -> None:
        """Check and handle DM API rate limits."""
        helper = TwitterAPIHelper(self)
        await helper.check_dm_rate_limits()

    async def _make_twitter_api_call(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make a Twitter API call with proper error handling."""
        helper = TwitterAPIHelper(self)
        return await helper.make_api_call(method, endpoint, params, data)

    async def _process_dm_event(
        self,
        dm_event: Dict[str, Any],
        includes: Dict[str, Any]
    ) -> Optional[RawMessage]:
        """Process a DM event into a RawMessage."""
        return TwitterMessageHelper.process_dm_event(
            dm_event, includes, self._authenticated_user
        )

    async def _process_message_queue(self) -> None:
        """Process queued messages from webhooks."""
        logger.info("Starting Twitter message queue processor")

        while True:
            try:
                # Get item from queue with timeout
                item = await asyncio.wait_for(
                    self._processing_queue.get(),
                    timeout=1.0
                )

                if item['type'] == 'direct_message':
                    await self._process_webhook_dm(item['event'])

                # Mark task as done
                self._processing_queue.task_done()

            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                logger.info("Twitter message queue processor cancelled")
                break
            except Exception as e:
                logger.error(f"Error processing queued message: {e}")

    async def _process_webhook_dm(self, dm_event: Dict[str, Any]) -> None:
        """Process a DM event from webhook."""
        try:
            logger.debug(f"Processing webhook DM event: {dm_event.get('id')}")

            # Convert webhook DM format to API v2 format if needed
            # This depends on the webhook payload structure

            # Create raw message
            raw_message = await self._process_dm_event(dm_event, {})
            if not raw_message:
                return

            # Publish to event bus if available
            if self.event_bus:
                event = Event(
                    type=EventType.MESSAGE_RECEIVED,
                    data={
                        'platform': self.platform,
                        'message': raw_message.__dict__
                    },
                    source=f"{self.platform}_connector"
                )

                await self.event_bus.publish('messages.raw', event)
                logger.debug(
                    f"Published new Twitter DM to event bus: {raw_message.id}"
                )

        except Exception as e:
            logger.error(f"Error processing webhook DM: {e}")

    async def _platform_health_check(self) -> None:
        """Twitter-specific health check."""
        try:
            if not self.async_client:
                raise TwitterConnectorError("Twitter client not initialized")

            # Test API access
            me = await self.async_client.get_me()
            if not me.data:
                raise TwitterConnectorError("Unable to get user profile")

            logger.debug(
                f"Twitter health check passed for @{me.data.username}")

        except Exception as e:
            logger.error(f"Twitter health check failed: {e}")
            raise TwitterConnectorError(f"Health check failed: {e}")

    def get_next_page_token(self, response: Dict[str, Any]) -> Optional[str]:
        """Extract next page token from Twitter API response."""
        meta = response.get('meta', {})
        return meta.get('next_token')

    async def get_dm_count(self) -> int:
        """Get total DM count for the user."""
        try:
            if not self.async_client:
                return 0

            # Twitter API v2 doesn't provide a direct count endpoint
            # This would require fetching and counting messages
            # For now, return 0 as a placeholder
            return 0

        except Exception as e:
            logger.error(f"Error getting DM count: {e}")
            return 0

    def get_authenticated_user(self) -> Optional[Dict[str, Any]]:
        """Get authenticated user information."""
        return self._authenticated_user

    async def send_direct_message(
        self,
        recipient_id: str,
        text: str,
        media_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Send a direct message.

        Args:
            recipient_id: Twitter user ID of the recipient
            text: Message text
            media_id: Optional media ID for attachments

        Returns:
            Message ID if successful, None otherwise
        """
        try:
            if not self.async_client:
                raise TwitterConnectorError("Twitter client not initialized")

            # Prepare message data
            message_data = {
                'text': text,
                'target': {'recipient_id': recipient_id}
            }

            if media_id:
                message_data['attachments'] = [{'media_id': media_id}]

            # Send DM using API v2
            response = await self._make_twitter_api_call(
                'POST',
                f'/2/dm_conversations/with/{recipient_id}/messages',
                data=message_data
            )

            if response.get('data'):
                message_id = response['data'].get('dm_event_id')
                logger.info(f"Sent DM to {recipient_id}: {message_id}")
                return message_id

            return None

        except Exception as e:
            logger.error(f"Error sending DM: {e}")
            return None
