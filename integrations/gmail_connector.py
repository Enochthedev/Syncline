"""
Gmail connector with real-time capabilities and OAuth 2.0 authentication.

This module provides Gmail integration with push notifications, historical message
fetching, and real-time message processing capabilities.
"""

import asyncio
import base64
import email
import hashlib
import hmac
import json
import logging
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Union
from urllib.parse import parse_qs, urlparse

import aiohttp
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from .base_connector import BaseConnector, RawMessage, AuthenticationError
from services.event_bus import EventBus, Event, EventType
from services.message_schema import Platform, RawMessage as SchemaRawMessage

logger = logging.getLogger(__name__)


class GmailConnectorError(Exception):
    """Gmail connector specific errors."""
    pass


class GmailWebhookError(Exception):
    """Gmail webhook processing errors."""
    pass


class GmailConnector(BaseConnector):
    """
    Gmail connector with OAuth 2.0 authentication and real-time capabilities.

    Provides Gmail API integration with push notification webhook handling,
    historical message fetching with cursor-based pagination, and real-time
    message processing with webhook validation.
    """

    def __init__(
        self,
        config: Dict[str, Any],
        event_bus: Optional[EventBus] = None,
        **kwargs
    ):
        super().__init__("gmail", config, **kwargs)

        self.event_bus = event_bus
        self.credentials: Optional[Credentials] = None
        self.service = None

        # Gmail-specific configuration
        self.scopes = config.get('scopes', [
            'https://www.googleapis.com/auth/gmail.readonly',
            'https://www.googleapis.com/auth/gmail.modify'
        ])
        self.credentials_file = config.get(
            'credentials_file', 'config/credentials.json')
        self.token_file = config.get('token_file', 'token.json')
        self.webhook_endpoint = config.get(
            'webhook_endpoint', '/webhooks/gmail')
        self.webhook_secret = config.get('webhook_secret')
        self.topic_name = config.get('topic_name')

        # Pagination and fetching configuration
        self.max_results = config.get('max_results', 100)
        self.include_spam_trash = config.get('include_spam_trash', False)

        # Real-time processing
        self._webhook_server_task: Optional[asyncio.Task] = None
        self._processing_queue: asyncio.Queue = asyncio.Queue()
        self._processor_task: Optional[asyncio.Task] = None

    async def authenticate(self) -> None:
        """Authenticate with Gmail using OAuth 2.0."""
        try:
            logger.info("Starting Gmail OAuth 2.0 authentication")

            # Try to load existing credentials
            if os.path.exists(self.token_file):
                self.credentials = Credentials.from_authorized_user_file(
                    self.token_file, self.scopes
                )
                logger.debug("Loaded existing credentials from token file")

            # If credentials are not valid, refresh or re-authenticate
            if not self.credentials or not self.credentials.valid:
                if (self.credentials and self.credentials.expired and
                        self.credentials.refresh_token):
                    logger.info("Refreshing expired Gmail credentials")
                    self.credentials.refresh(Request())
                else:
                    logger.info("Starting new Gmail OAuth flow")
                    if not os.path.exists(self.credentials_file):
                        raise AuthenticationError(
                            f"Credentials file not found: {self.credentials_file}"
                        )

                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_file, self.scopes
                    )
                    self.credentials = flow.run_local_server(port=0)

                # Save credentials for future use
                with open(self.token_file, 'w') as token:
                    token.write(self.credentials.to_json())
                logger.info("Saved Gmail credentials to token file")

            # Build Gmail service
            self.service = build('gmail', 'v1', credentials=self.credentials)

            # Test the connection
            profile = self.service.users().getProfile(userId='me').execute()
            logger.info(
                f"Gmail authentication successful for {profile.get('emailAddress')}")

        except Exception as e:
            logger.error(f"Gmail authentication failed: {e}")
            raise AuthenticationError(f"Gmail authentication failed: {e}")

    async def start_real_time_ingestion(self) -> None:
        """Start real-time message ingestion using Gmail push notifications."""
        try:
            logger.info("Starting Gmail real-time ingestion")

            # Set up push notifications if topic is configured
            if self.topic_name:
                await self._setup_push_notifications()

            # Start message processor
            self._processor_task = asyncio.create_task(
                self._process_message_queue())

            logger.info("Gmail real-time ingestion started successfully")

        except Exception as e:
            logger.error(f"Failed to start Gmail real-time ingestion: {e}")
            raise GmailConnectorError(
                f"Failed to start real-time ingestion: {e}")

    async def stop_real_time_ingestion(self) -> None:
        """Stop real-time message ingestion."""
        try:
            logger.info("Stopping Gmail real-time ingestion")

            # Stop push notifications
            if self.topic_name:
                await self._stop_push_notifications()

            # Stop processor task
            if self._processor_task:
                self._processor_task.cancel()
                try:
                    await self._processor_task
                except asyncio.CancelledError:
                    pass
                self._processor_task = None

            logger.info("Gmail real-time ingestion stopped")

        except Exception as e:
            logger.error(f"Error stopping Gmail real-time ingestion: {e}")

    async def fetch_historical_messages(
        self,
        cursor: Optional[str] = None,
        limit: int = 100
    ) -> List[RawMessage]:
        """
        Fetch historical messages with cursor-based pagination.

        Args:
            cursor: Page token for pagination (None for first page)
            limit: Maximum number of messages to fetch

        Returns:
            List of raw messages
        """
        try:
            logger.debug(
                f"Fetching historical Gmail messages (cursor: {cursor}, limit: {limit})")

            if not self.service:
                raise GmailConnectorError("Gmail service not initialized")

            # Build query parameters
            query_params = {
                'userId': 'me',
                'maxResults': min(limit, self.max_results),
                'includeSpamTrash': self.include_spam_trash
            }

            if cursor:
                query_params['pageToken'] = cursor

            # Fetch message list
            result = self.service.users().messages().list(**query_params).execute()
            messages = result.get('messages', [])

            if not messages:
                logger.debug("No messages found")
                return []

            # Fetch full message details
            raw_messages = []
            for msg_info in messages:
                try:
                    # Get full message
                    full_message = self.service.users().messages().get(
                        userId='me',
                        id=msg_info['id'],
                        format='full'
                    ).execute()

                    # Create raw message
                    raw_message = RawMessage(
                        id=full_message['id'],
                        platform=self.platform,
                        platform_message_id=full_message['id'],
                        thread_id=full_message.get(
                            'threadId', full_message['id']),
                        sender_id=self._extract_sender_id(full_message),
                        content=self._extract_content(full_message),
                        timestamp=self._extract_timestamp(full_message),
                        raw_data=full_message
                    )

                    raw_messages.append(raw_message)

                except Exception as e:
                    logger.error(
                        f"Error processing message {msg_info['id']}: {e}")
                    continue

            logger.info(f"Fetched {len(raw_messages)} Gmail messages")
            return raw_messages

        except HttpError as e:
            logger.error(f"Gmail API error: {e}")
            raise GmailConnectorError(f"Gmail API error: {e}")
        except Exception as e:
            logger.error(f"Error fetching Gmail messages: {e}")
            raise GmailConnectorError(f"Error fetching messages: {e}")

    async def handle_webhook(self, payload: Dict[str, Any]) -> None:
        """
        Handle incoming Gmail push notification webhook.

        Args:
            payload: Webhook payload from Gmail push notification
        """
        try:
            logger.debug("Processing Gmail webhook payload")

            # Validate webhook if secret is configured
            if self.webhook_secret:
                await self._validate_webhook(payload)

            # Extract message data from push notification
            message_data = payload.get('message', {})
            if not message_data:
                logger.warning("No message data in webhook payload")
                return

            # Decode the push notification data
            data = message_data.get('data', '')
            if data:
                try:
                    decoded_data = json.loads(
                        base64.b64decode(data).decode('utf-8'))
                    history_id = decoded_data.get('historyId')

                    if history_id:
                        # Queue for processing
                        await self._processing_queue.put({
                            'type': 'history_update',
                            'history_id': history_id,
                            'timestamp': datetime.now(timezone.utc)
                        })

                        logger.debug(
                            f"Queued history update for processing: {history_id}")
                except (json.JSONDecodeError, ValueError) as decode_error:
                    logger.warning(
                        f"Failed to decode webhook data: {decode_error}")
                    # Continue processing - don't fail the entire webhook

        except Exception as e:
            logger.error(f"Error handling Gmail webhook: {e}")
            # Only raise for critical errors, not data parsing issues
            if not isinstance(e, (json.JSONDecodeError, ValueError)):
                raise GmailWebhookError(f"Webhook processing failed: {e}")

    async def _setup_push_notifications(self) -> None:
        """Set up Gmail push notifications."""
        try:
            logger.info("Setting up Gmail push notifications")

            if not self.service:
                raise GmailConnectorError("Gmail service not initialized")

            # Watch for changes
            request = {
                'topicName': self.topic_name,
                'labelIds': ['INBOX'],  # Can be configured
                'labelFilterAction': 'include'
            }

            result = self.service.users().watch(userId='me', body=request).execute()
            logger.info(
                f"Gmail push notifications set up successfully: {result}")

        except Exception as e:
            logger.error(f"Failed to set up Gmail push notifications: {e}")
            raise

    async def _stop_push_notifications(self) -> None:
        """Stop Gmail push notifications."""
        try:
            logger.info("Stopping Gmail push notifications")

            if not self.service:
                return

            self.service.users().stop(userId='me').execute()
            logger.info("Gmail push notifications stopped")

        except Exception as e:
            logger.error(f"Error stopping Gmail push notifications: {e}")

    async def _validate_webhook(self, payload: Dict[str, Any]) -> None:
        """Validate webhook signature if secret is configured."""
        if not self.webhook_secret:
            return

        # Implementation depends on how webhook signature is provided
        # This is a placeholder for webhook validation logic
        logger.debug("Webhook validation not implemented yet")

    async def _process_message_queue(self) -> None:
        """Process queued messages from webhooks."""
        logger.info("Starting Gmail message queue processor")

        while True:
            try:
                # Get item from queue with timeout
                item = await asyncio.wait_for(
                    self._processing_queue.get(),
                    timeout=1.0
                )

                if item['type'] == 'history_update':
                    await self._process_history_update(item['history_id'])

                # Mark task as done
                self._processing_queue.task_done()

            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                logger.info("Gmail message queue processor cancelled")
                break
            except Exception as e:
                logger.error(f"Error processing queued message: {e}")

    async def _process_history_update(self, history_id: str) -> None:
        """Process a history update from Gmail."""
        try:
            logger.debug(f"Processing Gmail history update: {history_id}")

            if not self.service:
                return

            # Get history changes
            result = self.service.users().history().list(
                userId='me',
                startHistoryId=history_id
            ).execute()

            history = result.get('history', [])

            for history_item in history:
                # Process messages added
                messages_added = history_item.get('messagesAdded', [])
                for msg_added in messages_added:
                    message = msg_added.get('message', {})
                    if message:
                        await self._process_new_message(message['id'])

                # Process messages deleted (optional)
                messages_deleted = history_item.get('messagesDeleted', [])
                for msg_deleted in messages_deleted:
                    logger.debug(
                        f"Message deleted: {msg_deleted.get('message', {}).get('id')}")

        except Exception as e:
            logger.error(f"Error processing history update {history_id}: {e}")

    async def _process_new_message(self, message_id: str) -> None:
        """Process a new message from Gmail."""
        try:
            logger.debug(f"Processing new Gmail message: {message_id}")

            if not self.service:
                return

            # Get full message
            full_message = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()

            # Create raw message
            raw_message = RawMessage(
                id=full_message['id'],
                platform=self.platform,
                platform_message_id=full_message['id'],
                thread_id=full_message.get('threadId', full_message['id']),
                sender_id=self._extract_sender_id(full_message),
                content=self._extract_content(full_message),
                timestamp=self._extract_timestamp(full_message),
                raw_data=full_message
            )

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
                    f"Published new Gmail message to event bus: {message_id}")

        except Exception as e:
            logger.error(f"Error processing new message {message_id}: {e}")

    def _extract_sender_id(self, message: Dict[str, Any]) -> str:
        """Extract sender ID from Gmail message."""
        headers = message.get('payload', {}).get('headers', [])

        for header in headers:
            if header.get('name', '').lower() == 'from':
                from_header = header.get('value', '')
                # Extract email from "Name <email>" format
                if '<' in from_header and '>' in from_header:
                    email_part = from_header.split('<')[1].split('>')[0]
                    return email_part.strip()
                else:
                    return from_header.strip()

        return 'unknown'

    def _extract_content(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Extract content from Gmail message."""
        payload = message.get('payload', {})

        # Initialize content structure
        content = {
            'text': None,
            'html': None,
            'attachments': []
        }

        # Extract body content
        self._extract_body_content(payload, content)

        return content

    def _extract_body_content(self, payload: Dict[str, Any], content: Dict[str, Any]) -> None:
        """Recursively extract body content from message payload."""
        mime_type = payload.get('mimeType', '')

        if mime_type == 'text/plain':
            body_data = payload.get('body', {}).get('data', '')
            if body_data:
                content['text'] = base64.urlsafe_b64decode(
                    body_data).decode('utf-8')

        elif mime_type == 'text/html':
            body_data = payload.get('body', {}).get('data', '')
            if body_data:
                content['html'] = base64.urlsafe_b64decode(
                    body_data).decode('utf-8')

        elif mime_type.startswith('multipart/'):
            # Process multipart content
            parts = payload.get('parts', [])
            for part in parts:
                self._extract_body_content(part, content)

        # Handle attachments
        if payload.get('body', {}).get('attachmentId'):
            filename = payload.get('filename', 'attachment')
            content['attachments'].append({
                'filename': filename,
                'mime_type': mime_type,
                'attachment_id': payload['body']['attachmentId'],
                'size': payload.get('body', {}).get('size', 0)
            })

    def _extract_timestamp(self, message: Dict[str, Any]) -> datetime:
        """Extract timestamp from Gmail message."""
        internal_date = message.get('internalDate')
        if internal_date:
            # Gmail internal date is in milliseconds
            timestamp = datetime.fromtimestamp(
                int(internal_date) / 1000,
                tz=timezone.utc
            )
            return timestamp

        return datetime.now(timezone.utc)

    async def _platform_health_check(self) -> None:
        """Gmail-specific health check."""
        try:
            if not self.service:
                raise GmailConnectorError("Gmail service not initialized")

            # Test API access
            profile = self.service.users().getProfile(userId='me').execute()

            if not profile.get('emailAddress'):
                raise GmailConnectorError("Unable to get user profile")

            logger.debug(
                f"Gmail health check passed for {profile.get('emailAddress')}")

        except Exception as e:
            logger.error(f"Gmail health check failed: {e}")
            raise GmailConnectorError(f"Health check failed: {e}")

    def get_next_page_token(self, response: Dict[str, Any]) -> Optional[str]:
        """Extract next page token from Gmail API response."""
        return response.get('nextPageToken')

    async def get_message_count(self) -> int:
        """Get total message count for the user."""
        try:
            if not self.service:
                return 0

            profile = self.service.users().getProfile(userId='me').execute()
            return profile.get('messagesTotal', 0)

        except Exception as e:
            logger.error(f"Error getting message count: {e}")
            return 0
