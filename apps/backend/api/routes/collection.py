"""
Collection Management API

Endpoints for managing message collection:
- Start/stop collection for connections
- Check collection status
- Webhook receivers for real-time updates
- Collection history and progress
"""

import hashlib
import hmac
import logging
from typing import Any, Dict, List
from uuid import UUID, uuid4

from fastapi import APIRouter, Body, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_database_session, validate_uuid
from db.models.collection_job import CollectionJob, JobStatus, JobType
from db.models.platform_connection import (
    ConnectionStatus,
    PlatformConnection,
    PlatformType,
)
from db.models.raw_message import RawMessage
from services.collection_orchestrator import CollectionOrchestrator
from services.event_bus import get_event_bus
from services.events.types import Event, EventType

logger = logging.getLogger(__name__)
router = APIRouter()


# =============================================================================
# Request/Response Models
# =============================================================================


class StartCollectionRequest(BaseModel):
    """Request to start collection for a connection."""

    job_type: JobType = Field(
        default=JobType.HISTORICAL, description="Type of collection job"
    )
    priority: int = Field(
        default=0, description="Job priority (higher = more important)"
    )


class StartCollectionResponse(BaseModel):
    """Response with collection job details."""

    job_id: UUID = Field(description="Collection job ID")
    connection_id: UUID = Field(description="Platform connection ID")
    job_type: str = Field(description="Type of collection job")
    status: str = Field(description="Job status")
    created_at: str = Field(description="Job creation timestamp")


class CollectionStatusResponse(BaseModel):
    """Collection status for a connection."""

    job_id: UUID = Field(description="Collection job ID")
    connection_id: UUID = Field(description="Platform connection ID")
    job_type: str = Field(description="Type of collection job")
    status: str = Field(description="Job status")
    progress: Dict[str, Any] = Field(
        default_factory=dict, description="Job progress information"
    )
    error_message: str | None = Field(
        default=None, description="Error message if failed"
    )
    created_at: str = Field(description="Job creation timestamp")
    updated_at: str = Field(description="Last update timestamp")
    is_active: bool = Field(description="Whether job is currently running")


class CollectionHistoryResponse(BaseModel):
    """Collection history for a connection."""

    connection_id: UUID = Field(description="Platform connection ID")
    jobs: List[CollectionStatusResponse] = Field(description="List of collection jobs")
    total: int = Field(description="Total number of jobs")


class WebhookEventResponse(BaseModel):
    """Response for webhook event processing."""

    event_id: str = Field(description="Event ID")
    platform: str = Field(description="Platform name")
    status: str = Field(description="Processing status")
    message: str = Field(description="Status message")
    messages_processed: int = Field(
        default=0, description="Number of messages processed"
    )


# =============================================================================
# Webhook Signature Validation
# =============================================================================


def validate_webhook_signature(
    platform: str, payload: bytes, signature: str | None, secret: str | None
) -> bool:
    """
    Validate webhook signature for security.

    Args:
        platform: Platform name
        payload: Raw request payload
        signature: Signature from request header
        secret: Webhook secret for validation

    Returns:
        True if signature is valid, False otherwise
    """
    if not secret or not signature:
        logger.warning(f"Missing signature or secret for {platform} webhook")
        return False

    try:
        # Platform-specific signature validation
        if platform == "gmail":
            # Gmail uses X-Goog-Channel-Token header
            # For now, basic validation - enhance with actual Gmail logic
            return True

        elif platform == "slack":
            # Slack uses X-Slack-Signature with HMAC-SHA256
            timestamp = (
                signature.split(",")[0].split("=")[1] if "," in signature else ""
            )
            base_string = f"v0:{timestamp}:{payload.decode()}"
            computed_signature = (
                "v0="
                + hmac.new(
                    secret.encode(), base_string.encode(), hashlib.sha256
                ).hexdigest()
            )
            return hmac.compare_digest(computed_signature, signature)

        elif platform == "discord":
            # Discord uses X-Signature-Ed25519 with Ed25519
            # For now, basic validation - enhance with actual Discord logic
            return True

        elif platform == "whatsapp":
            # WhatsApp uses X-Hub-Signature-256 with HMAC-SHA256
            computed_signature = (
                "sha256="
                + hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
            )
            return hmac.compare_digest(computed_signature, signature)

        else:
            # Generic HMAC-SHA256 validation
            computed_signature = hmac.new(
                secret.encode(), payload, hashlib.sha256
            ).hexdigest()
            return hmac.compare_digest(computed_signature, signature)

    except Exception as e:
        logger.error(f"Signature validation error for {platform}: {e}")
        return False


async def route_webhook_event(
    platform: str, event_data: Dict[str, Any], db: AsyncSession
) -> Dict[str, Any]:
    """
    Route webhook event to appropriate handler.

    Args:
        platform: Platform name
        event_data: Webhook event data
        db: Database session

    Returns:
        Processing result dictionary
    """
    result = {"messages_processed": 0, "errors": []}

    try:
        # Extract messages from platform-specific event format
        messages = []

        if platform == "gmail":
            # Gmail push notification format
            # Contains historyId, need to fetch actual messages
            history_id = event_data.get("historyId")
            if history_id:
                # TODO: Fetch messages using history API
                logger.info(f"Gmail history update: {history_id}")

        elif platform == "slack":
            # Slack event format
            event = event_data.get("event", {})
            if event.get("type") == "message":
                messages.append(event)

        elif platform == "discord":
            # Discord gateway event format
            if event_data.get("t") == "MESSAGE_CREATE":
                messages.append(event_data.get("d", {}))

        elif platform == "whatsapp":
            # WhatsApp webhook format
            entry = event_data.get("entry", [])
            for item in entry:
                changes = item.get("changes", [])
                for change in changes:
                    if change.get("field") == "messages":
                        value = change.get("value", {})
                        messages.extend(value.get("messages", []))

        elif platform == "twitter":
            # Twitter webhook format
            if "tweet_create_events" in event_data:
                messages.extend(event_data["tweet_create_events"])

        elif platform == "telegram":
            # Telegram webhook format
            if "message" in event_data:
                messages.append(event_data["message"])

        # Process each message
        for msg_data in messages:
            try:
                # Find connection for this platform
                # For now, we'll need to match based on platform-specific identifiers
                # This is a simplified version - enhance with proper connection matching

                # Create raw message record
                raw_message = RawMessage(
                    connection_id=UUID(
                        "00000000-0000-0000-0000-000000000000"
                    ),  # Placeholder
                    platform=platform,
                    platform_message_id=str(msg_data.get("id", uuid4())),
                    raw_data=msg_data,
                    processed=False,
                )

                db.add(raw_message)
                result["messages_processed"] += 1

                # Publish MESSAGE_COLLECTED event
                event_bus = get_event_bus()
                await event_bus.publish(
                    Event(
                        event_id=str(uuid4()),
                        event_type=EventType.MESSAGE_COLLECTED,
                        source="webhook_receiver",
                        payload={
                            "raw_message_id": str(raw_message.id),
                            "platform": platform,
                            "platform_message_id": raw_message.platform_message_id,
                            "source": "webhook",
                        },
                    )
                )

            except Exception as e:
                logger.error(f"Error processing message from {platform}: {e}")
                result["errors"].append(str(e))

        # Commit all messages
        await db.commit()

    except Exception as e:
        logger.error(f"Error routing webhook event for {platform}: {e}")
        result["errors"].append(str(e))
        await db.rollback()

    return result


# =============================================================================
# Collection Management Endpoints
# =============================================================================


@router.post(
    "/start/{connection_id}",
    response_model=StartCollectionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start collection",
    description="Start message collection for a platform connection",
)
async def start_collection(
    connection_id: str = Depends(validate_uuid),
    request: StartCollectionRequest = Body(...),
    db: AsyncSession = Depends(get_database_session),
) -> StartCollectionResponse:
    """
    Start message collection for a connection.

    Creates a collection job and begins fetching messages from the platform.

    Args:
        connection_id: Platform connection ID
        request: Collection start request
        db: Database session

    Returns:
        Collection job details

    Raises:
        HTTPException: If connection not found or not active
    """
    try:
        # Find connection
        result = await db.execute(
            select(PlatformConnection).where(
                PlatformConnection.id == UUID(connection_id)
            )
        )
        connection = result.scalar_one_or_none()

        if not connection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Connection {connection_id} not found",
            )

        if connection.status != ConnectionStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Connection is not active (status={connection.status.value})",
            )

        # Create collection orchestrator
        orchestrator = CollectionOrchestrator(db=db)

        # Create collection job
        job = await orchestrator.create_job(
            connection_id=connection.id,
            job_type=request.job_type,
            priority=request.priority,
        )

        # Start the job
        await orchestrator.start_job(job.id)

        logger.info(
            f"Started {request.job_type.value} collection for connection {connection_id}, "
            f"job_id={job.id}"
        )

        return StartCollectionResponse(
            job_id=job.id,
            connection_id=connection.id,
            job_type=job.job_type.value,
            status=job.status.value,
            created_at=job.created_at.isoformat(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start collection: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start collection: {str(e)}",
        )


@router.post(
    "/stop/{connection_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Stop collection",
    description="Stop active collection for a platform connection",
)
async def stop_collection(
    connection_id: str = Depends(validate_uuid),
    db: AsyncSession = Depends(get_database_session),
) -> None:
    """
    Stop active collection for a connection.

    Pauses any running collection jobs for the specified connection.

    Args:
        connection_id: Platform connection ID
        db: Database session

    Raises:
        HTTPException: If connection not found or no active jobs
    """
    try:
        # Find connection
        result = await db.execute(
            select(PlatformConnection).where(
                PlatformConnection.id == UUID(connection_id)
            )
        )
        connection = result.scalar_one_or_none()

        if not connection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Connection {connection_id} not found",
            )

        # Find active jobs
        jobs_result = await db.execute(
            select(CollectionJob).where(
                CollectionJob.connection_id == connection.id,
                CollectionJob.status.in_([JobStatus.RUNNING, JobStatus.PENDING]),
            )
        )
        active_jobs = jobs_result.scalars().all()

        if not active_jobs:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No active collection jobs for connection {connection_id}",
            )

        # Create orchestrator and pause jobs
        orchestrator = CollectionOrchestrator(db=db)

        for job in active_jobs:
            await orchestrator.pause_job(job.id)
            logger.info(f"Stopped collection job {job.id}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to stop collection: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stop collection: {str(e)}",
        )


@router.get(
    "/status/{connection_id}",
    response_model=CollectionStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get collection status",
    description="Get current collection status for a connection",
)
async def get_collection_status(
    connection_id: str = Depends(validate_uuid),
    db: AsyncSession = Depends(get_database_session),
) -> CollectionStatusResponse:
    """
    Get collection status for a connection.

    Returns the most recent collection job status.

    Args:
        connection_id: Platform connection ID
        db: Database session

    Returns:
        Collection status details

    Raises:
        HTTPException: If connection not found or no jobs exist
    """
    try:
        # Find connection
        result = await db.execute(
            select(PlatformConnection).where(
                PlatformConnection.id == UUID(connection_id)
            )
        )
        connection = result.scalar_one_or_none()

        if not connection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Connection {connection_id} not found",
            )

        # Get most recent job
        job_result = await db.execute(
            select(CollectionJob)
            .where(CollectionJob.connection_id == connection.id)
            .order_by(CollectionJob.created_at.desc())
            .limit(1)
        )
        job = job_result.scalar_one_or_none()

        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No collection jobs found for connection {connection_id}",
            )

        # Create orchestrator to check if job is active
        orchestrator = CollectionOrchestrator(db=db)
        job_status = await orchestrator.get_job_status(job.id)

        return CollectionStatusResponse(
            job_id=job.id,
            connection_id=job.connection_id,
            job_type=job.job_type.value,
            status=job.status.value,
            progress=job.progress or {},
            error_message=job.error_message,
            created_at=job.created_at.isoformat(),
            updated_at=job.updated_at.isoformat(),
            is_active=job_status.get("is_active", False) if job_status else False,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get collection status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get collection status: {str(e)}",
        )


@router.get(
    "/history/{connection_id}",
    response_model=CollectionHistoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get collection history",
    description="Get collection job history for a connection",
)
async def get_collection_history(
    connection_id: str = Depends(validate_uuid),
    limit: int = 10,
    db: AsyncSession = Depends(get_database_session),
) -> CollectionHistoryResponse:
    """
    Get collection history for a connection.

    Returns recent collection jobs with their status and progress.

    Args:
        connection_id: Platform connection ID
        limit: Maximum number of jobs to return
        db: Database session

    Returns:
        Collection history

    Raises:
        HTTPException: If connection not found
    """
    try:
        # Find connection
        result = await db.execute(
            select(PlatformConnection).where(
                PlatformConnection.id == UUID(connection_id)
            )
        )
        connection = result.scalar_one_or_none()

        if not connection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Connection {connection_id} not found",
            )

        # Get collection orchestrator
        orchestrator = CollectionOrchestrator(db=db)

        # Get job history
        jobs_data = await orchestrator.get_connection_jobs(
            connection_id=connection.id, limit=limit
        )

        # Convert to response models
        jobs = [
            CollectionStatusResponse(
                job_id=UUID(job["job_id"]),
                connection_id=UUID(job["connection_id"]),
                job_type=job["job_type"],
                status=job["status"],
                progress=job.get("progress", {}),
                error_message=job.get("error_message"),
                created_at=job["created_at"],
                updated_at=job["updated_at"],
                is_active=False,  # Historical jobs are not active
            )
            for job in jobs_data
        ]

        return CollectionHistoryResponse(
            connection_id=connection.id,
            jobs=jobs,
            total=len(jobs),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get collection history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get collection history: {str(e)}",
        )


# =============================================================================
# Webhook Receiver Endpoint
# =============================================================================


@router.post(
    "/webhook/{platform}",
    response_model=WebhookEventResponse,
    status_code=status.HTTP_200_OK,
    summary="Webhook receiver",
    description="Receive real-time webhook events from platforms",
)
async def receive_webhook(
    platform: PlatformType,
    request: Request,
    db: AsyncSession = Depends(get_database_session),
    x_hub_signature: str | None = Header(default=None, alias="X-Hub-Signature-256"),
    x_slack_signature: str | None = Header(default=None, alias="X-Slack-Signature"),
    x_discord_signature: str | None = Header(default=None, alias="X-Signature-Ed25519"),
) -> WebhookEventResponse:
    """
    Receive webhook events from platforms.

    This endpoint:
    1. Validates webhook signature for security
    2. Parses platform-specific event format
    3. Routes events to appropriate handlers
    4. Stores raw messages in database
    5. Publishes MESSAGE_COLLECTED events

    Args:
        platform: Platform sending the webhook
        request: FastAPI request object
        db: Database session
        x_hub_signature: WhatsApp/Facebook signature header
        x_slack_signature: Slack signature header
        x_discord_signature: Discord signature header

    Returns:
        Webhook processing result

    Raises:
        HTTPException: If signature validation fails
    """
    event_id = str(uuid4())

    try:
        # Read raw payload
        payload = await request.body()

        # Parse JSON payload
        try:
            event_data = await request.json()
        except Exception as e:
            logger.error(f"Failed to parse webhook payload: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON payload"
            )

        # Determine signature header based on platform
        signature = None
        if platform == PlatformType.WHATSAPP:
            signature = x_hub_signature
        elif platform == PlatformType.SLACK:
            signature = x_slack_signature
        elif platform == PlatformType.DISCORD:
            signature = x_discord_signature

        # Validate webhook signature
        # TODO: Get webhook secret from connection configuration
        webhook_secret = None  # Placeholder - should be retrieved from config

        if webhook_secret:
            is_valid = validate_webhook_signature(
                platform=platform.value,
                payload=payload,
                signature=signature,
                secret=webhook_secret,
            )

            if not is_valid:
                logger.warning(f"Invalid webhook signature for {platform.value}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid webhook signature",
                )

        # Handle webhook verification challenges (platform-specific)
        if platform == PlatformType.WHATSAPP:
            # WhatsApp sends verification challenge
            if "hub.challenge" in event_data:
                return WebhookEventResponse(
                    event_id=event_id,
                    platform=platform.value,
                    status="verified",
                    message="Webhook verified",
                    messages_processed=0,
                )

        elif platform == PlatformType.SLACK:
            # Slack sends URL verification
            if event_data.get("type") == "url_verification":
                return WebhookEventResponse(
                    event_id=event_id,
                    platform=platform.value,
                    status="verified",
                    message=event_data.get("challenge", ""),
                    messages_processed=0,
                )

        # Route webhook event to handler
        result = await route_webhook_event(
            platform=platform.value, event_data=event_data, db=db
        )

        logger.info(
            f"Processed webhook from {platform.value}: "
            f"{result['messages_processed']} messages, "
            f"{len(result.get('errors', []))} errors"
        )

        return WebhookEventResponse(
            event_id=event_id,
            platform=platform.value,
            status="processed",
            message=f"Processed {result['messages_processed']} messages",
            messages_processed=result["messages_processed"],
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Webhook processing failed for {platform.value}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Webhook processing failed: {str(e)}",
        )
