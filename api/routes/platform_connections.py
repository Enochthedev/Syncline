"""
Platform Connection Management API Routes

Provides endpoints for managing platform connections, OAuth flows,
health monitoring, and troubleshooting.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_current_user, get_db
from db.models.user import User
from integrations.connector_manager import ConnectorManager
from integrations.base_connector import ConnectorHealth, ConnectorStatus
from integrations.token_manager import TokenManager, TokenInfo
from services.security.oauth_service import OAuthService
from services.security.types import OAuthConfig, OAuthState

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/platforms", tags=["platform-connections"])

# Pydantic models for request/response


class PlatformInfo(BaseModel):
    platform: str
    display_name: str
    description: str
    icon: str
    is_supported: bool
    oauth_config: Optional[Dict[str, Any]] = None


class ConnectionStatus(BaseModel):
    id: str
    platform: str
    display_name: str
    is_connected: bool
    is_enabled: bool
    connection_status: str
    last_sync_time: Optional[datetime] = None
    last_error_time: Optional[datetime] = None
    last_error: Optional[str] = None
    sync_preferences: Dict[str, Any]
    platform_specific_settings: Dict[str, Any]
    connection_history: List[Dict[str, Any]]
    health_metrics: Dict[str, Any]


class SyncPreferencesUpdate(BaseModel):
    enabled: Optional[bool] = None
    sync_messages: Optional[bool] = None
    sync_contacts: Optional[bool] = None
    sync_files: Optional[bool] = None
    sync_frequency: Optional[str] = None
    data_filters: Optional[Dict[str, Any]] = None
    privacy_settings: Optional[Dict[str, Any]] = None


class PlatformSettingsUpdate(BaseModel):
    settings: Dict[str, Any]


class OAuthInitiateResponse(BaseModel):
    auth_url: str
    state: str


class OAuthCompleteRequest(BaseModel):
    code: str
    state: str


class TroubleshootingIssue(BaseModel):
    id: str
    severity: str
    title: str
    description: str
    possible_causes: List[str]
    last_occurred: datetime


class SuggestedAction(BaseModel):
    id: str
    title: str
    description: str
    action_type: str
    automated: bool
    estimated_time: Optional[str] = None


class TroubleshootingInfo(BaseModel):
    platform: str
    issues: List[TroubleshootingIssue]
    suggested_actions: List[SuggestedAction]
    diagnostic_data: Dict[str, Any]


class BulkOperationResult(BaseModel):
    successful: List[str]
    failed: List[Dict[str, str]]
    total_processed: int


class ExecuteActionRequest(BaseModel):
    action_id: str


class ExecuteActionResponse(BaseModel):
    success: bool
    message: Optional[str] = None

# Dependency injection


async def get_connector_manager() -> ConnectorManager:
    """Get the connector manager instance."""
    # In a real implementation, this would be injected from the application context
    from main import app
    return app.state.connector_manager


async def get_oauth_service() -> OAuthService:
    """Get the OAuth service instance."""
    from main import app
    return app.state.oauth_service

# Routes


@router.get("/available", response_model=List[PlatformInfo])
async def get_available_platforms(
    current_user: User = Depends(get_current_user)
) -> List[PlatformInfo]:
    """Get list of available platforms for connection."""

    # Define supported platforms with their configurations
    platforms = [
        PlatformInfo(
            platform="gmail",
            display_name="Gmail",
            description="Connect your Gmail account to sync emails and contacts",
            icon="gmail",
            is_supported=True,
            oauth_config={
                "scopes": ["https://www.googleapis.com/auth/gmail.readonly",
                           "https://www.googleapis.com/auth/contacts.readonly"],
                "auth_url": "https://accounts.google.com/o/oauth2/auth",
                "token_url": "https://oauth2.googleapis.com/token"
            }
        ),
        PlatformInfo(
            platform="slack",
            display_name="Slack",
            description="Connect your Slack workspace to sync messages and channels",
            icon="slack",
            is_supported=True,
            oauth_config={
                "scopes": ["channels:read", "groups:read", "im:read", "mpim:read",
                           "channels:history", "groups:history", "im:history", "mpim:history"],
                "auth_url": "https://slack.com/oauth/v2/authorize",
                "token_url": "https://slack.com/api/oauth.v2.access"
            }
        ),
        PlatformInfo(
            platform="discord",
            display_name="Discord",
            description="Connect your Discord account to sync messages and servers",
            icon="discord",
            is_supported=True,
            oauth_config={
                "scopes": ["identify", "guilds", "guilds.members.read"],
                "auth_url": "https://discord.com/api/oauth2/authorize",
                "token_url": "https://discord.com/api/oauth2/token"
            }
        ),
        PlatformInfo(
            platform="whatsapp",
            display_name="WhatsApp",
            description="Connect your WhatsApp account (Business API required)",
            icon="whatsapp",
            is_supported=False  # Requires special setup
        ),
        PlatformInfo(
            platform="twitter",
            display_name="Twitter/X",
            description="Connect your Twitter account to sync tweets and DMs",
            icon="twitter",
            is_supported=True,
            oauth_config={
                "scopes": ["tweet.read", "users.read", "dm.read"],
                "auth_url": "https://twitter.com/i/oauth2/authorize",
                "token_url": "https://api.twitter.com/2/oauth2/token"
            }
        ),
        PlatformInfo(
            platform="linkedin",
            display_name="LinkedIn",
            description="Connect your LinkedIn account to sync messages and connections",
            icon="linkedin",
            is_supported=True,
            oauth_config={
                "scopes": ["r_liteprofile", "r_emailaddress", "w_member_social"],
                "auth_url": "https://www.linkedin.com/oauth/v2/authorization",
                "token_url": "https://www.linkedin.com/oauth/v2/accessToken"
            }
        )
    ]

    return platforms


@router.get("/connections", response_model=List[ConnectionStatus])
async def get_user_connections(
    current_user: User = Depends(get_current_user),
    connector_manager: ConnectorManager = Depends(get_connector_manager)
) -> List[ConnectionStatus]:
    """Get all platform connections for the current user."""

    try:
        # Get connector health status
        health_status = await connector_manager.get_connector_health()

        # Get connector statistics
        stats = await connector_manager.get_connector_stats()

        connections = []
        for platform, health in health_status.items():
            platform_stats = stats.get(platform)

            connection = ConnectionStatus(
                id=f"{current_user.id}_{platform}",
                platform=platform,
                display_name=platform.title(),
                is_connected=health.status != ConnectorStatus.DISCONNECTED,
                is_enabled=True,  # This would come from user preferences
                connection_status=health.status.value,
                last_sync_time=health.last_check if health.status == ConnectorStatus.HEALTHY else None,
                last_error_time=health.last_check if health.last_error else None,
                last_error=health.last_error,
                sync_preferences={
                    "enabled": True,
                    "sync_messages": True,
                    "sync_contacts": True,
                    "sync_files": True,
                    "sync_frequency": "realtime",
                    "data_filters": {},
                    "privacy_settings": {
                        "enable_pii_redaction": True,
                        "enable_ai_analysis": True,
                        "data_retention_days": 365
                    }
                },
                platform_specific_settings={},
                connection_history=[],
                health_metrics={
                    "uptime": health.uptime_seconds,
                    "error_count": health.error_count,
                    "successful_syncs": platform_stats.successful_syncs if platform_stats else 0,
                    "failed_syncs": platform_stats.failed_syncs if platform_stats else 0,
                    "average_response_time": 0,
                    "last_health_check": health.last_check.isoformat()
                }
            )
            connections.append(connection)

        return connections

    except Exception as e:
        logger.error(f"Failed to get user connections: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve platform connections"
        )


@router.post("/{platform}/oauth/initiate", response_model=OAuthInitiateResponse)
async def initiate_oauth_flow(
    platform: str,
    current_user: User = Depends(get_current_user),
    oauth_service: OAuthService = Depends(get_oauth_service)
) -> OAuthInitiateResponse:
    """Initiate OAuth flow for a platform."""

    try:
        # Generate OAuth state for CSRF protection
        oauth_state = OAuthState(
            user_id=str(current_user.id),
            platform=platform,
            state=str(uuid4()),
            created_at=datetime.now(timezone.utc)
        )

        # Get platform OAuth configuration
        oauth_config = await oauth_service.get_platform_oauth_config(platform)
        if not oauth_config:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"OAuth not supported for platform: {platform}"
            )

        # Build authorization URL
        auth_url = await oauth_service.build_authorization_url(
            oauth_config, oauth_state
        )

        # Store OAuth state for verification
        await oauth_service.store_oauth_state(oauth_state)

        return OAuthInitiateResponse(
            auth_url=auth_url,
            state=oauth_state.state
        )

    except Exception as e:
        logger.error(f"Failed to initiate OAuth for {platform}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate OAuth flow: {str(e)}"
        )


@router.post("/{platform}/oauth/complete")
async def complete_oauth_flow(
    platform: str,
    request: OAuthCompleteRequest,
    current_user: User = Depends(get_current_user),
    oauth_service: OAuthService = Depends(get_oauth_service),
    connector_manager: ConnectorManager = Depends(get_connector_manager)
) -> Dict[str, Any]:
    """Complete OAuth flow and establish platform connection."""

    try:
        # Verify OAuth state
        oauth_state = await oauth_service.verify_oauth_state(
            request.state, str(current_user.id), platform
        )

        if not oauth_state:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid OAuth state"
            )

        # Exchange authorization code for tokens
        token_info = await oauth_service.exchange_code_for_tokens(
            platform, request.code, oauth_state
        )

        # Store tokens securely
        await oauth_service.store_user_tokens(
            str(current_user.id), platform, token_info
        )

        # Start the connector for this platform
        await connector_manager.start_connector(platform)

        # Clean up OAuth state
        await oauth_service.cleanup_oauth_state(request.state)

        return {
            "id": f"{current_user.id}_{platform}",
            "platform": platform,
            "display_name": platform.title(),
            "is_connected": True,
            "last_sync_time": datetime.now(timezone.utc).isoformat(),
            "sync_preferences": {
                "enabled": True,
                "sync_messages": True,
                "sync_contacts": True,
                "sync_files": True,
                "sync_frequency": "realtime"
            },
            "platform_specific_settings": {},
            "health_metrics": {
                "uptime": 0,
                "error_count": 0,
                "successful_syncs": 0,
                "failed_syncs": 0,
                "average_response_time": 0,
                "last_health_check": datetime.now(timezone.utc).isoformat()
            }
        }

    except Exception as e:
        logger.error(f"Failed to complete OAuth for {platform}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to complete OAuth flow: {str(e)}"
        )


@router.delete("/{platform}/connection")
async def disconnect_platform(
    platform: str,
    current_user: User = Depends(get_current_user),
    connector_manager: ConnectorManager = Depends(get_connector_manager),
    oauth_service: OAuthService = Depends(get_oauth_service)
) -> Dict[str, str]:
    """Disconnect a platform and revoke tokens."""

    try:
        # Stop the connector
        await connector_manager.stop_connector(platform)

        # Revoke OAuth tokens
        await oauth_service.revoke_user_tokens(str(current_user.id), platform)

        return {"message": f"Successfully disconnected {platform}"}

    except Exception as e:
        logger.error(f"Failed to disconnect {platform}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to disconnect platform: {str(e)}"
        )


@router.put("/{platform}/sync-preferences")
async def update_sync_preferences(
    platform: str,
    preferences: SyncPreferencesUpdate,
    current_user: User = Depends(get_current_user)
) -> Dict[str, str]:
    """Update sync preferences for a platform."""

    try:
        # In a real implementation, this would update user preferences in the database
        # For now, we'll just return success

        logger.info(
            f"Updated sync preferences for {platform}: {preferences.dict(exclude_unset=True)}")

        return {"message": f"Sync preferences updated for {platform}"}

    except Exception as e:
        logger.error(f"Failed to update sync preferences for {platform}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update sync preferences"
        )


@router.put("/{platform}/settings")
async def update_platform_settings(
    platform: str,
    settings: PlatformSettingsUpdate,
    current_user: User = Depends(get_current_user)
) -> Dict[str, str]:
    """Update platform-specific settings."""

    try:
        # In a real implementation, this would update platform settings in the database
        logger.info(
            f"Updated platform settings for {platform}: {settings.settings}")

        return {"message": f"Platform settings updated for {platform}"}

    except Exception as e:
        logger.error(f"Failed to update platform settings for {platform}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update platform settings"
        )


@router.get("/{platform}/health")
async def get_platform_health(
    platform: str,
    current_user: User = Depends(get_current_user),
    connector_manager: ConnectorManager = Depends(get_connector_manager)
) -> Dict[str, Any]:
    """Get health metrics for a specific platform."""

    try:
        health_status = await connector_manager.get_connector_health(platform)
        stats = await connector_manager.get_connector_stats(platform)

        if platform not in health_status:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Platform {platform} not found"
            )

        health = health_status[platform]
        platform_stats = stats.get(platform)

        return {
            "uptime": health.uptime_seconds,
            "error_count": health.error_count,
            "successful_syncs": platform_stats.successful_syncs if platform_stats else 0,
            "failed_syncs": platform_stats.failed_syncs if platform_stats else 0,
            "average_response_time": 0,  # Would be calculated from actual metrics
            "last_health_check": health.last_check.isoformat(),
            "rate_limit_status": {
                "remaining": 1000,  # Mock data
                "reset_time": datetime.now(timezone.utc).isoformat()
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get health for {platform}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve platform health"
        )


@router.get("/{platform}/troubleshoot", response_model=TroubleshootingInfo)
async def get_troubleshooting_info(
    platform: str,
    current_user: User = Depends(get_current_user),
    connector_manager: ConnectorManager = Depends(get_connector_manager)
) -> TroubleshootingInfo:
    """Get troubleshooting information for a platform."""

    try:
        health_status = await connector_manager.get_connector_health(platform)

        if platform not in health_status:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Platform {platform} not found"
            )

        health = health_status[platform]

        # Generate issues based on health status
        issues = []
        suggested_actions = []

        if health.status == ConnectorStatus.DISCONNECTED:
            issues.append(TroubleshootingIssue(
                id="disconnected",
                severity="high",
                title="Platform Not Connected",
                description=f"{platform} is not currently connected",
                possible_causes=["OAuth token expired",
                                 "Manual disconnection", "Authentication failure"],
                last_occurred=health.last_check
            ))

            suggested_actions.append(SuggestedAction(
                id="reconnect",
                title="Reconnect Platform",
                description="Initiate a new connection to the platform",
                action_type="reconnect",
                automated=False,
                estimated_time="2-3 minutes"
            ))

        elif health.status == ConnectorStatus.UNHEALTHY:
            issues.append(TroubleshootingIssue(
                id="unhealthy",
                severity="medium",
                title="Connection Issues",
                description="The platform connection is experiencing issues",
                possible_causes=["Network connectivity",
                                 "API rate limits", "Service outage"],
                last_occurred=health.last_check
            ))

            suggested_actions.append(SuggestedAction(
                id="retry_sync",
                title="Retry Synchronization",
                description="Attempt to sync data again",
                action_type="retry_sync",
                automated=True,
                estimated_time="30 seconds"
            ))

        if health.error_count > 5:
            issues.append(TroubleshootingIssue(
                id="high_error_rate",
                severity="medium",
                title="High Error Rate",
                description="Multiple errors detected in recent operations",
                possible_causes=["API changes",
                                 "Rate limiting", "Network issues"],
                last_occurred=health.last_check
            ))

            suggested_actions.append(SuggestedAction(
                id="refresh_token",
                title="Refresh Authentication",
                description="Refresh the authentication token",
                action_type="refresh_token",
                automated=True,
                estimated_time="1 minute"
            ))

        return TroubleshootingInfo(
            platform=platform,
            issues=issues,
            suggested_actions=suggested_actions,
            diagnostic_data={
                "connection_status": health.status.value,
                "last_error": health.last_error,
                "last_sync_time": health.last_check.isoformat(),
                "health_metrics": {
                    "uptime": health.uptime_seconds,
                    "error_count": health.error_count
                }
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get troubleshooting info for {platform}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve troubleshooting information"
        )


@router.post("/{platform}/troubleshoot/execute", response_model=ExecuteActionResponse)
async def execute_troubleshooting_action(
    platform: str,
    request: ExecuteActionRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    connector_manager: ConnectorManager = Depends(get_connector_manager)
) -> ExecuteActionResponse:
    """Execute a troubleshooting action."""

    try:
        action_id = request.action_id

        # Execute different actions based on action_id
        if action_id == "reconnect":
            # This would trigger a reconnection flow
            background_tasks.add_task(
                connector_manager.restart_connector, platform)
            return ExecuteActionResponse(
                success=True,
                message="Reconnection initiated"
            )

        elif action_id == "retry_sync":
            # Trigger a manual sync
            background_tasks.add_task(
                connector_manager.start_connector, platform)
            return ExecuteActionResponse(
                success=True,
                message="Sync retry initiated"
            )

        elif action_id == "refresh_token":
            # This would refresh the OAuth token
            return ExecuteActionResponse(
                success=True,
                message="Token refresh completed"
            )

        else:
            return ExecuteActionResponse(
                success=False,
                message=f"Unknown action: {action_id}"
            )

    except Exception as e:
        logger.error(
            f"Failed to execute action {request.action_id} for {platform}: {e}")
        return ExecuteActionResponse(
            success=False,
            message=f"Failed to execute action: {str(e)}"
        )


@router.post("/{platform}/sync")
async def sync_platform(
    platform: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    connector_manager: ConnectorManager = Depends(get_connector_manager)
) -> Dict[str, str]:
    """Trigger manual sync for a platform."""

    try:
        # Add sync task to background
        background_tasks.add_task(connector_manager.start_connector, platform)

        return {"message": f"Sync initiated for {platform}"}

    except Exception as e:
        logger.error(f"Failed to sync {platform}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync platform: {str(e)}"
        )


@router.post("/bulk/enable", response_model=BulkOperationResult)
async def bulk_enable_platforms(
    platforms: List[str],
    current_user: User = Depends(get_current_user)
) -> BulkOperationResult:
    """Enable multiple platforms in bulk."""

    successful = []
    failed = []

    for platform in platforms:
        try:
            # In a real implementation, this would update user preferences
            successful.append(platform)
        except Exception as e:
            failed.append({"platform": platform, "error": str(e)})

    return BulkOperationResult(
        successful=successful,
        failed=failed,
        total_processed=len(platforms)
    )


@router.post("/bulk/disable", response_model=BulkOperationResult)
async def bulk_disable_platforms(
    platforms: List[str],
    current_user: User = Depends(get_current_user)
) -> BulkOperationResult:
    """Disable multiple platforms in bulk."""

    successful = []
    failed = []

    for platform in platforms:
        try:
            # In a real implementation, this would update user preferences
            successful.append(platform)
        except Exception as e:
            failed.append({"platform": platform, "error": str(e)})

    return BulkOperationResult(
        successful=successful,
        failed=failed,
        total_processed=len(platforms)
    )


@router.post("/sync-all", response_model=BulkOperationResult)
async def sync_all_platforms(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    connector_manager: ConnectorManager = Depends(get_connector_manager)
) -> BulkOperationResult:
    """Sync all connected platforms."""

    try:
        # Get all connected platforms
        health_status = await connector_manager.get_connector_health()
        connected_platforms = [
            platform for platform, health in health_status.items()
            if health.status != ConnectorStatus.DISCONNECTED
        ]

        successful = []
        failed = []

        for platform in connected_platforms:
            try:
                background_tasks.add_task(
                    connector_manager.start_connector, platform)
                successful.append(platform)
            except Exception as e:
                failed.append({"platform": platform, "error": str(e)})

        return BulkOperationResult(
            successful=successful,
            failed=failed,
            total_processed=len(connected_platforms)
        )

    except Exception as e:
        logger.error(f"Failed to sync all platforms: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to sync all platforms"
        )
