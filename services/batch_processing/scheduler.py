"""
Batch Processing Scheduler

Manages scheduling and execution of batch processing jobs including:
- Daily and weekly digest generation
- Entity graph building
- Memory optimization
- Data retention cleanup
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any
# Note: croniter would be imported in production
# from croniter import croniter
import json

from config.config import settings
from services.event_bus import EventBus, EventType
from db.session import get_async_session
from db.models.user import User
from db.models.tenant import Tenant

from .types import (
    BatchJob,
    BatchJobType,
    BatchJobStatus,
    ScheduleConfig,
    BatchJobResult,
    DigestRequest,
    DigestType,
    EntityGraphRequest,
    EntityGraphScope,
    MemoryOptimizationRequest,
    MemoryOptimizationType,
    RetentionRequest,
    RetentionPolicy
)

logger = logging.getLogger(__name__)


class BatchScheduler:
    """
    Scheduler for batch processing jobs with cron-like scheduling.

    Provides:
    - Cron-based job scheduling
    - Job queue management
    - Retry logic with exponential backoff
    - Resource management and throttling
    - Progress tracking and monitoring
    """

    def __init__(self, event_bus: Optional[EventBus] = None):
        """Initialize the batch scheduler."""
        self.event_bus = event_bus
        self._running = False
        self._jobs: Dict[str, BatchJob] = {}
        self._schedules: Dict[str, ScheduleConfig] = {}
        self._job_handlers: Dict[BatchJobType, Callable] = {}
        self._scheduler_task: Optional[asyncio.Task] = None

        # Resource limits
        self.max_concurrent_jobs = getattr(
            settings, 'BATCH_MAX_CONCURRENT_JOBS', 3)
        self.max_memory_mb = getattr(settings, 'BATCH_MAX_MEMORY_MB', 2048)
        self.job_timeout_minutes = getattr(
            settings, 'BATCH_JOB_TIMEOUT_MINUTES', 60)

        # Statistics
        self.stats = {
            'jobs_scheduled': 0,
            'jobs_completed': 0,
            'jobs_failed': 0,
            'total_runtime_seconds': 0.0,
            'last_schedule_check': None
        }

        logger.info("Initialized BatchScheduler")

    async def start(self) -> None:
        """Start the batch scheduler."""
        if self._running:
            logger.warning("BatchScheduler is already running")
            return

        self._running = True

        # Register default job handlers
        await self._register_default_handlers()

        # Set up default schedules
        await self._setup_default_schedules()

        # Start scheduler loop
        self._scheduler_task = asyncio.create_task(self._scheduler_loop())

        logger.info("BatchScheduler started")

    async def stop(self) -> None:
        """Stop the batch scheduler."""
        if not self._running:
            return

        self._running = False

        # Cancel scheduler task
        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass

        # Wait for running jobs to complete (with timeout)
        running_jobs = [job for job in self._jobs.values()
                        if job.status == BatchJobStatus.RUNNING]

        if running_jobs:
            logger.info(
                f"Waiting for {len(running_jobs)} running jobs to complete...")
            await asyncio.sleep(5)  # Give jobs time to finish gracefully

        logger.info("BatchScheduler stopped")

    def register_job_handler(self, job_type: BatchJobType, handler: Callable) -> None:
        """Register a handler for a specific job type."""
        self._job_handlers[job_type] = handler
        logger.info(f"Registered handler for job type: {job_type}")

    def add_schedule(self, schedule: ScheduleConfig) -> None:
        """Add a scheduled job configuration."""
        schedule_id = f"{schedule.job_type}_{schedule.cron_expression}"
        self._schedules[schedule_id] = schedule
        logger.info(
            f"Added schedule: {schedule.name} ({schedule.cron_expression})")

    async def schedule_job(self, job: BatchJob) -> str:
        """Schedule a batch job for execution."""
        self._jobs[job.id] = job
        self.stats['jobs_scheduled'] += 1

        logger.info(f"Scheduled job {job.id} of type {job.type}")

        # Publish event if event bus is available
        if self.event_bus:
            await self.event_bus.publish(
                EventType.BATCH_JOB_SCHEDULED,
                {
                    'job_id': job.id,
                    'job_type': job.type.value,
                    'scheduled_at': job.scheduled_at.isoformat(),
                    'tenant_id': job.tenant_id
                }
            )

        return job.id

    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a scheduled or running job."""
        if job_id not in self._jobs:
            return False

        job = self._jobs[job_id]

        if job.status in [BatchJobStatus.COMPLETED, BatchJobStatus.FAILED, BatchJobStatus.CANCELLED]:
            return False

        job.status = BatchJobStatus.CANCELLED
        job.updated_at = datetime.utcnow()

        logger.info(f"Cancelled job {job_id}")
        return True

    def get_job_status(self, job_id: str) -> Optional[BatchJob]:
        """Get the status of a specific job."""
        return self._jobs.get(job_id)

    def get_jobs_by_type(self, job_type: BatchJobType) -> List[BatchJob]:
        """Get all jobs of a specific type."""
        return [job for job in self._jobs.values() if job.type == job_type]

    def get_running_jobs(self) -> List[BatchJob]:
        """Get all currently running jobs."""
        return [job for job in self._jobs.values() if job.status == BatchJobStatus.RUNNING]

    async def _scheduler_loop(self) -> None:
        """Main scheduler loop that checks for jobs to execute."""
        while self._running:
            try:
                await self._check_scheduled_jobs()
                await self._execute_pending_jobs()
                await self._cleanup_old_jobs()

                self.stats['last_schedule_check'] = datetime.utcnow()

                # Sleep for 60 seconds before next check
                await asyncio.sleep(60)

            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                await asyncio.sleep(60)

    async def _check_scheduled_jobs(self) -> None:
        """Check for scheduled jobs that need to be created."""
        now = datetime.utcnow()

        for schedule_id, schedule in self._schedules.items():
            if not schedule.enabled:
                continue

            try:
                # Check if it's time to run this schedule
                # In production, would use croniter for proper cron parsing
                # For now, simulate schedule checking
                next_run = now - timedelta(hours=1)  # Simplified scheduling

                # Check if we need to create a job for this schedule
                recent_jobs = [
                    job for job in self._jobs.values()
                    if (job.type == schedule.job_type and
                        job.scheduled_at >= next_run and
                        job.scheduled_at <= now)
                ]

                if not recent_jobs:
                    # Create new job for this schedule
                    await self._create_scheduled_job(schedule)

            except Exception as e:
                logger.error(f"Error checking schedule {schedule_id}: {e}")

    async def _create_scheduled_job(self, schedule: ScheduleConfig) -> None:
        """Create a job from a schedule configuration."""
        # Get tenants to process
        tenants = await self._get_tenants_for_schedule(schedule)

        for tenant_id in tenants:
            # Create job parameters based on schedule type
            parameters = await self._build_job_parameters(schedule, tenant_id)

            job = BatchJob(
                type=schedule.job_type,
                tenant_id=tenant_id,
                parameters=parameters,
                scheduled_at=datetime.utcnow()
            )

            await self.schedule_job(job)

    async def _execute_pending_jobs(self) -> None:
        """Execute pending jobs that are ready to run."""
        # Get jobs ready for execution
        now = datetime.utcnow()
        pending_jobs = [
            job for job in self._jobs.values()
            if (job.status == BatchJobStatus.PENDING and
                job.scheduled_at <= now)
        ]

        # Sort by priority (scheduled_at for now)
        pending_jobs.sort(key=lambda j: j.scheduled_at)

        # Check resource limits
        running_count = len(self.get_running_jobs())
        available_slots = self.max_concurrent_jobs - running_count

        # Execute jobs up to resource limits
        for job in pending_jobs[:available_slots]:
            await self._execute_job(job)

    async def _execute_job(self, job: BatchJob) -> None:
        """Execute a single batch job."""
        if job.type not in self._job_handlers:
            job.status = BatchJobStatus.FAILED
            job.error_message = f"No handler registered for job type: {job.type}"
            logger.error(job.error_message)
            return

        job.status = BatchJobStatus.RUNNING
        job.started_at = datetime.utcnow()
        job.updated_at = datetime.utcnow()

        logger.info(f"Starting execution of job {job.id} ({job.type})")

        try:
            # Execute job with timeout
            handler = self._job_handlers[job.type]

            # Create timeout task
            timeout_seconds = self.job_timeout_minutes * 60
            result = await asyncio.wait_for(
                handler(job),
                timeout=timeout_seconds
            )

            # Update job with results
            if isinstance(result, BatchJobResult):
                job.result_data = {
                    'success': result.success,
                    'items_processed': result.items_processed,
                    'items_failed': result.items_failed,
                    'duration_seconds': result.duration_seconds,
                    'summary': result.summary
                }
                job.metrics = {
                    'memory_peak_mb': result.memory_peak_mb,
                    'cpu_time_seconds': result.cpu_time_seconds
                }

                if result.success:
                    job.status = BatchJobStatus.COMPLETED
                    self.stats['jobs_completed'] += 1
                else:
                    job.status = BatchJobStatus.FAILED
                    job.error_message = result.error_details
                    self.stats['jobs_failed'] += 1
            else:
                job.status = BatchJobStatus.COMPLETED
                job.result_data = {'result': str(result)}
                self.stats['jobs_completed'] += 1

            job.completed_at = datetime.utcnow()
            job.progress = 100.0

            # Update statistics
            if job.started_at:
                duration = (job.completed_at - job.started_at).total_seconds()
                self.stats['total_runtime_seconds'] += duration

            logger.info(f"Completed job {job.id} with status {job.status}")

        except asyncio.TimeoutError:
            job.status = BatchJobStatus.FAILED
            job.error_message = f"Job timed out after {self.job_timeout_minutes} minutes"
            job.completed_at = datetime.utcnow()
            self.stats['jobs_failed'] += 1
            logger.error(f"Job {job.id} timed out")

        except Exception as e:
            job.status = BatchJobStatus.FAILED
            job.error_message = str(e)
            job.completed_at = datetime.utcnow()
            self.stats['jobs_failed'] += 1
            logger.error(f"Job {job.id} failed: {e}")

            # Check if we should retry
            if job.retry_count < job.max_retries:
                await self._schedule_retry(job)

        finally:
            job.updated_at = datetime.utcnow()

            # Publish completion event
            if self.event_bus:
                await self.event_bus.publish(
                    EventType.BATCH_JOB_COMPLETED,
                    {
                        'job_id': job.id,
                        'job_type': job.type.value,
                        'status': job.status.value,
                        'duration_seconds': (job.completed_at - job.started_at).total_seconds() if job.started_at and job.completed_at else 0,
                        'tenant_id': job.tenant_id
                    }
                )

    async def _schedule_retry(self, job: BatchJob) -> None:
        """Schedule a job for retry with exponential backoff."""
        job.retry_count += 1
        job.status = BatchJobStatus.RETRYING

        # Calculate retry delay (exponential backoff)
        delay_minutes = 2 ** job.retry_count  # 2, 4, 8, 16 minutes
        job.scheduled_at = datetime.utcnow() + timedelta(minutes=delay_minutes)

        logger.info(
            f"Scheduled retry {job.retry_count}/{job.max_retries} for job {job.id} in {delay_minutes} minutes")

    async def _cleanup_old_jobs(self) -> None:
        """Clean up old completed/failed jobs to prevent memory leaks."""
        cutoff_time = datetime.utcnow() - timedelta(hours=24)

        old_jobs = [
            job_id for job_id, job in self._jobs.items()
            if (job.status in [BatchJobStatus.COMPLETED, BatchJobStatus.FAILED, BatchJobStatus.CANCELLED] and
                job.updated_at < cutoff_time)
        ]

        for job_id in old_jobs:
            del self._jobs[job_id]

        if old_jobs:
            logger.info(f"Cleaned up {len(old_jobs)} old jobs")

    async def _register_default_handlers(self) -> None:
        """Register default job handlers."""
        # Import handlers here to avoid circular imports
        from .digest_generator import DigestGenerator
        from .entity_graph_builder import EntityGraphBuilder
        from .memory_optimizer import MemoryOptimizer
        from .retention_manager import RetentionManager

        # Create handler instances
        digest_generator = DigestGenerator()
        entity_graph_builder = EntityGraphBuilder()
        memory_optimizer = MemoryOptimizer()
        retention_manager = RetentionManager()

        # Register handlers
        self.register_job_handler(
            BatchJobType.DAILY_DIGEST, digest_generator.generate_daily_digest)
        self.register_job_handler(
            BatchJobType.WEEKLY_DIGEST, digest_generator.generate_weekly_digest)
        self.register_job_handler(
            BatchJobType.ENTITY_GRAPH_BUILD, entity_graph_builder.build_entity_graph)
        self.register_job_handler(
            BatchJobType.MEMORY_OPTIMIZATION, memory_optimizer.optimize_memory)
        self.register_job_handler(
            BatchJobType.DATA_RETENTION, retention_manager.apply_retention_policy)

    async def _setup_default_schedules(self) -> None:
        """Set up default scheduled jobs."""
        # Daily digest at 6 AM
        daily_digest_schedule = ScheduleConfig(
            job_type=BatchJobType.DAILY_DIGEST,
            cron_expression="0 6 * * *",  # 6 AM daily
            name="Daily Digest Generation",
            description="Generate daily summaries for all users",
            timeout_minutes=30
        )
        self.add_schedule(daily_digest_schedule)

        # Weekly digest on Sunday at 8 AM
        weekly_digest_schedule = ScheduleConfig(
            job_type=BatchJobType.WEEKLY_DIGEST,
            cron_expression="0 8 * * 0",  # 8 AM on Sundays
            name="Weekly Digest Generation",
            description="Generate weekly summaries and trends",
            timeout_minutes=60
        )
        self.add_schedule(weekly_digest_schedule)

        # Entity graph building daily at 2 AM
        entity_graph_schedule = ScheduleConfig(
            job_type=BatchJobType.ENTITY_GRAPH_BUILD,
            cron_expression="0 2 * * *",  # 2 AM daily
            name="Entity Graph Building",
            description="Build and update entity relationship graphs",
            timeout_minutes=45
        )
        self.add_schedule(entity_graph_schedule)

        # Memory optimization weekly on Saturday at 3 AM
        memory_optimization_schedule = ScheduleConfig(
            job_type=BatchJobType.MEMORY_OPTIMIZATION,
            cron_expression="0 3 * * 6",  # 3 AM on Saturdays
            name="Memory Optimization",
            description="Optimize memory usage and consolidate data",
            timeout_minutes=120
        )
        self.add_schedule(memory_optimization_schedule)

        # Data retention monthly on 1st at 1 AM
        retention_schedule = ScheduleConfig(
            job_type=BatchJobType.DATA_RETENTION,
            cron_expression="0 1 1 * *",  # 1 AM on 1st of each month
            name="Data Retention Cleanup",
            description="Apply data retention policies and cleanup old data",
            timeout_minutes=180
        )
        self.add_schedule(retention_schedule)

    async def _get_tenants_for_schedule(self, schedule: ScheduleConfig) -> List[str]:
        """Get list of tenant IDs that should be processed for a schedule."""
        try:
            async with get_async_session() as session:
                from sqlalchemy import select

                query = select(Tenant.id)
                if schedule.tenant_filter:
                    query = query.where(Tenant.id.in_(schedule.tenant_filter))

                result = await session.execute(query)
                tenant_ids = [str(row[0]) for row in result.fetchall()]

                return tenant_ids

        except Exception as e:
            logger.error(f"Error getting tenants for schedule: {e}")
            return []

    async def _build_job_parameters(self, schedule: ScheduleConfig, tenant_id: str) -> Dict[str, Any]:
        """Build job parameters based on schedule configuration."""
        parameters = schedule.default_parameters.copy()
        parameters['tenant_id'] = tenant_id

        # Add job-type specific parameters
        if schedule.job_type == BatchJobType.DAILY_DIGEST:
            parameters.update({
                'digest_types': [DigestType.DAILY_PERSONAL, DigestType.DAILY_CONTACT],
                'start_date': (datetime.utcnow() - timedelta(days=1)).isoformat(),
                'end_date': datetime.utcnow().isoformat()
            })
        elif schedule.job_type == BatchJobType.WEEKLY_DIGEST:
            parameters.update({
                'digest_types': [DigestType.WEEKLY_OVERVIEW, DigestType.WEEKLY_TRENDS],
                'start_date': (datetime.utcnow() - timedelta(weeks=1)).isoformat(),
                'end_date': datetime.utcnow().isoformat()
            })
        elif schedule.job_type == BatchJobType.ENTITY_GRAPH_BUILD:
            parameters.update({
                'scope': EntityGraphScope.TENANT,
                'include_relationships': True,
                'min_confidence': 0.6
            })
        elif schedule.job_type == BatchJobType.MEMORY_OPTIMIZATION:
            parameters.update({
                'optimization_types': [
                    MemoryOptimizationType.CONSOLIDATE_SUMMARIES,
                    MemoryOptimizationType.CLEANUP_DUPLICATES
                ]
            })
        elif schedule.job_type == BatchJobType.DATA_RETENTION:
            parameters.update({
                'policies': [
                    RetentionPolicy.MESSAGES_90_DAYS,
                    RetentionPolicy.SUMMARIES_6_MONTHS
                ]
            })

        return parameters

    def get_scheduler_stats(self) -> Dict[str, Any]:
        """Get scheduler statistics."""
        running_jobs = len(self.get_running_jobs())
        pending_jobs = len([j for j in self._jobs.values()
                           if j.status == BatchJobStatus.PENDING])

        return {
            **self.stats,
            'running_jobs': running_jobs,
            'pending_jobs': pending_jobs,
            'total_jobs': len(self._jobs),
            'schedules_configured': len(self._schedules),
            'is_running': self._running
        }
