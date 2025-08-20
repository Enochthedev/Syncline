"""
Slack connector with Events API integration and Socket Mode support.

This module provides Slack integration with OAuth 2.0 authentication,
real-time event handling, and historical message fetching capabilities.
"""

import asyncio
import json
import logging
import websockets
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Union
from urllib.parse import urlencode
import aiohttp

from .base_connector import BaseConnector, RawMessage, AuthenticationError
from services.event_bus import EventBus, Event, EventType
from services.message_schema import Platform, RawMessage as SchemaRawMessage

logger = logging.getLogger(__name__)


class SlackConnectorError(Exception):
    """Slack connector specific errors."""
    pass


class SlackWebhookError(Exception):
    """Slack webhook processing errors."""
    pass


class SlackSocketModeError(Exception):
    """Slack Socket Mode specific errors."""
    pass


class SlackConnector(BaseConnector):
    """
    Slack connector with OAuth 2.0 authentication and real-time capabilities.

    Provides Slack API integration with Events API, Socket Mode support,
    historical message fetching with conversation history API, and real-time
    message processing with proper event filtering.
    """

    def __init__(
        self,
        config: Dict[str, Any],
        event_bus: Optional[EventBus] = None,
        **kwargs
    ):
        super().__init__("slack", config, **kwargs)

        self.event_bus = event_bus

        # Slack-specific configuration
        self.client_id = config.get('client_id')
        self.client_secret = config.get('client_secret')
        self.signing_secret = config.get('signing_secret')
        self.app_token = config.get('app_token')  # For Socket Mode
        self.bot_token: Optional[str] = None
        self.user_token: Optional[str] = None

        # OAuth configuration
        self.scopes = config.get('scopes', [
            'channels:history',
            'channels:read',
            'chat:write',
            'groups:history',
            'groups:read',
            'im:history',
            'im:read',
            'mpim:history',
            'mpim:read',
            'users:read',
            'users:read.email',
            'team:read'
        ])
        self.redirect_uri = config.get(
            'redirect_uri', 'http://localhost:8000/slack/oauth/callback')

        # API configuration
        self.api_base_url = "https://slack.com/api"
        self.socket_mode_enabled = config.get('socket_mode_enabled', True)
        self.events_api_enabled = config.get('events_api_enabled', True)
        self.webhook_endpoint = config.get(
            'webhook_endpoint', '/webhooks/slack')

        # Pagination and fetching configuration
        self.max_results = config.get('max_results', 200)
        self.include_private_channels = config.get(
            'include_private_channels', True)
        self.include_direct_messages = config.get(
            'include_direct_messages', True)

        # Real-time processing
        self._socket_connection: Optional[websockets.WebSocketServerProtocol] = None
        self._socket_task: Optional[asyncio.Task] = None
        self._processing_queue: asyncio.Queue = asyncio.Queue()
        self._processor_task: Optional[asyncio.Task] = None
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = 5

        # Channel and user caches
        self._channels_cache: Dict[str, Dict[str, Any]] = {}
        self._users_cache: Dict[str, Dict[str, Any]] = {}
        self._team_info: Optional[Dict[str, Any]] = None

    async def authenticate(self) -> None:
        """Authenticate with Slack using OAuth 2.0."""
        try:
            logger.info("Starting Slack OAuth 2.0 authentication")

            if not self.client_id or not self.client_secret:
                raise AuthenticationError(
                    "Slack client_id and client_secret are required"
                )

            # Check if we have existing tokens
            if self.token_manager:
                token_info = await self.token_manager.get_token(self.platform)
                if token_info and not token_info.is_expired():
                    self.bot_token = token_info.access_token
                    self.user_token = token_info.metadata.get('user_token')
                    logger.info("Using existing Slack tokens")
                    await self._validate_tokens()
                    return

            # If no valid tokens, start OAuth flow
            await self._start_oauth_flow()

        except Exception as e:
            logger.error(f"Slack authentication failed: {e}")
            raise AuthenticationError(f"Slack authentication failed: {e}")

    async def start_real_time_ingestion(self) -> None:
        """Start real-time message ingestion using Socket Mode or Events API."""
        try:
            logger.info("Starting Slack real-time ingestion")

            # Load channel and user information
            await self._load_workspace_info()

            # Start message processor
            self._processor_task = asyncio.create_task(
                self._process_message_queue()
            )

            # Start Socket Mode if enabled and app token is available
            if self.socket_mode_enabled and self.app_token:
                await self._start_socket_mode()
            elif self.events_api_enabled:
                logger.info(
                    "Socket Mode not available, using Events API webhooks")
            else:
                logger.warning("No real-time method configured")

            logger.info("Slack real-time ingestion started successfully")

        except Exception as e:
            logger.error(f"Failed to start Slack real-time ingestion: {e}")
            raise SlackConnectorError(
                f"Failed to start real-time ingestion: {e}")

    async def stop_real_time_ingestion(self) -> None:
        """Stop real-time message ingestion."""
        try:
            logger.info("Stopping Slack real-time ingestion")

            # Stop Socket Mode connection
            if self._socket_task:
                self._socket_task.cancel()
                try:
                    await self._socket_task
                except asyncio.CancelledError:
                    pass
                self._socket_task = None

            if self._socket_connection:
                await self._socket_connection.close()
                self._socket_connection = None

            # Stop processor task
            if self._processor_task:
                self._processor_task.cancel()
                try:
                    await self._processor_task
                except asyncio.CancelledError:
                    pass
                self._processor_task = None

            logger.info("Slack real-time ingestion stopped")

        except Exception as e:
            logger.error(f"Error stopping Slack real-time ingestion: {e}")

    async def fetch_historical_messages(
        self,
        cursor: Optional[str] = None,
        limit: int = 100
    ) -> List[RawMessage]:
        """
        Fetch historical messages with cursor-based pagination.

        Args:
            cursor: Cursor for pagination (None for first page)
            limit: Maximum number of messages to fetch

        Returns:
            List of raw messages
        """
        try:
            logger.debug(
                f"Fetching historical Slack messages (cursor: {cursor}, limit: {limit})"
            )

            if not self.bot_token:
                raise SlackConnectorError("Bot token not available")

            raw_messages = []

            # Get all channels first
            channels = await self._get_all_channels()

            for channel in channels:
                channel_id = channel['id']
                channel_messages = await self._fetch_channel_history(
                    channel_id, cursor, limit
                )
                raw_messages.extend(channel_messages)

                # Respect rate limits
                await asyncio.sleep(0.1)

            logger.info(f"Fetched {len(raw_messages)} Slack messages")
            return raw_messages

        except Exception as e:
            logger.error(f"Error fetching Slack messages: {e}")
            raise SlackConnectorError(f"Error fetching messages: {e}")

    async def handle_webhook(self, payload: Dict[str, Any]) -> None:
        """
        Handle incoming Slack Events API webhook.

        Args:
            payload: Webhook payload from Slack Events API
        """
        try:
            logger.debug("Processing Slack webhook payload")

            # Handle URL verification challenge
            if payload.get('type') == 'url_verification':
                return payload.get('challenge')

            # Validate webhook signature
            await self._validate_webhook_signature(payload)

            # Handle event callback
            if payload.get('type') == 'event_callback':
                event = payload.get('event', {})
                await self._handle_slack_event(event)

            return None

        except Exception as e:
            logger.error(f"Error handling Slack webhook: {e}")
            raise SlackWebhookError(f"Webhook processing failed: {e}")

    async def _start_oauth_flow(self) -> None:
        """Start OAuth 2.0 flow for Slack authentication."""
        # Generate OAuth URL
        oauth_params = {
            'client_id': self.client_id,
            'scope': ' '.join(self.scopes),
            'redirect_uri': self.redirect_uri,
            'response_type': 'code'
        }

        oauth_url = f"https://slack.com/oauth/v2/authorize?{urlencode(oauth_params)}"

        logger.info(f"Please visit this URL to authorize the app: {oauth_url}")

        # In a real implementation, you would:
        # 1. Open the URL in a browser or provide it to the user
        # 2. Handle the callback with the authorization code
        # 3. Exchange the code for tokens
        # For now, we'll assume tokens are provided via configuration

        raise AuthenticationError(
            "OAuth flow not fully implemented. Please provide bot_token in configuration."
        )

    async def _validate_tokens(self) -> None:
        """Validate Slack tokens by making a test API call."""
        try:
            # Test bot token
            if self.bot_token:
                response = await self._make_api_call('auth.test', token=self.bot_token)
                if not response.get('ok'):
                    raise AuthenticationError(
                        f"Bot token validation failed: {response.get('error')}")

            # Test user token if available
            if self.user_token:
                response = await self._make_api_call('auth.test', token=self.user_token)
                if not response.get('ok'):
                    logger.warning(
                        f"User token validation failed: {response.get('error')}")

            logger.info("Slack token validation successful")

        except Exception as e:
            logger.error(f"Token validation failed: {e}")
            raise AuthenticationError(f"Token validation failed: {e}")

    async def _load_workspace_info(self) -> None:
        """Load workspace information including channels and users."""
        try:
            logger.info("Loading Slack workspace information")

            # Load team info
            team_response = await self._make_api_call('team.info')
            if team_response.get('ok'):
                self._team_info = team_response.get('team', {})

            # Load channels
            await self._load_channels()

            # Load users
            await self._load_users()

            logger.info("Slack workspace information loaded successfully")

        except Exception as e:
            logger.error(f"Failed to load workspace info: {e}")
            raise SlackConnectorError(f"Failed to load workspace info: {e}")

    async def _load_channels(self) -> None:
        """Load all channels from the workspace."""
        try:
            # Load public channels
            channels_response = await self._make_api_call(
                'conversations.list',
                params={'types': 'public_channel,private_channel,mpim,im'}
            )

            if channels_response.get('ok'):
                channels = channels_response.get('channels', [])
                for channel in channels:
                    self._channels_cache[channel['id']] = channel

            logger.debug(f"Loaded {len(self._channels_cache)} channels")

        except Exception as e:
            logger.error(f"Failed to load channels: {e}")

    async def _load_users(self) -> None:
        """Load all users from the workspace."""
        try:
            users_response = await self._make_api_call('users.list')

            if users_response.get('ok'):
                users = users_response.get('members', [])
                for user in users:
                    self._users_cache[user['id']] = user

            logger.debug(f"Loaded {len(self._users_cache)} users")

        except Exception as e:
            logger.error(f"Failed to load users: {e}")

    async def _start_socket_mode(self) -> None:
        """Start Socket Mode connection for real-time events."""
        try:
            logger.info("Starting Slack Socket Mode connection")

            if not self.app_token:
                raise SlackSocketModeError(
                    "App token required for Socket Mode")

            # Get Socket Mode URL
            response = await self._make_api_call(
                'apps.connections.open',
                token=self.app_token
            )

            if not response.get('ok'):
                raise SlackSocketModeError(
                    f"Failed to get Socket Mode URL: {response.get('error')}")

            socket_url = response.get('url')
            if not socket_url:
                raise SlackSocketModeError("No Socket Mode URL received")

            # Start Socket Mode task
            self._socket_task = asyncio.create_task(
                self._socket_mode_handler(socket_url)
            )

            logger.info("Slack Socket Mode connection started")

        except Exception as e:
            logger.error(f"Failed to start Socket Mode: {e}")
            raise SlackSocketModeError(f"Failed to start Socket Mode: {e}")

    async def _socket_mode_handler(self, socket_url: str) -> None:
        """Handle Socket Mode WebSocket connection."""
        while self._running and self._reconnect_attempts < self._max_reconnect_attempts:
            try:
                logger.info(f"Connecting to Slack Socket Mode: {socket_url}")

                async with websockets.connect(socket_url) as websocket:
                    self._socket_connection = websocket
                    self._reconnect_attempts = 0

                    logger.info("Socket Mode connection established")

                    async for message in websocket:
                        try:
                            data = json.loads(message)
                            await self._handle_socket_message(data)
                        except json.JSONDecodeError as e:
                            logger.error(
                                f"Failed to parse Socket Mode message: {e}")
                        except Exception as e:
                            logger.error(
                                f"Error handling Socket Mode message: {e}")

            except websockets.exceptions.ConnectionClosed:
                logger.warning("Socket Mode connection closed")
                self._reconnect_attempts += 1
                if self._reconnect_attempts < self._max_reconnect_attempts:
                    wait_time = min(2 ** self._reconnect_attempts, 60)
                    logger.info(f"Reconnecting in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error("Max reconnection attempts reached")
                    break
            except Exception as e:
                logger.error(f"Socket Mode connection error: {e}")
                self._reconnect_attempts += 1
                await asyncio.sleep(5)

        self._socket_connection = None

    async def _handle_socket_message(self, data: Dict[str, Any]) -> None:
        """Handle incoming Socket Mode message."""
        try:
            message_type = data.get('type')

            if message_type == 'hello':
                logger.info("Received Socket Mode hello message")
                return

            elif message_type == 'events_api':
                # Acknowledge the message
                envelope_id = data.get('envelope_id')
                if envelope_id and self._socket_connection:
                    ack_message = json.dumps({
                        'envelope_id': envelope_id
                    })
                    await self._socket_connection.send(ack_message)

                # Process the event
                event = data.get('payload', {}).get('event', {})
                await self._handle_slack_event(event)

            elif message_type == 'disconnect':
                logger.warning("Received Socket Mode disconnect message")
                reason = data.get('reason', 'unknown')
                logger.warning(f"Disconnect reason: {reason}")

        except Exception as e:
            logger.error(f"Error handling Socket Mode message: {e}")

    async def _handle_slack_event(self, event: Dict[str, Any]) -> None:
        """Handle Slack event from Events API or Socket Mode."""
        try:
            event_type = event.get('type')

            if event_type == 'message':
                # Filter out bot messages and message subtypes we don't want
                if (event.get('bot_id') or
                        event.get('subtype') in ['bot_message', 'message_changed', 'message_deleted']):
                    return

                # Queue message for processing
                await self._processing_queue.put({
                    'type': 'message',
                    'event': event,
                    'timestamp': datetime.now(timezone.utc)
                })

            elif event_type in ['channel_created', 'channel_deleted', 'channel_rename']:
                # Refresh channel cache
                await self._load_channels()

            elif event_type in ['team_join', 'user_change']:
                # Refresh user cache
                await self._load_users()

        except Exception as e:
            logger.error(f"Error handling Slack event: {e}")

    async def _process_message_queue(self) -> None:
        """Process queued messages from events."""
        logger.info("Starting Slack message queue processor")

        while True:
            try:
                # Get item from queue with timeout
                item = await asyncio.wait_for(
                    self._processing_queue.get(),
                    timeout=1.0
                )

                if item['type'] == 'message':
                    await self._process_message_event(item['event'])

                # Mark task as done
                self._processing_queue.task_done()

            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                logger.info("Slack message queue processor cancelled")
                break
            except Exception as e:
                logger.error(f"Error processing queued message: {e}")

    async def _process_message_event(self, event: Dict[str, Any]) -> None:
        """Process a message event from Slack."""
        try:
            logger.debug(f"Processing Slack message event: {event.get('ts')}")

            # Create raw message
            raw_message = RawMessage(
                id=f"slack_{event.get('ts', '')}",
                platform=self.platform,
                platform_message_id=event.get('ts', ''),
                thread_id=event.get('channel', ''),
                sender_id=event.get('user', ''),
                content=self._extract_message_content(event),
                timestamp=self._extract_timestamp(event),
                raw_data=event
            )

            # Publish to event bus if available
            if self.event_bus:
                event_obj = Event(
                    type=EventType.MESSAGE_RECEIVED,
                    data={
                        'platform': self.platform,
                        'message': raw_message.__dict__
                    },
                    source=f"{self.platform}_connector"
                )

                await self.event_bus.publish('messages.raw', event_obj)
                logger.debug(
                    f"Published new Slack message to event bus: {raw_message.id}")

        except Exception as e:
            logger.error(f"Error processing message event: {e}")

    async def _get_all_channels(self) -> List[Dict[str, Any]]:
        """Get all channels for historical message fetching."""
        channels = []

        # Get public and private channels
        response = await self._make_api_call(
            'conversations.list',
            params={
                'types': 'public_channel,private_channel',
                'exclude_archived': True
            }
        )

        if response.get('ok'):
            channels.extend(response.get('channels', []))

        # Get direct messages if enabled
        if self.include_direct_messages:
            dm_response = await self._make_api_call(
                'conversations.list',
                params={
                    'types': 'im,mpim',
                    'exclude_archived': True
                }
            )

            if dm_response.get('ok'):
                channels.extend(dm_response.get('channels', []))

        return channels

    async def _fetch_channel_history(
        self,
        channel_id: str,
        cursor: Optional[str] = None,
        limit: int = 100
    ) -> List[RawMessage]:
        """Fetch message history for a specific channel."""
        try:
            params = {
                'channel': channel_id,
                'limit': min(limit, self.max_results)
            }

            if cursor:
                params['cursor'] = cursor

            response = await self._make_api_call('conversations.history', params=params)

            if not response.get('ok'):
                logger.warning(
                    f"Failed to fetch history for channel {channel_id}: {response.get('error')}")
                return []

            messages = response.get('messages', [])
            raw_messages = []

            for message in messages:
                # Skip bot messages and certain subtypes
                if (message.get('bot_id') or
                        message.get('subtype') in ['bot_message', 'channel_join', 'channel_leave']):
                    continue

                raw_message = RawMessage(
                    id=f"slack_{message.get('ts', '')}",
                    platform=self.platform,
                    platform_message_id=message.get('ts', ''),
                    thread_id=channel_id,
                    sender_id=message.get('user', ''),
                    content=self._extract_message_content(message),
                    timestamp=self._extract_timestamp(message),
                    raw_data=message
                )

                raw_messages.append(raw_message)

            return raw_messages

        except Exception as e:
            logger.error(
                f"Error fetching channel history for {channel_id}: {e}")
            return []

    async def _make_api_call(
        self,
        method: str,
        params: Optional[Dict[str, Any]] = None,
        token: Optional[str] = None
    ) -> Dict[str, Any]:
        """Make a Slack API call."""
        if not self._session:
            raise SlackConnectorError("HTTP session not initialized")

        url = f"{self.api_base_url}/{method}"
        headers = {
            'Authorization': f'Bearer {token or self.bot_token}',
            'Content-Type': 'application/json'
        }

        try:
            if params:
                response = await self._session.post(url, json=params, headers=headers)
            else:
                response = await self._session.post(url, headers=headers)

            response.raise_for_status()
            return await response.json()

        except aiohttp.ClientError as e:
            logger.error(f"Slack API call failed for {method}: {e}")
            raise SlackConnectorError(f"API call failed: {e}")

    def _extract_message_content(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Extract content from Slack message."""
        content = {
            'text': message.get('text', ''),
            'attachments': []
        }

        # Handle file attachments
        files = message.get('files', [])
        for file_info in files:
            content['attachments'].append({
                'id': file_info.get('id'),
                'name': file_info.get('name'),
                'mimetype': file_info.get('mimetype'),
                'size': file_info.get('size'),
                'url': file_info.get('url_private'),
                'permalink': file_info.get('permalink')
            })

        # Handle message attachments (rich content)
        attachments = message.get('attachments', [])
        for attachment in attachments:
            content['attachments'].append({
                'type': 'rich_content',
                'title': attachment.get('title'),
                'text': attachment.get('text'),
                'color': attachment.get('color'),
                'fields': attachment.get('fields', [])
            })

        return content

    def _extract_timestamp(self, message: Dict[str, Any]) -> datetime:
        """Extract timestamp from Slack message."""
        ts = message.get('ts')
        if ts:
            try:
                # Slack timestamps are in seconds with decimal precision
                timestamp = datetime.fromtimestamp(float(ts), tz=timezone.utc)
                return timestamp
            except (ValueError, TypeError):
                pass

        return datetime.now(timezone.utc)

    async def _validate_webhook_signature(self, payload: Dict[str, Any]) -> None:
        """Validate webhook signature from Slack."""
        # Implementation would verify the signature using signing_secret
        # This is a placeholder for webhook validation logic
        if self.signing_secret:
            logger.debug("Webhook signature validation not fully implemented")

    async def _platform_health_check(self) -> None:
        """Slack-specific health check."""
        try:
            if not self.bot_token:
                raise SlackConnectorError("Bot token not available")

            # Test API access
            response = await self._make_api_call('auth.test')

            if not response.get('ok'):
                raise SlackConnectorError(
                    f"API test failed: {response.get('error')}")

            logger.debug(
                f"Slack health check passed for team: {response.get('team')}")

        except Exception as e:
            logger.error(f"Slack health check failed: {e}")
            raise SlackConnectorError(f"Health check failed: {e}")

    def get_channel_info(self, channel_id: str) -> Optional[Dict[str, Any]]:
        """Get channel information from cache."""
        return self._channels_cache.get(channel_id)

    def get_user_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user information from cache."""
        return self._users_cache.get(user_id)

    def get_team_info(self) -> Optional[Dict[str, Any]]:
        """Get team information."""
        return self._team_info
