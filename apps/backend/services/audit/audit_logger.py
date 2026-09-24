"""
Audit Logging Service

Tracks data access and modifications for compliance:
- User actions (CRUD operations)
- Data access events
- Configuration changes
- Authentication events
- System events
"""

import logging
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from db.models.audit import AuditLog

logger = logging.getLogger(__name__)


class AuditAction(str, Enum):
    """Audit action types."""

    # Authentication
    LOGIN = "login"
    LOGOUT = "logout"
    LOGIN_FAILED = "login_failed"

    # Data access
    READ = "read"
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"

    # Configuration
    CONFIG_CHANGE = "config_change"

    # System events
    SYSTEM_START = "system_start"
    SYSTEM_STOP = "system_stop"
    ERROR = "error"


class AuditLogger:
    """
    Service for audit logging.

    Provides methods to log various types of events.
    """

    async def log(
        self,
        db: AsyncSession,
        action: AuditAction,
        user_id: Optional[UUID] = None,
        username: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        endpoint: Optional[str] = None,
        method: Optional[str] = None,
        status_code: Optional[int] = None,
        success: bool = True,
        details: Optional[dict[str, Any]] = None,
        error_message: Optional[str] = None,
        correlation_id: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> AuditLog:
        """
        Log an audit event.

        Args:
            db: Database session
            action: Action type
            user_id: User ID
            username: Username
            resource_type: Resource type (e.g., "message", "connection")
            resource_id: Resource ID
            ip_address: Client IP address
            user_agent: User agent string
            endpoint: API endpoint
            method: HTTP method
            status_code: HTTP status code
            success: Whether action succeeded
            details: Additional details
            error_message: Error message if failed
            correlation_id: Correlation ID
            request_id: Request ID

        Returns:
            Created audit log entry
        """
        audit_entry = AuditLog(
            user_id=user_id,
            username=username,
            action=action.value,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
            endpoint=endpoint,
            method=method,
            status_code=status_code,
            success=success,
            details=details,
            error_message=error_message,
            correlation_id=correlation_id,
            request_id=request_id,
        )

        db.add(audit_entry)
        await db.commit()

        logger.debug(f"Audit log created: {action.value} by {username or 'system'}")

        return audit_entry

    async def log_data_access(
        self,
        db: AsyncSession,
        user_id: UUID,
        username: str,
        resource_type: str,
        resource_id: str,
        action: AuditAction = AuditAction.READ,
        **kwargs,
    ) -> AuditLog:
        """
        Log data access event.

        Args:
            db: Database session
            user_id: User ID
            username: Username
            resource_type: Type of resource accessed
            resource_id: ID of resource accessed
            action: Action performed
            **kwargs: Additional audit log fields

        Returns:
            Audit log entry
        """
        return await self.log(
            db=db,
            action=action,
            user_id=user_id,
            username=username,
            resource_type=resource_type,
            resource_id=resource_id,
            **kwargs,
        )


# Global service instance
_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """
    Get the global audit logger instance.

    Returns:
        Audit logger
    """
    global _audit_logger

    if _audit_logger is None:
        _audit_logger = AuditLogger()

    return _audit_logger


__all__ = [
    "AuditLogger",
    "AuditLog",
    "AuditAction",
    "get_audit_logger",
]
