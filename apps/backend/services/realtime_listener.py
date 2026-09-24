"""
Real-time Message Listener Service

Implements polling-based message collection for platforms that don't support webhooks.

Features:
- Configurable polling intervals per platform
- Efficient change detection to minimize API calls
- Automatic backoff on rate limits
- Concurrent polling for multiple connections
- State tracking for incremental updates
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.collection_job import CollectionJob, JobStatus, JobType
from db.models.platform_connection import ConnectionStatus, PlatformConnection
from db.models.raw_message import RawMessage
from integrations.base_connector import BaseConnector, RateLimitError
from services.event_bus import EventBus, get_event_bus
from services.events.types import Event, EventType

logger = logging.getLogger(__name__)


# =============================================================================
# Polling Configuration
# =============================================================================


class PlatformPollingConfig:
    """Polling configuration for different platforms."""

    # Default polling intervals in seconds
    INTERVALS = {
        "twitter": 60,  # Twitter: 1 minute
        "telegram": 30,  # Telegram: 30 seconds
        "gmail": 120,  # Gmail: 2 minutes (if not using push)
        "slack": 60,  # Slack: 1 minute (if not using RTM/Events API)
        "discord": 60,  # Discord: 1 minute (if not using gateway)
        "whatsapp": 30,  # WhatsApp: 30 seconds
    }

    # Minimum intervals to respect rate limits
    MIN_INTERVALS = {
        "twitter": 30,
        "telegram": 10,
        "gmail": 60,
        "slack": 30,
        "discord": 30,
        "whatsapp": 15,
    }

    # Maximum intervals for inactive connections
    MAX_INTERVALS = {
        "twitter": 300,  # 5 minutes
        "telegram": 120,  # 2 minutes
        "gmail": 600,  # 10 minutes
        "slack": 300,  # 5 minutes
        "discord": 300,  # 5 minutes
        "whatsapp": 180,  # 3 minutes
    }

    @classmethod
    def get_interval(cls, platform: str, custom_interval: Optional[int] = None) -> int:
        """
        Get polling interval for platform.

        Args:
            platform: Platform name
            custom_interval: Optional custom interval

        Returns:
            Polling interval in seconds
        """
        if custom_interval:
            min_interval = cls.MIN_INTERVALS.get(platform, 30)
            max_interval = cls.MAX_INTERVALS.get(platform, 600)
            return max(min_interval, min(custom_interval, max_interval))

        return cls.INTERVALS.get(platform, 60)


# =============================================================================
# Polling State Tracker
# =============================================================================


class PollingState:
    """
    Tracks polling state for a connection.

    Maintains information needed for efficient change detection:
    - Last poll timestamp
    - Last message ID/timestamp seen
    - Platform-specific cursors/tokens
    - Error tracking
    """

    def __init__(
        self,
        connection_id: UUID,
        platform: str,
        last_poll_at: Optional[datetime] = None,
        last_message_id: Optional[str] = None,
        last_message_timestamp: Optional[datetime] = None,
        platform_cursor: Optional[str] = None,
        consecutive_errors: int = 0,
        last_error: Optional[str] = None,
    ):
        """
        Initialize polling state.

        Args:
            connection_id: Platform connection ID
            platform: Platform name
            last_poll_at: Last successful poll timestamp
            last_message_id: Last message ID seen
            last_message_timestamp: Last message timestamp
            platform_cursor: Platform-specific cursor/token
            consecutive_errors: Number of consecutive errors
            last_error: Last error message
        """
        self.connection_id = connection_id
        self.platform = platform
        self.last_poll_at = last_poll_at
        self.last_message_id = last_message_id
        self.last_message_timestamp = last_message_timestamp
        self.platform_cursor = platform_cursor
        self.consecutive_errors = consecutive_errors
        self.last_error = last_error
        self.is_polling = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary for storage."""
        return {
            "last_poll_at": (
                self.last_poll_at.isoformat() if self.last_poll_at else None
            ),
            "last_message_id": self.last_message_id,
            "last_message_timestamp": (
                self.last_message_timestamp.isoformat()
                if self.last_message_timestamp
                else None
            ),
            "platform_cursor": self.platform_cursor,
            "consecutive_errors": self.consecutive_errors,
            "last_error": self.last_error,
        }

    @classmethod
    def from_dict(
        cls, connection_id: UUID, platform: str, data: Dict[str, Any]
    ) -> "PollingState":
        """Create state from dictionary."""
        return cls(
            connection_id=connection_id,
            platform=platform,
            last_poll_at=(
                datetime.fromisoformat(data["last_poll_at"])
                if data.get("last_poll_at")
                else None
            ),
            last_message_id=data.get("last_message_id"),
            last_message_timestamp=(
                datetime.fromisoformat(data["last_message_timestamp"])
                if data.get("last_message_timestamp")
                else None
            ),
            platform_cursor=data.get("platform_cursor"),
            consecutive_errors=data.get("consecutive_errors", 0),
            last_error=data.get("last_error"),
        )


# =============================================================================
# Real-time Listener
# =============================================================================


class RealtimeListener:
    """
    Service for polling-based real-time message collection.

    Features:
    - Configurable polling intervals per platform
    - Efficient change detection using timestamps/cursors
    - Automatic backoff on errors and rate limits
    - Concurrent polling for multiple connections
    - State persistence for resumability
    """

    def __init__(
        self,
        db: AsyncSession,
        event_bus: Optional[EventBus] = None,
        max_concurrent_polls: int = 10,
        backoff_multiplier: float = 2.0,
        max_backoff_seconds: int = 300,
    ):
        """
        Initialize realtime listener.

        Args:
            db: Database session
            event_bus: Event bus for publishing events
            max_concurrent_polls: Maximum concurrent polling tasks
            backoff_multiplier: Multiplier for exponential backoff
            max_backoff_seconds: Maximum backoff delay
        """
        self.db = db
        self.event_bus = event_bus or get_event_bus()
        self.max_concurrent_polls = max_concurrent_polls
        self.backoff_multiplier = backoff_multiplier
        self.max_backoff_seconds = max_backoff_seconds

        # Active polling tasks
        self._polling_tasks: Dict[UUID, asyncio.Task] = {}
        self._polling_states: Dict[UUID, PollingState] = {}
        self._polling_semaphore = asyncio.Semaphore(max_concurrent_polls)

        # Running state
        self._running = False

    async def start(self) -> None:
        """Start the realtime listener."""
        if self._running:
            logger.warning("Realtime listener already running")
            return

        self._running = True
        logger.info("Realtime listener started")

    async def stop(self) -> None:
        """Stop the realtime listener."""
        if not self._running:
            return

        self._running = False

        # Cancel all polling tasks
        for connection_id, task in list(self._polling_tasks.items()):
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        self._polling_tasks.clear()
        self._polling_states.clear()

        logger.info("Realtime listener stopped")

    async def start_polling(
        self,
        connection: PlatformConnection,
        connector: BaseConnector,
        poll_function: Callable,
        interval: Optional[int] = None,
    ) -> None:
        """
        Start polling for a connection.

        Args:
            connection: Platform connection
            connector: Platform connector instance
            poll_function: Platform-specific polling function
            interval: Optional custom polling interval in seconds
        """
        if connection.id in self._polling_tasks:
            logger.warning(f"Already polling connection {connection.id}")
            return

        # Load or create polling state
        state = await self._load_polling_state(connection)
        self._polling_states[connection.id] = state

        # Get polling interval
        poll_interval = PlatformPollingConfig.get_interval(
            connection.platform, interval
        )

        # Create polling task
        task = asyncio.create_task(
            self._poll_loop(
                connection=connection,
                connector=connector,
                poll_function=poll_function,
                interval=poll_interval,
            )
        )
        self._polling_tasks[connection.id] = task

        logger.info(
            f"Started polling for {connection.platform} "
            f"(connection={connection.id}, interval={poll_interval}s)"
        )

    async def stop_polling(self, connection_id: UUID) -> None:
        """
        Stop polling for a connection.

        Args:
            connection_id: Platform connection ID
        """
        if connection_id not in self._polling_tasks:
            logger.warning(f"Not polling connection {connection_id}")
            return

        # Cancel polling task
        task = self._polling_tasks[connection_id]
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        # Clean up
        del self._polling_tasks[connection_id]
        if connection_id in self._polling_states:
            # Save final state
            state = self._polling_states[connection_id]
            await self._save_polling_state(connection_id, state)
            del self._polling_states[connection_id]

        logger.info(f"Stopped polling for connection {connection_id}")

    async def get_polling_status(self, connection_id: UUID) -> Optional[Dict[str, Any]]:
        """
        Get polling status for a connection.

        Args:
            connection_id: Platform connection ID

        Returns:
            Status dictionary or None if not polling
        """
        if connection_id not in self._polling_states:
            return None

        state = self._polling_states[connection_id]

        return {
            "connection_id": str(connection_id),
            "platform": state.platform,
            "is_polling": state.is_polling,
            "last_poll_at": (
                state.last_poll_at.isoformat() if state.last_poll_at else None
            ),
            "last_message_id": state.last_message_id,
            "consecutive_errors": state.consecutive_errors,
            "last_error": state.last_error,
        }

    async def _poll_loop(
        self,
        connection: PlatformConnection,
        connector: BaseConnector,
        poll_function: Callable,
        interval: int,
    ) -> None:
        """
        Main polling loop for a connection.

        Args:
            connection: Platform connection
            connector: Platform connector
            poll_function: Platform-specific polling function
            interval: Polling interval in seconds
        """
        state = self._polling_states[connection.id]
        current_interval = interval

        try:
            while self._running:
                async with self._polling_semaphore:
                    state.is_polling = True

                    try:
                        # Perform poll
                        result = await self._poll_once(
                            connection=connection,
                            connector=connector,
                            poll_function=poll_function,
                            state=state,
                        )

                        # Update state on success
                        state.last_poll_at = datetime.utcnow()
                        state.consecutive_errors = 0
                        state.last_error = None

                        # Reset interval on success
                        current_interval = interval

                        # Save state
                        await self._save_polling_state(connection.id, state)

                        logger.debug(
                            f"Poll completed for {connection.platform} "
                            f"(connection={connection.id}): "
                            f"{result.get('new_messages', 0)} new messages"
                        )

                    except RateLimitError as e:
                        logger.warning(
                            f"Rate limit hit for {connection.platform} "
                            f"(connection={connection.id}), "
                            f"backing off for {e.retry_after or current_interval}s"
                        )
                        current_interval = min(
                            e.retry_after or current_interval * self.backoff_multiplier,
                            self.max_backoff_seconds,
                        )

                    except Exception as e:
                        logger.error(
                            f"Poll error for {connection.platform} "
                            f"(connection={connection.id}): {e}",
                            exc_info=True,
                        )

                        # Update error tracking
                        state.consecutive_errors += 1
                        state.last_error = str(e)

                        # Exponential backoff on errors
                        current_interval = min(
                            interval
                            * (self.backoff_multiplier**state.consecutive_errors),
                            self.max_backoff_seconds,
                        )

                        # Save error state
                        await self._save_polling_state(connection.id, state)

                    finally:
                        state.is_polling = False

                # Wait for next poll
                await asyncio.sleep(current_interval)

        except asyncio.CancelledError:
            logger.info(f"Polling cancelled for connection {connection.id}")
            raise
        except Exception as e:
            logger.error(
                f"Fatal error in poll loop for connection {connection.id}: {e}",
                exc_info=True,
            )

    async def _poll_once(
        self,
        connection: PlatformConnection,
        connector: BaseConnector,
        poll_function: Callable,
        state: PollingState,
    ) -> Dict[str, Any]:
        """
        Perform a single poll operation.

        Args:
            connection: Platform connection
            connector: Platform connector
            poll_function: Platform-specific polling function
            state: Current polling state

        Returns:
            Poll result dictionary
        """
        # Call platform-specific poll function
        result = await poll_function(
            connector=connector,
            since_timestamp=state.last_message_timestamp,
            since_id=state.last_message_id,
            cursor=state.platform_cursor,
        )

        messages = result.get("messages", [])
        new_count = 0

        # Process each message
        for msg_data in messages:
            try:
                # Extract message ID
                msg_id = self._extract_message_id(connection.platform, msg_data)

                if not msg_id:
                    logger.warning(f"Could not extract message ID from {msg_data}")
                    continue

                # Check if message already exists
                existing = await self._check_message_exists(connection.id, msg_id)

                if existing:
                    continue

                # Create raw message record
                raw_message = RawMessage(
                    connection_id=connection.id,
                    platform=connection.platform,
                    platform_message_id=msg_id,
                    raw_data=msg_data,
                    processed=False,
                )

                self.db.add(raw_message)
                new_count += 1

                # Update state with latest message
                msg_timestamp = self._extract_timestamp(connection.platform, msg_data)
                if msg_timestamp and (
                    not state.last_message_timestamp
                    or msg_timestamp > state.last_message_timestamp
                ):
                    state.last_message_timestamp = msg_timestamp
                    state.last_message_id = msg_id

                # Publish MESSAGE_COLLECTED event
                await self.event_bus.publish(
                    Event(
                        event_id=str(raw_message.id),
                        event_type=EventType.MESSAGE_COLLECTED,
                        source="realtime_listener",
                        payload={
                            "raw_message_id": str(raw_message.id),
                            "connection_id": str(connection.id),
                            "platform": connection.platform,
                            "platform_message_id": msg_id,
                            "source": "polling",
                        },
                    )
                )

            except Exception as e:
                logger.error(f"Error processing polled message: {e}", exc_info=True)

        # Commit all messages
        if new_count > 0:
            await self.db.commit()

        # Update cursor if provided
        if result.get("next_cursor"):
            state.platform_cursor = result["next_cursor"]

        return {
            "new_messages": new_count,
            "total_fetched": len(messages),
        }

    def _extract_message_id(
        self, platform: str, message_data: Dict[str, Any]
    ) -> Optional[str]:
        """Extract platform-specific message ID."""
        if platform == "twitter":
            return message_data.get("id_str") or str(message_data.get("id"))
        elif platform == "telegram":
            return str(message_data.get("message_id"))
        elif platform == "gmail":
            return message_data.get("id")
        elif platform == "slack":
            return message_data.get("ts") or message_data.get("client_msg_id")
        elif platform == "discord":
            return message_data.get("id")
        elif platform == "whatsapp":
            return message_data.get("id")
        else:
            return message_data.get("id")

    def _extract_timestamp(
        self, platform: str, message_data: Dict[str, Any]
    ) -> Optional[datetime]:
        """Extract message timestamp."""
        try:
            if platform == "twitter":
                created_at = message_data.get("created_at")
                if created_at:
                    from datetime import datetime

                    return datetime.strptime(created_at, "%a %b %d %H:%M:%S %z %Y")
            elif platform == "telegram":
                timestamp = message_data.get("date")
                if timestamp:
                    return datetime.fromtimestamp(timestamp)
            elif platform == "gmail":
                timestamp = message_data.get("internalDate")
                if timestamp:
                    return datetime.fromtimestamp(int(timestamp) / 1000)
            elif platform == "slack":
                ts = message_data.get("ts")
                if ts:
                    return datetime.fromtimestamp(float(ts))
            elif platform == "discord":
                timestamp = message_data.get("timestamp")
                if timestamp:
                    return datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            elif platform == "whatsapp":
                timestamp = message_data.get("timestamp")
                if timestamp:
                    return datetime.fromtimestamp(timestamp)
        except Exception as e:
            logger.warning(f"Failed to extract timestamp from {platform}: {e}")

        return None

    async def _check_message_exists(
        self, connection_id: UUID, platform_message_id: str
    ) -> bool:
        """Check if message already exists."""
        result = await self.db.execute(
            select(RawMessage.id)
            .where(
                RawMessage.connection_id == connection_id,
                RawMessage.platform_message_id == platform_message_id,
            )
            .limit(1)
        )
        return result.scalar_one_or_none() is not None

    async def _load_polling_state(self, connection: PlatformConnection) -> PollingState:
        """Load polling state from connection metadata."""
        metadata = connection.platform_metadata or {}
        polling_state_data = metadata.get("polling_state", {})

        if polling_state_data:
            return PollingState.from_dict(
                connection.id, connection.platform, polling_state_data
            )

        return PollingState(connection_id=connection.id, platform=connection.platform)

    async def _save_polling_state(
        self, connection_id: UUID, state: PollingState
    ) -> None:
        """Save polling state to connection metadata."""
        await self.db.execute(
            update(PlatformConnection)
            .where(PlatformConnection.id == connection_id)
            .values(
                platform_metadata=PlatformConnection.platform_metadata.op("||")(
                    {"polling_state": state.to_dict()}
                )
            )
        )
        await self.db.commit()
