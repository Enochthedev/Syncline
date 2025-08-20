"""
Encryption key rotation utilities with automated scheduling.

This service provides automated key rotation capabilities with
scheduling, notifications, and policy management.
"""

import logging
import asyncio
from typing import Dict, List, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import uuid

from .types import KeyRotationPolicy, KeyType, AuditEventType
from .encryption_service import EncryptionService
from .audit_logger import AuditLogger

logger = logging.getLogger(__name__)


@dataclass
class RotationJob:
    """Represents a scheduled key rotation job."""
    job_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    key_id: str = ""
    key_type: KeyType = KeyType.DATA_ENCRYPTION_KEY
    scheduled_time: datetime = field(default_factory=datetime.utcnow)
    policy: Optional[KeyRotationPolicy] = None
    status: str = "scheduled"  # scheduled, running, completed, failed
    created_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None


class KeyRotationError(Exception):
    """Base exception for key rotation operations."""
    pass


class KeyRotationService:
    """
    Automated key rotation service with scheduling and policy management.

    Provides automated rotation of encryption keys based on policies
    with notifications and audit logging.
    """

    def __init__(
        self,
        encryption_service: EncryptionService,
        audit_logger: AuditLogger,
        notification_callback: Optional[Callable] = None
    ):
        self.encryption_service = encryption_service
        self.audit_logger = audit_logger
        self.notification_callback = notification_callback

        # Rotation policies by key type
        self._policies: Dict[KeyType, KeyRotationPolicy] = {}

        # Scheduled rotation jobs
        self._rotation_jobs: Dict[str, RotationJob] = {}

        # Background task for processing rotations
        self._rotation_task: Optional[asyncio.Task] = None
        self._running = False

        # Default policies
        self._setup_default_policies()

    def _setup_default_policies(self) -> None:
        """Set up default rotation policies."""
        # Data encryption keys - rotate every 90 days
        self._policies[KeyType.DATA_ENCRYPTION_KEY] = KeyRotationPolicy(
            key_type=KeyType.DATA_ENCRYPTION_KEY,
            rotation_interval_days=90,
            advance_notice_days=7,
            auto_rotate=True
        )

        # Token encryption keys - rotate every 30 days
        self._policies[KeyType.TOKEN_ENCRYPTION_KEY] = KeyRotationPolicy(
            key_type=KeyType.TOKEN_ENCRYPTION_KEY,
            rotation_interval_days=30,
            advance_notice_days=3,
            auto_rotate=True
        )

        # Master keys - rotate every 365 days (manual)
        self._policies[KeyType.MASTER_KEY] = KeyRotationPolicy(
            key_type=KeyType.MASTER_KEY,
            rotation_interval_days=365,
            advance_notice_days=30,
            auto_rotate=False  # Manual rotation for master keys
        )

    async def start_rotation_scheduler(self) -> None:
        """Start the background key rotation scheduler."""
        if self._running:
            logger.warning("Key rotation scheduler is already running")
            return

        self._running = True
        self._rotation_task = asyncio.create_task(
            self._rotation_scheduler_loop())

        await self.audit_logger.log_event(
            event_type=AuditEventType.KEY_ROTATION,
            action="start_scheduler",
            details={"scheduler_status": "started"}
        )

        logger.info("Key rotation scheduler started")

    async def stop_rotation_scheduler(self) -> None:
        """Stop the background key rotation scheduler."""
        if not self._running:
            return

        self._running = False
        if self._rotation_task:
            self._rotation_task.cancel()
            try:
                await self._rotation_task
            except asyncio.CancelledError:
                pass

        await self.audit_logger.log_event(
            event_type=AuditEventType.KEY_ROTATION,
            action="stop_scheduler",
            details={"scheduler_status": "stopped"}
        )

        logger.info("Key rotation scheduler stopped")

    async def _rotation_scheduler_loop(self) -> None:
        """Main loop for the rotation scheduler."""
        while self._running:
            try:
                # Check for due rotations every hour
                await self._check_and_schedule_rotations()

                # Process scheduled rotation jobs
                await self._process_rotation_jobs()

                # Sleep for 1 hour
                await asyncio.sleep(3600)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in rotation scheduler loop: {e}")
                await asyncio.sleep(300)  # Sleep 5 minutes on error

    async def _check_and_schedule_rotations(self) -> None:
        """Check for keys that need rotation and schedule jobs."""
        try:
            current_time = datetime.utcnow()

            # This would need to be implemented based on key storage
            # For now, we'll simulate checking keys that need rotation
            keys_needing_rotation = await self._get_keys_needing_rotation()

            for key_info in keys_needing_rotation:
                key_id = key_info["key_id"]
                key_type = KeyType(key_info["key_type"])

                # Check if already scheduled
                if any(job.key_id == key_id and job.status == "scheduled"
                       for job in self._rotation_jobs.values()):
                    continue

                policy = self._policies.get(key_type)
                if not policy:
                    logger.warning(
                        f"No rotation policy found for key type: {key_type}")
                    continue

                # Schedule rotation
                if policy.auto_rotate:
                    await self._schedule_rotation(key_id, key_type, policy)
                else:
                    # Send notification for manual rotation
                    await self._send_rotation_notification(key_id, key_type, policy)

        except Exception as e:
            logger.error(f"Error checking for rotations: {e}")

    async def _get_keys_needing_rotation(self) -> List[Dict[str, str]]:
        """Get list of keys that need rotation."""
        # This would need to be implemented based on key storage
        # For now, return empty list as this requires key storage integration
        return []

    async def _schedule_rotation(
        self,
        key_id: str,
        key_type: KeyType,
        policy: KeyRotationPolicy
    ) -> str:
        """
        Schedule a key rotation job.

        Args:
            key_id: ID of the key to rotate
            key_type: Type of the key
            policy: Rotation policy to apply

        Returns:
            Job ID of the scheduled rotation
        """
        try:
            # Calculate rotation time (immediate for overdue keys)
            scheduled_time = datetime.utcnow()

            # Create rotation job
            job = RotationJob(
                key_id=key_id,
                key_type=key_type,
                scheduled_time=scheduled_time,
                policy=policy
            )

            self._rotation_jobs[job.job_id] = job

            await self.audit_logger.log_event(
                event_type=AuditEventType.KEY_ROTATION,
                action="schedule_rotation",
                resource_type="encryption_key",
                resource_id=key_id,
                details={
                    "job_id": job.job_id,
                    "key_type": key_type.value,
                    "scheduled_time": scheduled_time.isoformat(),
                    "auto_rotate": policy.auto_rotate
                }
            )

            logger.info(
                f"Scheduled key rotation: {key_id} (job: {job.job_id})")
            return job.job_id

        except Exception as e:
            await self.audit_logger.log_event(
                event_type=AuditEventType.KEY_ROTATION,
                action="schedule_rotation",
                resource_type="encryption_key",
                resource_id=key_id,
                success=False,
                error_message=str(e),
                details={"key_type": key_type.value}
            )
            logger.error(f"Failed to schedule rotation for key {key_id}: {e}")
            raise KeyRotationError(f"Failed to schedule rotation: {e}")

    async def _process_rotation_jobs(self) -> None:
        """Process scheduled rotation jobs."""
        current_time = datetime.utcnow()

        # Find jobs that are due
        due_jobs = [
            job for job in self._rotation_jobs.values()
            if job.status == "scheduled" and job.scheduled_time <= current_time
        ]

        for job in due_jobs:
            await self._execute_rotation_job(job)

    async def _execute_rotation_job(self, job: RotationJob) -> None:
        """Execute a rotation job."""
        try:
            job.status = "running"

            await self.audit_logger.log_event(
                event_type=AuditEventType.KEY_ROTATION,
                action="start_rotation",
                resource_type="encryption_key",
                resource_id=job.key_id,
                details={
                    "job_id": job.job_id,
                    "key_type": job.key_type.value
                }
            )

            # Perform the actual key rotation
            new_key = await self.encryption_service.rotate_key(job.key_id)

            # Mark job as completed
            job.status = "completed"
            job.completed_at = datetime.utcnow()

            await self.audit_logger.log_event(
                event_type=AuditEventType.KEY_ROTATION,
                action="complete_rotation",
                resource_type="encryption_key",
                resource_id=job.key_id,
                details={
                    "job_id": job.job_id,
                    "key_type": job.key_type.value,
                    "new_key_id": new_key.key_id,
                    "duration_seconds": (job.completed_at - job.created_at).total_seconds()
                }
            )

            # Send completion notification
            if self.notification_callback:
                await self.notification_callback(
                    "key_rotation_completed",
                    {
                        "key_id": job.key_id,
                        "new_key_id": new_key.key_id,
                        "key_type": job.key_type.value,
                        "job_id": job.job_id
                    }
                )

            logger.info(
                f"Key rotation completed: {job.key_id} -> {new_key.key_id}")

        except Exception as e:
            job.status = "failed"
            job.error_message = str(e)
            job.completed_at = datetime.utcnow()

            await self.audit_logger.log_event(
                event_type=AuditEventType.KEY_ROTATION,
                action="rotation_failed",
                resource_type="encryption_key",
                resource_id=job.key_id,
                success=False,
                error_message=str(e),
                details={
                    "job_id": job.job_id,
                    "key_type": job.key_type.value
                }
            )

            # Send failure notification
            if self.notification_callback:
                await self.notification_callback(
                    "key_rotation_failed",
                    {
                        "key_id": job.key_id,
                        "key_type": job.key_type.value,
                        "job_id": job.job_id,
                        "error": str(e)
                    }
                )

            logger.error(f"Key rotation failed for {job.key_id}: {e}")

    async def _send_rotation_notification(
        self,
        key_id: str,
        key_type: KeyType,
        policy: KeyRotationPolicy
    ) -> None:
        """Send notification for manual key rotation."""
        if self.notification_callback:
            await self.notification_callback(
                "key_rotation_required",
                {
                    "key_id": key_id,
                    "key_type": key_type.value,
                    "policy": {
                        "rotation_interval_days": policy.rotation_interval_days,
                        "advance_notice_days": policy.advance_notice_days,
                        "auto_rotate": policy.auto_rotate
                    }
                }
            )

        await self.audit_logger.log_event(
            event_type=AuditEventType.KEY_ROTATION,
            action="rotation_notification_sent",
            resource_type="encryption_key",
            resource_id=key_id,
            details={
                "key_type": key_type.value,
                "manual_rotation_required": True
            }
        )

    async def rotate_key_immediately(
        self,
        key_id: str,
        key_type: KeyType,
        reason: str = "manual_rotation"
    ) -> str:
        """
        Rotate a key immediately.

        Args:
            key_id: ID of the key to rotate
            key_type: Type of the key
            reason: Reason for immediate rotation

        Returns:
            Job ID of the rotation
        """
        try:
            policy = self._policies.get(key_type)
            if not policy:
                # Create temporary policy for immediate rotation
                policy = KeyRotationPolicy(
                    key_type=key_type,
                    rotation_interval_days=0,
                    auto_rotate=True
                )

            # Schedule immediate rotation
            job_id = await self._schedule_rotation(key_id, key_type, policy)

            # Process the job immediately
            job = self._rotation_jobs[job_id]
            await self._execute_rotation_job(job)

            return job_id

        except Exception as e:
            logger.error(f"Failed to rotate key immediately {key_id}: {e}")
            raise KeyRotationError(f"Immediate rotation failed: {e}")

    def set_rotation_policy(
        self,
        key_type: KeyType,
        policy: KeyRotationPolicy
    ) -> None:
        """
        Set rotation policy for a key type.

        Args:
            key_type: Type of key
            policy: Rotation policy to set
        """
        self._policies[key_type] = policy
        logger.info(
            f"Set rotation policy for {key_type.value}: {policy.rotation_interval_days} days")

    def get_rotation_policy(self, key_type: KeyType) -> Optional[KeyRotationPolicy]:
        """Get rotation policy for a key type."""
        return self._policies.get(key_type)

    def get_rotation_jobs(
        self,
        status: Optional[str] = None,
        key_type: Optional[KeyType] = None
    ) -> List[RotationJob]:
        """
        Get rotation jobs with optional filters.

        Args:
            status: Filter by job status
            key_type: Filter by key type

        Returns:
            List of rotation jobs matching filters
        """
        jobs = list(self._rotation_jobs.values())

        if status:
            jobs = [job for job in jobs if job.status == status]

        if key_type:
            jobs = [job for job in jobs if job.key_type == key_type]

        return jobs

    async def cleanup_completed_jobs(self, older_than_days: int = 30) -> int:
        """
        Clean up completed rotation jobs older than specified days.

        Args:
            older_than_days: Remove jobs completed more than this many days ago

        Returns:
            Number of jobs cleaned up
        """
        cutoff_date = datetime.utcnow() - timedelta(days=older_than_days)

        jobs_to_remove = []
        for job_id, job in self._rotation_jobs.items():
            if (job.status in ["completed", "failed"] and
                job.completed_at and
                    job.completed_at < cutoff_date):
                jobs_to_remove.append(job_id)

        for job_id in jobs_to_remove:
            del self._rotation_jobs[job_id]

        if jobs_to_remove:
            await self.audit_logger.log_event(
                event_type=AuditEventType.KEY_ROTATION,
                action="cleanup_jobs",
                details={
                    "cleaned_jobs_count": len(jobs_to_remove),
                    "older_than_days": older_than_days
                }
            )

        logger.info(
            f"Cleaned up {len(jobs_to_remove)} completed rotation jobs")
        return len(jobs_to_remove)
