"""
Audit logging service with immutable timestamps and compliance tracking.

This service provides comprehensive audit logging for all security-related
operations with immutable timestamps and compliance features.
"""

import logging
import json
import hashlib
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
import uuid
import asyncio
from contextlib import asynccontextmanager

from .types import AuditEvent, AuditEventType, AuditSeverity
from ..storage.backends import get_storage_backend
from db.session import get_async_session
from db.models.audit import AuditLog
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import timedelta

logger = logging.getLogger(__name__)


class AuditLoggerError(Exception):
    """Base exception for audit logger operations."""
    pass


class AuditLogger:
    """
    Audit logging service with immutable timestamps and compliance tracking.

    Provides comprehensive audit logging for security operations with
    tamper-evident logging and compliance features.
    """

    def __init__(
        self,
        storage_backend: Optional[Any] = None,
        enable_database_logging: bool = True,
        enable_file_logging: bool = True,
        retention_days: int = 2555  # 7 years for compliance
    ):
        self.storage_backend = storage_backend or get_storage_backend()
        self.enable_database_logging = enable_database_logging
        self.enable_file_logging = enable_file_logging
        self.retention_days = retention_days
        self._event_queue: List[AuditEvent] = []
        self._batch_size = 100
        self._flush_interval = 30  # seconds
        self._last_flush = datetime.utcnow()

        # Background flush task will be started when needed
        self._background_task: Optional[asyncio.Task] = None

    async def _ensure_background_task(self) -> None:
        """Ensure background flush task is running."""
        if self._background_task is None or self._background_task.done():
            try:
                self._background_task = asyncio.create_task(
                    self._background_flush())
            except RuntimeError:
                # No event loop running, skip background task
                pass

    async def log_event(
        self,
        event_type: AuditEventType,
        action: str,
        user_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        severity: AuditSeverity = AuditSeverity.LOW,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        session_id: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None
    ) -> str:
        """
        Log an audit event.

        Args:
            event_type: Type of audit event
            action: Action being performed
            user_id: ID of user performing the action
            resource_type: Type of resource being accessed
            resource_id: ID of resource being accessed
            severity: Severity level of the event
            details: Additional event details
            ip_address: IP address of the request
            user_agent: User agent string
            session_id: Session ID
            success: Whether the action was successful
            error_message: Error message if action failed

        Returns:
            Event ID of the logged event
        """
        try:
            # Create audit event
            event = AuditEvent(
                event_type=event_type,
                action=action,
                user_id=user_id,
                resource_type=resource_type,
                resource_id=resource_id,
                severity=severity,
                details=details or {},
                ip_address=ip_address,
                user_agent=user_agent,
                session_id=session_id,
                success=success,
                error_message=error_message,
                timestamp=datetime.now(timezone.utc)  # Immutable UTC timestamp
            )

            # Ensure background task is running
            await self._ensure_background_task()

            # Add to queue for batch processing
            self._event_queue.append(event)

            # Flush if queue is full or high severity event
            if len(self._event_queue) >= self._batch_size or severity in [AuditSeverity.HIGH, AuditSeverity.CRITICAL]:
                await self._flush_events()

            return event.event_id

        except Exception as e:
            logger.error(f"Failed to log audit event: {e}")
            # Don't raise exception to avoid breaking the main operation
            return str(uuid.uuid4())

    async def _flush_events(self) -> None:
        """Flush queued events to storage."""
        if not self._event_queue:
            return

        events_to_flush = self._event_queue.copy()
        self._event_queue.clear()

        try:
            # Log to database
            if self.enable_database_logging:
                await self._log_to_database(events_to_flush)

            # Log to file storage
            if self.enable_file_logging:
                await self._log_to_file(events_to_flush)

            self._last_flush = datetime.utcnow()

        except Exception as e:
            logger.error(f"Failed to flush audit events: {e}")
            # Re-queue events for retry
            self._event_queue.extend(events_to_flush)

    async def _log_to_database(self, events: List[AuditEvent]) -> None:
        """Log events to database."""
        try:
            async with get_async_session() as session:
                audit_logs = []
                for event in events:
                    # Create integrity hash
                    integrity_hash = self._calculate_integrity_hash(event)

                    audit_log = AuditLog(
                        event_id=event.event_id,
                        event_type=event.event_type.value if hasattr(
                            event.event_type, 'value') else str(event.event_type),
                        action=event.action,
                        user_id=event.user_id,
                        resource_type=event.resource_type,
                        resource_id=event.resource_id,
                        severity=event.severity.value if hasattr(
                            event.severity, 'value') else str(event.severity),
                        timestamp=event.timestamp,
                        details=event.details,
                        ip_address=event.ip_address,
                        user_agent=event.user_agent,
                        session_id=event.session_id,
                        success=event.success,
                        error_message=event.error_message,
                        integrity_hash=integrity_hash
                    )
                    audit_logs.append(audit_log)

                session.add_all(audit_logs)
                await session.commit()

        except Exception as e:
            logger.error(f"Failed to log events to database: {e}")
            raise

    async def _log_to_file(self, events: List[AuditEvent]) -> None:
        """Log events to file storage."""
        try:
            # Group events by date for file organization
            events_by_date = {}
            for event in events:
                date_key = event.timestamp.strftime('%Y-%m-%d')
                if date_key not in events_by_date:
                    events_by_date[date_key] = []
                events_by_date[date_key].append(event)

            # Write to separate files by date
            for date_key, date_events in events_by_date.items():
                file_path = f"audit_logs/{date_key}/audit.jsonl"

                # Convert events to JSON lines
                log_lines = []
                for event in date_events:
                    log_entry = {
                        "event_id": event.event_id,
                        "event_type": event.event_type.value,
                        "action": event.action,
                        "user_id": event.user_id,
                        "resource_type": event.resource_type,
                        "resource_id": event.resource_id,
                        "severity": event.severity.value,
                        "timestamp": event.timestamp.isoformat(),
                        "details": event.details,
                        "ip_address": event.ip_address,
                        "user_agent": event.user_agent,
                        "session_id": event.session_id,
                        "success": event.success,
                        "error_message": event.error_message,
                        "integrity_hash": self._calculate_integrity_hash(event)
                    }
                    log_lines.append(json.dumps(log_entry, sort_keys=True))

                # Append to file
                content = "\n".join(log_lines) + "\n"
                await self.storage_backend.append(file_path, content)

        except Exception as e:
            logger.error(f"Failed to log events to file: {e}")
            raise

    def _calculate_integrity_hash(self, event: AuditEvent) -> str:
        """Calculate integrity hash for tamper detection."""
        # Create deterministic string representation
        hash_data = {
            "event_id": event.event_id,
            "event_type": event.event_type.value,
            "action": event.action,
            "user_id": event.user_id,
            "resource_type": event.resource_type,
            "resource_id": event.resource_id,
            "severity": event.severity.value,
            "timestamp": event.timestamp.isoformat(),
            "details": event.details,
            "success": event.success,
            "error_message": event.error_message
        }

        # Create JSON string with sorted keys for consistency
        hash_string = json.dumps(
            hash_data, sort_keys=True, separators=(',', ':'))

        # Calculate SHA-256 hash
        return hashlib.sha256(hash_string.encode('utf-8')).hexdigest()

    async def _background_flush(self) -> None:
        """Background task to flush events periodically."""
        while True:
            try:
                await asyncio.sleep(self._flush_interval)

                # Check if we need to flush
                time_since_flush = (datetime.utcnow() -
                                    self._last_flush).total_seconds()
                if self._event_queue and time_since_flush >= self._flush_interval:
                    await self._flush_events()

            except Exception as e:
                logger.error(f"Background flush error: {e}")

    async def search_events(
        self,
        event_type: Optional[AuditEventType] = None,
        action: Optional[str] = None,
        user_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        severity: Optional[AuditSeverity] = None,
        success: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Search audit events with filters.

        Args:
            event_type: Filter by event type
            action: Filter by action
            user_id: Filter by user ID
            resource_type: Filter by resource type
            resource_id: Filter by resource ID
            start_time: Filter events after this time
            end_time: Filter events before this time
            severity: Filter by severity level
            success: Filter by success status
            limit: Maximum number of results
            offset: Offset for pagination

        Returns:
            List of audit events matching the filters
        """
        try:
            async with get_async_session() as session:
                query = select(AuditLog)

                # Apply filters
                conditions = []
                if event_type:
                    event_type_value = event_type.value if hasattr(
                        event_type, 'value') else str(event_type)
                    conditions.append(AuditLog.event_type == event_type_value)
                if action:
                    conditions.append(AuditLog.action == action)
                if user_id:
                    conditions.append(AuditLog.user_id == user_id)
                if resource_type:
                    conditions.append(AuditLog.resource_type == resource_type)
                if resource_id:
                    conditions.append(AuditLog.resource_id == resource_id)
                if start_time:
                    conditions.append(AuditLog.timestamp >= start_time)
                if end_time:
                    conditions.append(AuditLog.timestamp <= end_time)
                if severity:
                    severity_value = severity.value if hasattr(
                        severity, 'value') else str(severity)
                    conditions.append(AuditLog.severity == severity_value)
                if success is not None:
                    conditions.append(AuditLog.success == success)

                if conditions:
                    query = query.where(and_(*conditions))

                # Order by timestamp descending
                query = query.order_by(AuditLog.timestamp.desc())

                # Apply pagination
                query = query.offset(offset).limit(limit)

                result = await session.execute(query)
                audit_logs = result.scalars().all()

                # Convert to dict format
                events = []
                for log in audit_logs:
                    events.append({
                        "event_id": log.event_id,
                        "event_type": log.event_type,
                        "action": log.action,
                        "user_id": log.user_id,
                        "resource_type": log.resource_type,
                        "resource_id": log.resource_id,
                        "severity": log.severity,
                        "timestamp": log.timestamp.isoformat(),
                        "details": log.details,
                        "ip_address": log.ip_address,
                        "user_agent": log.user_agent,
                        "session_id": log.session_id,
                        "success": log.success,
                        "error_message": log.error_message,
                        "integrity_hash": log.integrity_hash
                    })

                return events

        except Exception as e:
            logger.error(f"Failed to search audit events: {e}")
            raise AuditLoggerError(f"Search failed: {e}")

    async def verify_integrity(
        self,
        event_id: str
    ) -> bool:
        """
        Verify the integrity of an audit event.

        Args:
            event_id: ID of the event to verify

        Returns:
            True if integrity is verified, False otherwise
        """
        try:
            async with get_async_session() as session:
                query = select(AuditLog).where(AuditLog.event_id == event_id)
                result = await session.execute(query)
                audit_log = result.scalar_one_or_none()

                if not audit_log:
                    return False

                # Recreate the event for hash calculation
                event = AuditEvent(
                    event_id=audit_log.event_id,
                    event_type=AuditEventType(audit_log.event_type),
                    action=audit_log.action,
                    user_id=audit_log.user_id,
                    resource_type=audit_log.resource_type,
                    resource_id=audit_log.resource_id,
                    severity=AuditSeverity(audit_log.severity),
                    timestamp=audit_log.timestamp,
                    details=audit_log.details or {},
                    success=audit_log.success,
                    error_message=audit_log.error_message
                )

                # Calculate expected hash
                expected_hash = self._calculate_integrity_hash(event)

                # Compare with stored hash
                return expected_hash == audit_log.integrity_hash

        except Exception as e:
            logger.error(
                f"Failed to verify integrity for event {event_id}: {e}")
            return False

    async def cleanup_old_events(self) -> int:
        """
        Clean up audit events older than retention period.

        Returns:
            Number of events cleaned up
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=self.retention_days)

            async with get_async_session() as session:
                # Count events to be deleted
                count_query = select(AuditLog).where(
                    AuditLog.timestamp < cutoff_date)
                count_result = await session.execute(count_query)
                count = len(count_result.scalars().all())

                # Delete old events
                delete_query = AuditLog.__table__.delete().where(AuditLog.timestamp < cutoff_date)
                await session.execute(delete_query)
                await session.commit()

                logger.info(f"Cleaned up {count} old audit events")
                return count

        except Exception as e:
            logger.error(f"Failed to cleanup old audit events: {e}")
            raise AuditLoggerError(f"Cleanup failed: {e}")

    async def get_statistics(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get audit statistics for a time period.

        Args:
            start_time: Start of time period
            end_time: End of time period

        Returns:
            Dictionary with audit statistics
        """
        try:
            async with get_async_session() as session:
                query = select(AuditLog)

                # Apply time filters
                conditions = []
                if start_time:
                    conditions.append(AuditLog.timestamp >= start_time)
                if end_time:
                    conditions.append(AuditLog.timestamp <= end_time)

                if conditions:
                    query = query.where(and_(*conditions))

                result = await session.execute(query)
                events = result.scalars().all()

                # Calculate statistics
                total_events = len(events)
                successful_events = sum(1 for e in events if e.success)
                failed_events = total_events - successful_events

                # Group by event type
                event_types = {}
                for event in events:
                    event_type = event.event_type
                    if event_type not in event_types:
                        event_types[event_type] = 0
                    event_types[event_type] += 1

                # Group by severity
                severities = {}
                for event in events:
                    severity = event.severity
                    if severity not in severities:
                        severities[severity] = 0
                    severities[severity] += 1

                return {
                    "total_events": total_events,
                    "successful_events": successful_events,
                    "failed_events": failed_events,
                    "success_rate": successful_events / total_events if total_events > 0 else 0,
                    "event_types": event_types,
                    "severities": severities,
                    "time_period": {
                        "start": start_time.isoformat() if start_time else None,
                        "end": end_time.isoformat() if end_time else None
                    }
                }

        except Exception as e:
            logger.error(f"Failed to get audit statistics: {e}")
            raise AuditLoggerError(f"Statistics failed: {e}")
