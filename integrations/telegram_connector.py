"""
Telegram connector with Bot API integration.

This module provides Telegram integration with Bot API authentication,
webhook handling for real-time message processing, user-bot functionality
for personal message access, and message history fetching with proper
offset management.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Union
from urllib.parse import urljoin

import aiohttp
from telegram import Bot, Update, Message as TelegramMessage
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from telegram.error import TelegramError, BadRequest, Forbidden, NetworkError

from .base_connector import BaseConnector, RawMessage, AuthenticationError, RateLimitError
from services.event_bus import EventBus, Event, EventType
from services.message_schema import Platform, RawMessage as SchemaRawMessage

logger = logging.getLogger(__name__)


class TelegramConnectorError(Exception):
    """Telegram connector specific errors."""
    pass


class TelegramWebhookError(Exception):
    """Telegram webhook processing errors."""
    pass


class TelegramConnector(BaseConnector):
    """
    Telegram connector with Bot API integration.

    Provides Telegram Bot API integration with bot authentication, webhook handling
    for real-time message processing, user-bot functionality for personal message
    access, and message history fetching with proper offset management.
    """

    def __init__(
        self,
        config: Dict[str, Any],
        event_bus: Optional[EventBus] = None,
        **kwargs
    ):
        super().__init__("telegram", config, **kwargs)

        self.event_bus = event_bus

        # Telegram Bot API configuration
        self.bot_token = config.get('bot_token')
        self.webhook_url = config.get('webhook_url')
        self.webhook_secret = config.get('webhook_secret')
        self.webhook_path = config.get('webhook_path', '/webhooks/telegram')

        # Bot configuration
        self.allowed_updates = config.get('allowed_updates', [
            'message', 'edited_message', 'channel_post', 'edited_channel_post'
        ])
        self.drop_pending_updates = config.get('drop_pending_updates', True)

        # API configuration
        self.api_base_url = "https://api.telegram.org"
        self.max_connections = config.get('max_connections', 40)
        self.read_timeout = config.get('read_timeout', 30)
        self.write_timeout = config.get('write_timeout', 30)
        self.connect_timeout = config.get('connect_timeout', 30)

        # Message fetching configuration
        self.max_messages_per_request = config.get(
            'max_messages_per_request', 100)
        self.include_private_chats = config.get('include_private_chats', True)
        self.include_group_chats = config.get('include_group_chats', True)
        self.include_channels = config.get('include_channels', True)

        # Bot instances
        self.bot: Optional[Bot] = None
        self.application: Optional[Application] = None

        # Processing queue and tasks
        self._processing_queue: asyncio.Queue = asyncio.Queue()
        self._processor_task: Optional[asyncio.Task] = None
        self._webhook_server_task: Optional[asyncio.Task] = None

        # State management
        self._last_update_id = 0
        self._polling_task: Optional[asyncio.Task] = None
        self._webhook_configured = False

        # Chat and user caches
        self._chats_cache: Dict[int, Dict[str, Any]] = {}
        self._users_cache: Dict[int, Dict[str, Any]] = {}
        self._bot_info: Optional[Dict[str, Any]] = None

        # Rate limiting
        self._message_rate_limit = 30  # messages per second
        self._last_message_time = datetime.now(timezone.utc)
        self._message_count = 0

    async def authenticate(self) -> None:
        """Authenticate with Telegram using bot token."""
        try:
            logger.info("Starting Telegram bot authentication")

            if not self.bot_token:
                raise AuthenticationError("Telegram bot token is required")

            # Initialize bot
            self.bot = Bot(token=self.bot_token)

            # Test bot token by getting bot info
            try:
                bot_info = await self.bot.get_me()
                self._bot_info = {
                    'id': bot_info.id,
                    'username': bot_info.username,
                    'first_name': bot_info.first_name,
                    'is_bot': bot_info.is_bot,
                    'can_join_groups': bot_info.can_join_groups,
                    'can_read_all_group_messages': bot_info.can_read_all_group_messages,
                    'supports_inline_queries': bot_info.supports_inline_queries
                }

                logger.info(
                    f"Telegram authentication successful for bot: @{bot_info.username} ({bot_info.first_name})"
                )

            except TelegramError as e:
                raise AuthenticationError(f"Invalid Telegram bot token: {e}")

            # Initialize application for webhook handling
            self.application = Application.builder().token(self.bot_token).build()

            # Add message handlers
            self.application.add_handler(
                MessageHandler(filters.ALL, self._handle_telegram_message)
            )

        except Exception as e:
            logger.error(f"Telegram authentication failed: {e}")
            raise AuthenticationError(f"Telegram authentication failed: {e}")

    async def start_real_time_ingestion(self) -> None:
        """Start real-time message ingestion using webhooks or polling."""
        try:
            logger.info("Starting Telegram real-time ingestion")

            # Start message processor
            self._processor_task = asyncio.create_task(
                self._process_message_queue()
            )

            # Set up webhooks if URL is configured, otherwise use polling
            if self.webhook_url:
                await self._setup_webhook()
            else:
                await self._start_polling()

            logger.info("Telegram real-time ingestion started successfully")

        except Exception as e:
            logger.error(f"Failed to start Telegram real-time ingestion: {e}")
            raise TelegramConnectorError(
                f"Failed to start real-time ingestion: {e}"
            )

    async def stop_real_time_ingestion(self) -> None:
        """Stop real-time message ingestion."""
        try:
            logger.info("Stopping Telegram real-time ingestion")

            # Stop polling if active
            if self._polling_task:
                self._polling_task.cancel()
                try:
                    await self._polling_task
                except asyncio.CancelledError:
                    pass
                self._polling_task = None

            # Remove webhook if configured
            if self._webhook_configured:
                await self._remove_webhook()

            # Stop webhook server if running
            if self._webhook_server_task:
                self._webhook_server_task.cancel()
                try:
                    await self._webhook_server_task
                except asyncio.CancelledError:
                    pass
                self._webhook_server_task = None

            # Stop processor task
            if self._processor_task:
                self._processor_task.cancel()
                try:
                    await self._processor_task
                except asyncio.CancelledError:
                    pass
                self._processor_task = None

            # Stop application
            if self.application:
                await self.application.stop()
                await self.application.shutdown()

            logger.info("Telegram real-time ingestion stopped")

        except Exception as e:
            logger.error(f"Error stopping Telegram real-time ingestion: {e}")

    async def fetch_historical_messages(
        self,
        cursor: Optional[str] = None,
        limit: int = 100
    ) -> List[RawMessage]:
        """
        Fetch historical messages with offset-based pagination.

        Args:
            cursor: Update offset to start from (None for latest)
            limit: Maximum number of messages to fetch

        Returns:
            List of raw messages
        """
        try:
            logger.debug(
                f"Fetching historical Telegram messages (cursor: {cursor}, limit: {limit})"
            )

            if not self.bot:
                raise TelegramConnectorError("Bot not initialized")

            raw_messages = []
            offset = int(cursor) if cursor else 0

            # Get updates using getUpdates method
            try:
                updates = await self.bot.get_updates(
                    offset=offset,
                    limit=min(limit, self.max_messages_per_request),
                    timeout=10,
                    allowed_updates=self.allowed_updates
                )

                for update in updates:
                    try:
                        raw_message = await self._process_update_to_raw_message(update)
                        if raw_message:
                            raw_messages.append(raw_message)

                        # Update offset for next request
                        self._last_update_id = max(
                            self._last_update_id, update.update_id)

                    except Exception as e:
                        logger.error(
                            f"Error processing update {update.update_id}: {e}")
                        continue

                logger.info(f"Fetched {len(raw_messages)} Telegram messages")
                return raw_messages

            except TelegramError as e:
                logger.error(f"Error fetching Telegram updates: {e}")
                raise TelegramConnectorError(f"Error fetching updates: {e}")

        except Exception as e:
            logger.error(f"Error fetching Telegram messages: {e}")
            raise TelegramConnectorError(f"Error fetching messages: {e}")

    async def handle_webhook(self, payload: Dict[str, Any]) -> None:
        """
        Handle incoming Telegram webhook payload.

        Args:
            payload: Webhook payload from Telegram
        """
        try:
            logger.debug("Processing Telegram webhook payload")

            # Validate webhook secret if configured
            if self.webhook_secret:
                await self._validate_webhook_signature(payload)

            # Parse update from webhook payload
            try:
                update = Update.de_json(payload, self.bot)
                if update:
                    await self._processing_queue.put({
                        'type': 'webhook_update',
                        'update': update,
                        'timestamp': datetime.now(timezone.utc)
                    })
                else:
                    logger.warning(
                        "Failed to parse Telegram update from webhook")

            except Exception as e:
                logger.error(f"Error parsing Telegram webhook update: {e}")
                raise TelegramWebhookError(f"Failed to parse update: {e}")

        except Exception as e:
            logger.error(f"Error handling Telegram webhook: {e}")
            raise TelegramWebhookError(f"Webhook processing failed: {e}")

    async def _setup_webhook(self) -> None:
        """Set up Telegram webhook for real-time updates."""
        try:
            logger.info(f"Setting up Telegram webhook: {self.webhook_url}")

            if not self.bot:
                raise TelegramConnectorError("Bot not initialized")

            # Construct full webhook URL
            webhook_url = urljoin(self.webhook_url, self.webhook_path)

            # Set webhook
            success = await self.bot.set_webhook(
                url=webhook_url,
                allowed_updates=self.allowed_updates,
                drop_pending_updates=self.drop_pending_updates,
                secret_token=self.webhook_secret
            )

            if success:
                self._webhook_configured = True
                logger.info(
                    f"Telegram webhook configured successfully: {webhook_url}")
            else:
                raise TelegramConnectorError("Failed to set Telegram webhook")

        except TelegramError as e:
            logger.error(f"Error setting up Telegram webhook: {e}")
            raise TelegramConnectorError(f"Webhook setup failed: {e}")

    async def _remove_webhook(self) -> None:
        """Remove Telegram webhook."""
        try:
            logger.info("Removing Telegram webhook")

            if not self.bot:
                return

            success = await self.bot.delete_webhook(drop_pending_updates=True)
            if success:
                self._webhook_configured = False
                logger.info("Telegram webhook removed successfully")
            else:
                logger.warning("Failed to remove Telegram webhook")

        except TelegramError as e:
            logger.error(f"Error removing Telegram webhook: {e}")

    async def _start_polling(self) -> None:
        """Start polling for updates when webhook is not available."""
        try:
            logger.info("Starting Telegram polling for updates")

            self._polling_task = asyncio.create_task(self._polling_loop())

        except Exception as e:
            logger.error(f"Error starting Telegram polling: {e}")
            raise TelegramConnectorError(f"Polling setup failed: {e}")

    async def _polling_loop(self) -> None:
        """Main polling loop for getting updates."""
        logger.info("Starting Telegram polling loop")

        while self._running:
            try:
                # Get updates
                updates = await self.bot.get_updates(
                    offset=self._last_update_id + 1,
                    limit=100,
                    timeout=30,
                    allowed_updates=self.allowed_updates
                )

                for update in updates:
                    try:
                        await self._processing_queue.put({
                            'type': 'polling_update',
                            'update': update,
                            'timestamp': datetime.now(timezone.utc)
                        })

                        # Update offset
                        self._last_update_id = max(
                            self._last_update_id, update.update_id)

                    except Exception as e:
                        logger.error(
                            f"Error queuing update {update.update_id}: {e}")

                # Small delay to prevent excessive API calls
                if not updates:
                    await asyncio.sleep(1)

            except asyncio.CancelledError:
                logger.info("Telegram polling loop cancelled")
                break
            except TelegramError as e:
                logger.error(f"Telegram polling error: {e}")
                await asyncio.sleep(5)  # Wait before retrying
            except Exception as e:
                logger.error(f"Unexpected error in polling loop: {e}")
                await asyncio.sleep(5)

    async def _handle_telegram_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle incoming Telegram message from webhook."""
        try:
            await self._processing_queue.put({
                'type': 'message_handler',
                'update': update,
                'timestamp': datetime.now(timezone.utc)
            })
        except Exception as e:
            logger.error(f"Error handling Telegram message: {e}")

    async def _process_message_queue(self) -> None:
        """Process queued messages from webhooks and polling."""
        logger.info("Starting Telegram message queue processor")

        while True:
            try:
                # Get item from queue with timeout
                item = await asyncio.wait_for(
                    self._processing_queue.get(),
                    timeout=1.0
                )

                update = item['update']
                await self._process_telegram_update(update)

                # Mark task as done
                self._processing_queue.task_done()

            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                logger.info("Telegram message queue processor cancelled")
                break
            except Exception as e:
                logger.error(f"Error processing queued message: {e}")

    async def _process_telegram_update(self, update: Update) -> None:
        """Process a Telegram update and convert to raw message."""
        try:
            raw_message = await self._process_update_to_raw_message(update)
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
                    f"Published new Telegram message to event bus: {raw_message.id}"
                )

        except Exception as e:
            logger.error(f"Error processing Telegram update: {e}")

    async def _process_update_to_raw_message(self, update: Update) -> Optional[RawMessage]:
        """Convert Telegram update to RawMessage."""
        try:
            message = None

            # Extract message from different update types
            if update.message:
                message = update.message
            elif update.edited_message:
                message = update.edited_message
            elif update.channel_post:
                message = update.channel_post
            elif update.edited_channel_post:
                message = update.edited_channel_post
            else:
                # Skip non-message updates
                return None

            # Skip messages from bots (except channels)
            if message.from_user and message.from_user.is_bot and not message.chat.type == 'channel':
                return None

            # Cache chat and user information
            await self._cache_chat_info(message.chat)
            if message.from_user:
                await self._cache_user_info(message.from_user)

            # Extract message content
            content = await self._extract_message_content(message)

            # Create raw message
            raw_message = RawMessage(
                id=f"telegram_{message.message_id}_{message.chat.id}",
                platform=self.platform,
                platform_message_id=str(message.message_id),
                thread_id=str(message.chat.id),
                sender_id=str(message.from_user.id) if message.from_user else str(
                    message.chat.id),
                content=content,
                timestamp=message.date.replace(tzinfo=timezone.utc),
                metadata={
                    'chat_type': message.chat.type,
                    'chat_title': message.chat.title,
                    'message_thread_id': message.message_thread_id,
                    'reply_to_message_id': message.reply_to_message.message_id if message.reply_to_message else None,
                    'forward_from': self._extract_forward_info(message),
                    'edit_date': message.edit_date.isoformat() if message.edit_date else None,
                    'via_bot': message.via_bot.username if message.via_bot else None
                },
                raw_data=message.to_dict()
            )

            logger.debug(f"Processed Telegram message: {raw_message.id}")
            return raw_message

        except Exception as e:
            logger.error(
                f"Error converting Telegram update to raw message: {e}")
            return None

    async def _extract_message_content(self, message: TelegramMessage) -> Dict[str, Any]:
        """Extract content from Telegram message."""
        content = {
            'text': message.text or message.caption or '',
            'html': None,
            'markdown': None,
            'attachments': [],
            'entities': []
        }

        # Extract text entities (mentions, hashtags, etc.)
        if message.entities:
            for entity in message.entities:
                content['entities'].append({
                    'type': entity.type,
                    'offset': entity.offset,
                    'length': entity.length,
                    'url': entity.url,
                    'user': entity.user.to_dict() if entity.user else None,
                    'language': entity.language
                })

        # Extract attachments
        attachments = []

        # Photos
        if message.photo:
            largest_photo = max(message.photo, key=lambda p: p.file_size or 0)
            attachments.append({
                'type': 'photo',
                'file_id': largest_photo.file_id,
                'file_unique_id': largest_photo.file_unique_id,
                'width': largest_photo.width,
                'height': largest_photo.height,
                'file_size': largest_photo.file_size
            })

        # Documents
        if message.document:
            attachments.append({
                'type': 'document',
                'file_id': message.document.file_id,
                'file_unique_id': message.document.file_unique_id,
                'file_name': message.document.file_name,
                'mime_type': message.document.mime_type,
                'file_size': message.document.file_size
            })

        # Audio
        if message.audio:
            attachments.append({
                'type': 'audio',
                'file_id': message.audio.file_id,
                'file_unique_id': message.audio.file_unique_id,
                'duration': message.audio.duration,
                'performer': message.audio.performer,
                'title': message.audio.title,
                'mime_type': message.audio.mime_type,
                'file_size': message.audio.file_size
            })

        # Video
        if message.video:
            attachments.append({
                'type': 'video',
                'file_id': message.video.file_id,
                'file_unique_id': message.video.file_unique_id,
                'width': message.video.width,
                'height': message.video.height,
                'duration': message.video.duration,
                'mime_type': message.video.mime_type,
                'file_size': message.video.file_size
            })

        # Voice
        if message.voice:
            attachments.append({
                'type': 'voice',
                'file_id': message.voice.file_id,
                'file_unique_id': message.voice.file_unique_id,
                'duration': message.voice.duration,
                'mime_type': message.voice.mime_type,
                'file_size': message.voice.file_size
            })

        # Video note
        if message.video_note:
            attachments.append({
                'type': 'video_note',
                'file_id': message.video_note.file_id,
                'file_unique_id': message.video_note.file_unique_id,
                'length': message.video_note.length,
                'duration': message.video_note.duration,
                'file_size': message.video_note.file_size
            })

        # Sticker
        if message.sticker:
            attachments.append({
                'type': 'sticker',
                'file_id': message.sticker.file_id,
                'file_unique_id': message.sticker.file_unique_id,
                'width': message.sticker.width,
                'height': message.sticker.height,
                'is_animated': message.sticker.is_animated,
                'is_video': message.sticker.is_video,
                'emoji': message.sticker.emoji,
                'set_name': message.sticker.set_name,
                'file_size': message.sticker.file_size
            })

        # Location
        if message.location:
            attachments.append({
                'type': 'location',
                'latitude': message.location.latitude,
                'longitude': message.location.longitude,
                'live_period': message.location.live_period,
                'heading': message.location.heading,
                'proximity_alert_radius': message.location.proximity_alert_radius
            })

        # Contact
        if message.contact:
            attachments.append({
                'type': 'contact',
                'phone_number': message.contact.phone_number,
                'first_name': message.contact.first_name,
                'last_name': message.contact.last_name,
                'user_id': message.contact.user_id,
                'vcard': message.contact.vcard
            })

        content['attachments'] = attachments
        return content

    def _extract_forward_info(self, message: TelegramMessage) -> Optional[Dict[str, Any]]:
        """Extract forward information from message."""
        if not message.forward_from and not message.forward_from_chat:
            return None

        forward_info = {
            'date': message.forward_date.isoformat() if message.forward_date else None,
            'from_user': None,
            'from_chat': None,
            'from_message_id': message.forward_from_message_id,
            'signature': message.forward_signature
        }

        if message.forward_from:
            forward_info['from_user'] = {
                'id': message.forward_from.id,
                'username': message.forward_from.username,
                'first_name': message.forward_from.first_name,
                'last_name': message.forward_from.last_name
            }

        if message.forward_from_chat:
            forward_info['from_chat'] = {
                'id': message.forward_from_chat.id,
                'type': message.forward_from_chat.type,
                'title': message.forward_from_chat.title,
                'username': message.forward_from_chat.username
            }

        return forward_info

    async def _cache_chat_info(self, chat) -> None:
        """Cache chat information."""
        try:
            self._chats_cache[chat.id] = {
                'id': chat.id,
                'type': chat.type,
                'title': chat.title,
                'username': chat.username,
                'first_name': chat.first_name,
                'last_name': chat.last_name,
                'description': chat.description,
                'invite_link': chat.invite_link,
                'pinned_message_id': chat.pinned_message.message_id if chat.pinned_message else None
            }
        except Exception as e:
            logger.error(f"Error caching chat info: {e}")

    async def _cache_user_info(self, user) -> None:
        """Cache user information."""
        try:
            self._users_cache[user.id] = {
                'id': user.id,
                'is_bot': user.is_bot,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'username': user.username,
                'language_code': user.language_code,
                'is_premium': user.is_premium,
                'added_to_attachment_menu': user.added_to_attachment_menu
            }
        except Exception as e:
            logger.error(f"Error caching user info: {e}")

    async def _validate_webhook_signature(self, payload: Dict[str, Any]) -> None:
        """Validate webhook signature if secret is configured."""
        # Telegram webhook signature validation would go here
        # For now, we'll skip this as it requires access to the raw request headers
        pass

    async def _platform_health_check(self) -> None:
        """Telegram-specific health check."""
        try:
            if not self.bot:
                raise TelegramConnectorError("Bot not initialized")

            # Test bot token by getting bot info
            bot_info = await self.bot.get_me()
            if not bot_info:
                raise TelegramConnectorError("Unable to get bot info")

            logger.debug(
                f"Telegram health check passed for @{bot_info.username}")

        except TelegramError as e:
            logger.error(f"Telegram health check failed: {e}")
            raise TelegramConnectorError(f"Health check failed: {e}")

    def get_next_page_cursor(self, last_update_id: int) -> str:
        """Get cursor for next page of updates."""
        return str(last_update_id + 1)

    def get_bot_info(self) -> Optional[Dict[str, Any]]:
        """Get bot information."""
        return self._bot_info

    def get_cached_chat(self, chat_id: int) -> Optional[Dict[str, Any]]:
        """Get cached chat information."""
        return self._chats_cache.get(chat_id)

    def get_cached_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get cached user information."""
        return self._users_cache.get(user_id)

    async def send_message(
        self,
        chat_id: Union[int, str],
        text: str,
        parse_mode: Optional[str] = None,
        reply_to_message_id: Optional[int] = None
    ) -> Optional[int]:
        """
        Send a message to a chat.

        Args:
            chat_id: Chat ID to send message to
            text: Message text
            parse_mode: Parse mode (HTML, Markdown, etc.)
            reply_to_message_id: ID of message to reply to

        Returns:
            Message ID if successful, None otherwise
        """
        try:
            if not self.bot:
                raise TelegramConnectorError("Bot not initialized")

            message = await self.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=parse_mode,
                reply_to_message_id=reply_to_message_id
            )

            logger.info(
                f"Sent Telegram message to {chat_id}: {message.message_id}")
            return message.message_id

        except TelegramError as e:
            logger.error(f"Error sending Telegram message: {e}")
            return None

    async def get_chat_member_count(self, chat_id: Union[int, str]) -> int:
        """Get the number of members in a chat."""
        try:
            if not self.bot:
                return 0

            count = await self.bot.get_chat_member_count(chat_id)
            return count

        except TelegramError as e:
            logger.error(f"Error getting chat member count: {e}")
            return 0
