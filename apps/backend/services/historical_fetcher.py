"""
Historical Message Fetcher Service

Manages historical message fetching from platform connections with:
- Pagination support for each platform
- Checkpoint/resume functionality
- Progress tracking and monitoring
- Rate limiting and error handling
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.collection_job import CollectionJob, JobStatus
from db.models.platform_connection import PlatformConnection
from db.models.raw_message import RawMessage
from integrations.base_connector import BaseConnector, RateLimitError
from services.event_bus import EventBus, get_event_bus
from services.events.types import Event, EventType

logger = logging.getLogger(__name__)


# =============================================================================
# Checkpoint Management
# =============================================================================


class FetchCheckpoint:
    """
    Checkpoint for resumable historical fetching.

    Stores pagination state to allow resuming interrupted fetches.
    """

    def __init__(
        self,
        page_token: Optional[str] = None,
        last_message_id: Optional[str] = None,
        messages_fetched: int = 0,
        last_updated: Optional[datetime] = None,
        platform_specific: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize fetch checkpoint.

        Args:
            page_token: Platform-specific pagination token
            last_message_id: Last message ID fetched
            messages_fetched: Total messages fetched so far
            last_updated: Last checkpoint update time
            platform_specific: Platform-specific checkpoint data
        """
        self.page_token = page_token
        self.last_message_id = last_message_id
        self.messages_fetched = messages_fetched
        self.last_updated = last_updated or datetime.utcnow()
        self.platform_specific = platform_specific or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert checkpoint to dictionary for storage."""
        return {
            "page_token": self.page_token,
            "last_message_id": self.last_message_id,
            "messages_fetched": self.messages_fetched,
            "last_updated": self.last_updated.isoformat(),
            "platform_specific": self.platform_specific,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FetchCheckpoint":
        """Create checkpoint from dictionary."""
        return cls(
            page_token=data.get("page_token"),
            last_message_id=data.get("last_message_id"),
            messages_fetched=data.get("messages_fetched", 0),
            last_updated=(
                datetime.fromisoformat(data["last_updated"])
                if data.get("last_updated")
                else None
            ),
            platform_specific=data.get("platform_specific", {}),
        )


# =============================================================================
# Historical Fetcher
# =============================================================================


class HistoricalFetcher:
    """
    Service for fetching historical messages from platforms.

    Features:
    - Platform-agnostic pagination support
    - Checkpoint/resume functionality
    - Progress tracking and monitoring
    - Rate limiting and backoff
    - Duplicate detection
    - Event publishing for collected messages
    """

    def __init__(
        self,
        db: AsyncSession,
        event_bus: Optional[EventBus] = None,
        batch_size: int = 100,
        max_retries: int = 3,
        retry_delay: int = 5,
    ):
        """
        Initialize historical fetcher.

        Args:
            db: Database session
            event_bus: Event bus for publishing events
            batch_size: Number of messages to fetch per request
            max_retries: Maximum retry attempts on failure
            retry_delay: Delay between retries in seconds
        """
        self.db = db
        self.event_bus = event_bus or get_event_bus()
        self.batch_size = batch_size
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    async def fetch_historical_messages(
        self,
        job: CollectionJob,
        connection: PlatformConnection,
        connector: BaseConnector,
        fetch_function: Callable,
        max_messages: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Fetch historical messages from a platform.

        Args:
            job: Collection job for tracking progress
            connection: Platform connection
            connector: Platform connector instance
            fetch_function: Platform-specific fetch function
            max_messages: Maximum messages to fetch (None = all)

        Returns:
            Summary dictionary with fetch statistics
        """
        logger.info(
            f"Starting historical fetch for {connection.platform} "
            f"(job={job.id}, connection={connection.id})"
        )

        # Load or create checkpoint
        checkpoint = self._load_checkpoint(job)

        # Initialize statistics
        stats = {
            "total_fetched": checkpoint.messages_fetched,
            "new_messages": 0,
            "duplicate_messages": 0,
            "failed_messages": 0,
            "pages_processed": 0,
            "started_at": datetime.utcnow().isoformat(),
        }

        try:
            # Fetch messages in batches
            while True:
                # Check if we've reached the limit
                if max_messages and stats["total_fetched"] >= max_messages:
                    logger.info(
                        f"Reached max messages limit ({max_messages}) "
                        f"for job {job.id}"
                    )
                    break

                # Calculate batch size for this iteration
                remaining = None
                if max_messages:
                    remaining = max_messages - stats["total_fetched"]
                    batch_size = min(self.batch_size, remaining)
                else:
                    batch_size = self.batch_size

                # Fetch batch of messages
                batch_result = await self._fetch_batch(
                    connection=connection,
                    connector=connector,
                    fetch_function=fetch_function,
                    checkpoint=checkpoint,
                    batch_size=batch_size,
                )

                if not batch_result:
                    logger.info(f"No more messages to fetch for job {job.id}")
                    break

                # Process and store messages
                batch_stats = await self._process_batch(
                    connection=connection,
                    messages=batch_result["messages"],
                    job=job,
                )

                # Update statistics
                stats["new_messages"] += batch_stats["new"]
                stats["duplicate_messages"] += batch_stats["duplicates"]
                stats["failed_messages"] += batch_stats["failed"]
                stats["total_fetched"] += batch_stats["new"]
                stats["pages_processed"] += 1

                # Update checkpoint
                checkpoint.page_token = batch_result.get("next_page_token")
                checkpoint.messages_fetched = stats["total_fetched"]
                checkpoint.last_updated = datetime.utcnow()

                if batch_result.get("messages"):
                    last_msg = batch_result["messages"][-1]
                    checkpoint.last_message_id = last_msg.get("id")

                # Save checkpoint
                await self._save_checkpoint(job, checkpoint)

                # Update job progress
                await self._update_job_progress(job, stats, checkpoint)

                # Check if there are more pages
                if not batch_result.get("next_page_token"):
                    logger.info(f"Reached end of messages for job {job.id}")
                    break

                # Small delay to respect rate limits
                await asyncio.sleep(0.1)

            # Mark as completed
            stats["completed_at"] = datetime.utcnow().isoformat()
            stats["status"] = "completed"

            logger.info(
                f"Historical fetch completed for job {job.id}: "
                f"{stats['new_messages']} new, "
                f"{stats['duplicate_messages']} duplicates, "
                f"{stats['failed_messages']} failed"
            )

            return stats

        except Exception as e:
            logger.error(
                f"Historical fetch failed for job {job.id}: {e}", exc_info=True
            )
            stats["error"] = str(e)
            stats["status"] = "failed"
            raise

    async def _fetch_batch(
        self,
        connection: PlatformConnection,
        connector: BaseConnector,
        fetch_function: Callable,
        checkpoint: FetchCheckpoint,
        batch_size: int,
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch a batch of messages with retry logic.

        Args:
            connection: Platform connection
            connector: Platform connector
            fetch_function: Platform-specific fetch function
            checkpoint: Current checkpoint
            batch_size: Number of messages to fetch

        Returns:
            Batch result with messages and pagination token, or None
        """
        retry_count = 0
        last_error = None

        while retry_count < self.max_retries:
            try:
                # Call platform-specific fetch function
                result = await fetch_function(
                    connector=connector,
                    page_token=checkpoint.page_token,
                    batch_size=batch_size,
                    checkpoint=checkpoint,
                )

                return result

            except RateLimitError as e:
                logger.warning(
                    f"Rate limit hit for {connection.platform}, "
                    f"waiting {e.retry_after or self.retry_delay}s"
                )
                await asyncio.sleep(e.retry_after or self.retry_delay)
                retry_count += 1
                last_error = e

            except Exception as e:
                logger.error(f"Error fetching batch (attempt {retry_count + 1}): {e}")
                retry_count += 1
                last_error = e

                if retry_count < self.max_retries:
                    # Exponential backoff
                    delay = self.retry_delay * (2**retry_count)
                    await asyncio.sleep(delay)

        # All retries exhausted
        logger.error(
            f"Failed to fetch batch after {self.max_retries} attempts: " f"{last_error}"
        )
        raise last_error

    async def _process_batch(
        self,
        connection: PlatformConnection,
        messages: List[Dict[str, Any]],
        job: CollectionJob,
    ) -> Dict[str, int]:
        """
        Process and store a batch of messages.

        Args:
            connection: Platform connection
            messages: List of raw message data
            job: Collection job

        Returns:
            Statistics dictionary with counts
        """
        stats = {"new": 0, "duplicates": 0, "failed": 0}

        for msg_data in messages:
            try:
                # Extract platform message ID
                platform_msg_id = self._extract_message_id(
                    connection.platform, msg_data
                )

                if not platform_msg_id:
                    logger.warning(f"Could not extract message ID from {msg_data}")
                    stats["failed"] += 1
                    continue

                # Check if message already exists
                existing = await self._check_message_exists(
                    connection.id, platform_msg_id
                )

                if existing:
                    stats["duplicates"] += 1
                    continue

                # Create raw message record
                raw_message = RawMessage(
                    connection_id=connection.id,
                    platform=connection.platform,
                    platform_message_id=platform_msg_id,
                    raw_data=msg_data,
                    processed=False,
                )

                self.db.add(raw_message)
                stats["new"] += 1

                # Publish event for new message
                await self.event_bus.publish(
                    Event(
                        event_type=EventType.MESSAGE_COLLECTED,
                        source="historical_fetcher",
                        payload={
                            "raw_message_id": str(raw_message.id),
                            "connection_id": str(connection.id),
                            "platform": connection.platform,
                            "platform_message_id": platform_msg_id,
                            "job_id": str(job.id),
                        },
                    )
                )

            except Exception as e:
                logger.error(f"Error processing message: {e}", exc_info=True)
                stats["failed"] += 1

        # Commit batch
        try:
            await self.db.commit()
        except Exception as e:
            logger.error(f"Error committing batch: {e}")
            await self.db.rollback()
            raise

        return stats

    def _extract_message_id(
        self, platform: str, message_data: Dict[str, Any]
    ) -> Optional[str]:
        """
        Extract platform-specific message ID.

        Args:
            platform: Platform name
            message_data: Raw message data

        Returns:
            Message ID or None
        """
        # Platform-specific ID extraction
        if platform == "gmail":
            return message_data.get("id")
        elif platform == "slack":
            return message_data.get("ts") or message_data.get("client_msg_id")
        elif platform == "discord":
            return message_data.get("id")
        elif platform == "whatsapp":
            return message_data.get("id") or message_data.get("event_id")
        elif platform == "twitter":
            return message_data.get("id_str") or str(message_data.get("id"))
        elif platform == "telegram":
            return str(message_data.get("message_id"))
        else:
            # Generic fallback
            return message_data.get("id")

    async def _check_message_exists(
        self, connection_id: UUID, platform_message_id: str
    ) -> bool:
        """
        Check if message already exists in database.

        Args:
            connection_id: Platform connection ID
            platform_message_id: Platform message ID

        Returns:
            True if message exists, False otherwise
        """
        result = await self.db.execute(
            select(RawMessage.id)
            .where(
                RawMessage.connection_id == connection_id,
                RawMessage.platform_message_id == platform_message_id,
            )
            .limit(1)
        )
        return result.scalar_one_or_none() is not None

    def _load_checkpoint(self, job: CollectionJob) -> FetchCheckpoint:
        """
        Load checkpoint from job progress.

        Args:
            job: Collection job

        Returns:
            FetchCheckpoint instance
        """
        if job.progress and "checkpoint" in job.progress:
            return FetchCheckpoint.from_dict(job.progress["checkpoint"])
        return FetchCheckpoint()

    async def _save_checkpoint(
        self, job: CollectionJob, checkpoint: FetchCheckpoint
    ) -> None:
        """
        Save checkpoint to job progress.

        Args:
            job: Collection job
            checkpoint: Checkpoint to save
        """
        if not job.progress:
            job.progress = {}

        job.progress["checkpoint"] = checkpoint.to_dict()

        # Commit checkpoint
        await self.db.commit()

    async def _update_job_progress(
        self, job: CollectionJob, stats: Dict[str, Any], checkpoint: FetchCheckpoint
    ) -> None:
        """
        Update job progress with current statistics.

        Args:
            job: Collection job
            stats: Current statistics
            checkpoint: Current checkpoint
        """
        if not job.progress:
            job.progress = {}

        job.progress.update(
            {
                "total_fetched": stats["total_fetched"],
                "new_messages": stats["new_messages"],
                "duplicate_messages": stats["duplicate_messages"],
                "failed_messages": stats["failed_messages"],
                "pages_processed": stats["pages_processed"],
                "last_updated": datetime.utcnow().isoformat(),
                "checkpoint": checkpoint.to_dict(),
            }
        )

        await self.db.commit()
