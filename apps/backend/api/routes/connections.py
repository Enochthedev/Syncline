"""
Connection Management API

Endpoints for managing platform connections:
- Initiate OAuth flow
- Handle OAuth callbacks
- List active connections
- Disconnect platforms
- Check connection health
"""

import logging
from typing import List
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_database_session, validate_uuid
from db.models.platform_connection import (
    PlatformConnection,
    PlatformType,
    ConnectionStatus
)
from db.models.user import User
from integrations.base_connector import ConnectorHealth, ConnectorStatus
from integrations.gmail_connector import GmailConnector
from integrations.slack_connector import SlackConnector
from integrations.discord_connector import DiscordConnector
from integrations.whatsapp_connector import WhatsAppConnector
from integrations.twitter_connector import TwitterConnector
from integrations.telegram_connector import TelegramConnector
from services.event_bus import get_event_bus
from services.events.types import ConnectionEvent, EventType


logger = logging.getLogger(__name__)
router = APIRouter()


# =============================================================================
# Request/Response Models
# =============================================================================

class InitiateConnectionRequest(BaseModel):
    """Request to initiate platform connection."""
    user_id: UUID = Field(description="User ID initiating the connection")
    redirect_uri: str | None = Field(
        default=None,
        description="Optional redirect URI after OAuth"
    )


class InitiateConnectionResponse(BaseModel):
    """Response with OAuth URL."""
    connection_id: UUID = Field(description="Connection ID for tracking")
    authorization_url: str = Field(description="OAuth authorization URL")
    state: str = Field(description="OAuth state parameter for security")


class OAuthCallbackRequest(BaseModel):
    """OAuth callback parameters."""
    code: str = Field(description="Authorization code from OAuth provider")
    state: str = Field(description="State parameter for verification")


class ConnectionResponse(BaseModel):
    """Platform connection details."""
    id: UUID = Field(description="Connection ID")
    user_id: UUID = Field(description="User ID")
    platform: str = Field(description="Platform name")
    status: str = Field(description="Connection status")
    last_sync_at: str | None = Field(
        default=None,
        description="Last sync timestamp"
    )
    platform_metadata: dict = Field(
        default_factory=dict,
        description="Platform-specific metadata"
    )
    created_at: str = Field(description="Creation timestamp")
    updated_at: str = Field(description="Last update timestamp")


class ConnectionListResponse(BaseModel):
    """List of connections."""
    connections: List[ConnectionResponse] = Field(description="List of connections")
    total: int = Field(description="Total number of connections")


class ConnectionHealthResponse(BaseModel):
    """Connection health status."""
    connection_id: UUID = Field(description="Connection ID")
    platform: str = Field(description="Platform name")
    health_status: str = Field(description="Overall health status")
    connector_status: str = Field(description="Connector operational status")
    last_check_at: str = Field(description="Last health check timestamp")
    last_success_at: str | None = Field(
        default=None,
        description="Last successful operation"
    )
    last_error_at: str | None = Field(
        default=None,
        description="Last error timestamp"
    )
    last_error: str | None = Field(
        default=None,
        description="Last error message"
    )
    consecutive_failures: int = Field(description="Consecutive failure count")
    circuit_breaker_open: bool = Field(description="Circuit breaker status")
    metadata: dict = Field(
        default_factory=dict,
        description="Platform-specific health data"
    )


# =============================================================================
# Helper Functions
# =============================================================================

def _get_connector_class(platform: PlatformType):
    """Get connector class for platform."""
    connector_map = {
        PlatformType.GMAIL: GmailConnector,
        PlatformType.SLACK: SlackConnector,
        PlatformType.DISCORD: DiscordConnector,
        PlatformType.WHATSAPP: WhatsAppConnector,
        PlatformType.TWITTER: TwitterConnector,
        PlatformType.TELEGRAM: TelegramConnector,
    }
    return connector_map.get(platform)


async def _emit_connection_event(
    event_type: EventType,
    connection_id: UUID,
    platform: str,
    user_id: UUID,
    error: str | None = None
) -> None:
    """Emit connection lifecycle event."""
    try:
        event_bus = get_event_bus()
        event = ConnectionEvent(
            event_id=str(uuid4()),
            event_type=event_type,
            source="connection_api",
            payload={
                "connection_id": str(connection_id),
                "platform": platform,
                "user_id": str(user_id),
                "error": error,
            }
        )
        await event_bus.publish(event)
        logger.debug(f"Emitted {event_type.value} event for connection {connection_id}")
    except Exception as e:
        logger.error(f"Failed to emit connection event: {e}")


def _connection_to_response(conn: PlatformConnection) -> ConnectionResponse:
    """Convert database model to response model."""
    return ConnectionResponse(
        id=conn.id,
        user_id=conn.user_id,
        platform=conn.platform.value,
        status=conn.status.value,
        last_sync_at=conn.last_sync_at.isoformat() if conn.last_sync_at else None,
        platform_metadata=conn.platform_metadata or {},
        created_at=conn.created_at.isoformat(),
        updated_at=conn.updated_at.isoformat(),
    )


# =============================================================================
# API Endpoints
# =============================================================================

@router.post(
    "/initiate/{platform}",
    response_model=InitiateConnectionResponse,
    status_code=status.HTTP_200_OK,
    summary="Initiate platform connection",
    description="Start OAuth flow for connecting to a platform"
)
async def initiate_connection(
    platform: PlatformType,
    request: InitiateConnectionRequest,
    db: AsyncSession = Depends(get_database_session)
) -> InitiateConnectionResponse:
    """
    Initiate OAuth flow for platform connection.
    
    This endpoint starts the OAuth authentication process by:
    1. Creating a pending connection record
    2. Generating OAuth authorization URL
    3. Returning URL for user to complete authentication
    
    Args:
        platform: Platform to connect (gmail, slack, discord, etc.)
        request: Connection initiation request
        db: Database session
    
    Returns:
        Authorization URL and connection tracking ID
    
    Raises:
        HTTPException: If platform not supported or user not found
    """
    try:
        # Verify user exists
        user_result = await db.execute(
            select(User).where(User.id == request.user_id)
        )
        user = user_result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {request.user_id} not found"
            )
        
        # Get connector class
        connector_class = _get_connector_class(platform)
        if not connector_class:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Platform {platform.value} not supported"
            )
        
        # Create pending connection record
        connection = PlatformConnection(
            id=uuid4(),
            user_id=request.user_id,
            platform=platform,
            credentials={},  # Will be populated after OAuth
            status=ConnectionStatus.INACTIVE,
            platform_metadata={"oauth_state": str(uuid4())}
        )
        
        db.add(connection)
        await db.commit()
        await db.refresh(connection)
        
        # Generate OAuth URL (platform-specific implementation)
        # For now, return a placeholder - actual implementation depends on platform
        oauth_state = connection.platform_metadata.get("oauth_state", "")
        authorization_url = f"https://oauth.{platform.value}.com/authorize?state={oauth_state}"
        
        logger.info(
            f"Initiated {platform.value} connection for user {request.user_id}, "
            f"connection_id={connection.id}"
        )
        
        return InitiateConnectionResponse(
            connection_id=connection.id,
            authorization_url=authorization_url,
            state=oauth_state
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to initiate connection: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate connection: {str(e)}"
        )


@router.get(
    "/callback/{platform}",
    response_model=ConnectionResponse,
    status_code=status.HTTP_200_OK,
    summary="OAuth callback handler",
    description="Handle OAuth callback and complete connection"
)
async def oauth_callback(
    platform: PlatformType,
    code: str = Query(..., description="Authorization code"),
    state: str = Query(..., description="OAuth state parameter"),
    db: AsyncSession = Depends(get_database_session)
) -> ConnectionResponse:
    """
    Handle OAuth callback and complete platform connection.
    
    This endpoint:
    1. Validates OAuth state parameter
    2. Exchanges authorization code for access token
    3. Updates connection with credentials
    4. Emits CONNECTION_ESTABLISHED event
    
    Args:
        platform: Platform being connected
        code: Authorization code from OAuth provider
        state: State parameter for verification
        db: Database session
    
    Returns:
        Updated connection details
    
    Raises:
        HTTPException: If state invalid or OAuth exchange fails
    """
    try:
        # Find connection by state
        result = await db.execute(
            select(PlatformConnection).where(
                PlatformConnection.platform == platform,
                PlatformConnection.platform_metadata["oauth_state"].astext == state
            )
        )
        connection = result.scalar_one_or_none()
        
        if not connection:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid OAuth state or connection not found"
            )
        
        # Exchange code for tokens (platform-specific implementation)
        # For now, store placeholder credentials
        connection.credentials = {
            "access_token": f"token_{code[:10]}",
            "refresh_token": f"refresh_{code[:10]}",
            "expires_at": "2024-12-31T23:59:59Z"
        }
        connection.status = ConnectionStatus.ACTIVE
        connection.platform_metadata = {
            **connection.platform_metadata,
            "oauth_completed_at": "2024-11-10T00:00:00Z"
        }
        
        await db.commit()
        await db.refresh(connection)
        
        # Emit CONNECTION_ESTABLISHED event
        await _emit_connection_event(
            EventType.CONNECTION_ESTABLISHED,
            connection.id,
            platform.value,
            connection.user_id
        )
        
        logger.info(
            f"Completed {platform.value} connection for user {connection.user_id}, "
            f"connection_id={connection.id}"
        )
        
        return _connection_to_response(connection)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OAuth callback failed: {e}")
        
        # Emit CONNECTION_FAILED event if connection exists
        if connection:
            await _emit_connection_event(
                EventType.CONNECTION_FAILED,
                connection.id,
                platform.value,
                connection.user_id,
                error=str(e)
            )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OAuth callback failed: {str(e)}"
        )


@router.get(
    "",
    response_model=ConnectionListResponse,
    status_code=status.HTTP_200_OK,
    summary="List connections",
    description="List all platform connections for a user"
)
async def list_connections(
    user_id: UUID = Query(..., description="User ID to filter connections"),
    platform: PlatformType | None = Query(
        default=None,
        description="Optional platform filter"
    ),
    status_filter: ConnectionStatus | None = Query(
        default=None,
        alias="status",
        description="Optional status filter"
    ),
    db: AsyncSession = Depends(get_database_session)
) -> ConnectionListResponse:
    """
    List platform connections.
    
    Returns all connections for a user, optionally filtered by platform and status.
    
    Args:
        user_id: User ID to filter connections
        platform: Optional platform filter
        status_filter: Optional status filter
        db: Database session
    
    Returns:
        List of connections
    """
    try:
        # Build query
        query = select(PlatformConnection).where(
            PlatformConnection.user_id == user_id
        )
        
        if platform:
            query = query.where(PlatformConnection.platform == platform)
        
        if status_filter:
            query = query.where(PlatformConnection.status == status_filter)
        
        # Execute query
        result = await db.execute(query)
        connections = result.scalars().all()
        
        return ConnectionListResponse(
            connections=[_connection_to_response(conn) for conn in connections],
            total=len(connections)
        )
    
    except Exception as e:
        logger.error(f"Failed to list connections: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list connections: {str(e)}"
        )


@router.delete(
    "/{connection_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Disconnect platform",
    description="Disconnect and remove a platform connection"
)
async def disconnect_platform(
    connection_id: str = Depends(validate_uuid),
    db: AsyncSession = Depends(get_database_session)
) -> None:
    """
    Disconnect from a platform.
    
    This endpoint:
    1. Disconnects the connector
    2. Revokes credentials
    3. Updates connection status
    4. Emits CONNECTION_REVOKED event
    
    Args:
        connection_id: Connection ID to disconnect
        db: Database session
    
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
                detail=f"Connection {connection_id} not found"
            )
        
        # Get connector and disconnect
        connector_class = _get_connector_class(connection.platform)
        if connector_class and connection.credentials:
            try:
                connector = connector_class(
                    connection_id=connection.id,
                    credentials=connection.credentials
                )
                await connector.disconnect()
            except Exception as e:
                logger.warning(f"Failed to disconnect connector: {e}")
        
        # Update connection status
        connection.status = ConnectionStatus.REVOKED
        await db.commit()
        
        # Emit CONNECTION_REVOKED event
        await _emit_connection_event(
            EventType.CONNECTION_REVOKED,
            connection.id,
            connection.platform.value,
            connection.user_id
        )
        
        logger.info(
            f"Disconnected {connection.platform.value} connection {connection_id}"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to disconnect: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to disconnect: {str(e)}"
        )


@router.get(
    "/{connection_id}/health",
    response_model=ConnectionHealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Check connection health",
    description="Perform health check on a platform connection"
)
async def check_connection_health(
    connection_id: str = Depends(validate_uuid),
    db: AsyncSession = Depends(get_database_session)
) -> ConnectionHealthResponse:
    """
    Check health of a platform connection.
    
    Performs a health check on the connector and returns detailed status.
    
    Args:
        connection_id: Connection ID to check
        db: Database session
    
    Returns:
        Health status details
    
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
                detail=f"Connection {connection_id} not found"
            )
        
        # Get connector class
        connector_class = _get_connector_class(connection.platform)
        if not connector_class:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Platform {connection.platform.value} not supported"
            )
        
        # Create connector and perform health check
        connector = connector_class(
            connection_id=connection.id,
            credentials=connection.credentials
        )
        
        # Connect if not already connected
        if not connector.is_connected:
            await connector.connect()
        
        # Perform health check
        health = await connector.health_check()
        
        return ConnectionHealthResponse(
            connection_id=connection.id,
            platform=connection.platform.value,
            health_status=health.status.value,
            connector_status=health.connector_status.value,
            last_check_at=health.last_check_at.isoformat(),
            last_success_at=(
                health.last_success_at.isoformat()
                if health.last_success_at else None
            ),
            last_error_at=(
                health.last_error_at.isoformat()
                if health.last_error_at else None
            ),
            last_error=health.last_error,
            consecutive_failures=health.consecutive_failures,
            circuit_breaker_open=health.circuit_breaker_open,
            metadata=health.metadata
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Health check failed: {str(e)}"
        )
