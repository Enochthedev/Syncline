"""
Collection Orchestrator Service

Manages message collection jobs across all platform connections with:
- Job scheduling and prioritization
- Progress monitoring and tracking
- Concurrent collection management
- Error handling and retry logic
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.collection_job import CollectionJob, JobType, JobStatus
from db.models.platform_connection import PlatformConnection, ConnectionStatus
from services.event_bus import EventBus, get_event_bus
from services.events.types import Event, EventType


logger = logging.getLogger(__name__)


class CollectionOrchestrator:
    """
    Orchestrates message collection across all platform connections.
    
    Features:
    - Job scheduling with priority queue
    - Concurrent collection management
    - Progress monitoring and tracking
    - Automatic retry on failures
    - Event-driven architecture
    """
    
    def __init__(
        self,
        db: AsyncSession,
        event_bus: Optional[EventBus] = None,
        max_concurrent_jobs: int = 5,
        job_timeout_minutes: int = 60,
    ):
        """
        Initialize collection orchestrator.
        
        Args:
            db: Database session
            event_bus: Event bus for publishing events
            max_concurrent_jobs: Maximum concurrent collection jobs
            job_timeout_minutes: Job timeout in minutes
        """
        self.db = db
        self.event_bus = event_bus or get_event_bus()
        self.max_concurrent_jobs = max_concurrent_jobs
        self.job_timeout = timedelta(minutes=job_timeout_minutes)
        
        # Active jobs tracking
        self._active_jobs: Dict[UUID, asyncio.Task] = {}
        self._job_semaphore = asyncio.Semaphore(max_concurrent_jobs)
        
        # Running state
        self._running = False
        self._monitor_task: Optional[asyncio.Task] = None
    
    async def start(self) -> None:
        """Start the collection orchestrator."""
        if self._running:
            logger.warning("Collection orchestrator already running")
            return
        
        self._running = True
        
        # Start monitoring task
        self._monitor_task = asyncio.create_task(self._monitor_jobs())
        
        logger.info("Collection orchestrator started")
    
    async def stop(self) -> None:
        """Stop the collection orchestrator."""
        if not self._running:
            return
        
        self._running = False
        
        # Cancel monitoring task
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        
        # Cancel all active jobs
        for job_id, task in list(self._active_jobs.items()):
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        self._active_jobs.clear()
        
        logger.info("Collection orchestrator stopped")
    
    async def create_job(
        self,
        connection_id: UUID,
        job_type: JobType,
        priority: int = 0,
    ) -> CollectionJob:
        """
        Create a new collection job.
        
        Args:
            connection_id: Platform connection ID
            job_type: Type of collection job
            priority: Job priority (higher = more important)
        
        Returns:
            Created CollectionJob
        """
        # Create job record
        job = CollectionJob(
            connection_id=connection_id,
            job_type=job_type,
            status=JobStatus.PENDING,
            progress={
                "priority": priority,
                "created_at": datetime.utcnow().isoformat(),
            }
        )
        
        self.db.add(job)
        await self.db.commit()
        await self.db.refresh(job)
        
        logger.info(
            f"Created collection job {job.id} "
            f"(type={job_type}, connection={connection_id})"
        )
        
        # Publish event
        await self.event_bus.publish(
            Event(
                event_type=EventType.COLLECTION_STARTED,
                source="collection_orchestrator",
                payload={
                    "job_id": str(job.id),
                    "connection_id": str(connection_id),
                    "job_type": job_type.value,
                }
            )
        )
        
        return job
    
    async def start_job(self, job_id: UUID) -> None:
        """
        Start a collection job.
        
        Args:
            job_id: Collection job ID
        """
        # Check if already running
        if job_id in self._active_jobs:
            logger.warning(f"Job {job_id} already running")
            return
        
        # Get job from database
        result = await self.db.execute(
            select(CollectionJob).where(CollectionJob.id == job_id)
        )
        job = result.scalar_one_or_none()
        
        if not job:
            logger.error(f"Job {job_id} not found")
            return
        
        # Update job status
        job.status = JobStatus.RUNNING
        if not job.progress:
            job.progress = {}
        job.progress["started_at"] = datetime.utcnow().isoformat()
        await self.db.commit()
        
        # Create task for job execution
        task = asyncio.create_task(self._execute_job(job))
        self._active_jobs[job_id] = task
        
        logger.info(f"Started collection job {job_id}")
    
    async def pause_job(self, job_id: UUID) -> None:
        """
        Pause a running collection job.
        
        Args:
            job_id: Collection job ID
        """
        # Cancel task if running
        if job_id in self._active_jobs:
            task = self._active_jobs[job_id]
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            del self._active_jobs[job_id]
        
        # Update job status
        await self.db.execute(
            update(CollectionJob)
            .where(CollectionJob.id == job_id)
            .values(status=JobStatus.PAUSED)
        )
        await self.db.commit()
        
        logger.info(f"Paused collection job {job_id}")
    
    async def cancel_job(self, job_id: UUID) -> None:
        """
        Cancel a collection job.
        
        Args:
            job_id: Collection job ID
        """
        # Cancel task if running
        if job_id in self._active_jobs:
            task = self._active_jobs[job_id]
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            del self._active_jobs[job_id]
        
        # Update job status
        await self.db.execute(
            update(CollectionJob)
            .where(CollectionJob.id == job_id)
            .values(status=JobStatus.CANCELLED)
        )
        await self.db.commit()
        
        logger.info(f"Cancelled collection job {job_id}")
    
    async def get_job_status(self, job_id: UUID) -> Optional[Dict[str, Any]]:
        """
        Get status of a collection job.
        
        Args:
            job_id: Collection job ID
        
        Returns:
            Job status dictionary or None if not found
        """
        result = await self.db.execute(
            select(CollectionJob).where(CollectionJob.id == job_id)
        )
        job = result.scalar_one_or_none()
        
        if not job:
            return None
        
        return {
            "job_id": str(job.id),
            "connection_id": str(job.connection_id),
            "job_type": job.job_type.value,
            "status": job.status.value,
            "progress": job.progress or {},
            "error_message": job.error_message,
            "created_at": job.created_at.isoformat(),
            "updated_at": job.updated_at.isoformat(),
            "is_active": job_id in self._active_jobs,
        }

    async def get_active_jobs(self) -> List[Dict[str, Any]]:
        """
        Get all active collection jobs.
        
        Returns:
            List of active job status dictionaries
        """
        result = await self.db.execute(
            select(CollectionJob)
            .where(CollectionJob.status.in_([JobStatus.RUNNING, JobStatus.PENDING]))
            .order_by(CollectionJob.created_at.desc())
        )
        jobs = result.scalars().all()
        
        return [
            {
                "job_id": str(job.id),
                "connection_id": str(job.connection_id),
                "job_type": job.job_type.value,
                "status": job.status.value,
                "progress": job.progress or {},
                "created_at": job.created_at.isoformat(),
                "is_active": job.id in self._active_jobs,
            }
            for job in jobs
        ]
    
    async def get_connection_jobs(
        self,
        connection_id: UUID,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get collection jobs for a specific connection.
        
        Args:
            connection_id: Platform connection ID
            limit: Maximum number of jobs to return
        
        Returns:
            List of job status dictionaries
        """
        result = await self.db.execute(
            select(CollectionJob)
            .where(CollectionJob.connection_id == connection_id)
            .order_by(CollectionJob.created_at.desc())
            .limit(limit)
        )
        jobs = result.scalars().all()
        
        return [
            {
                "job_id": str(job.id),
                "connection_id": str(job.connection_id),
                "job_type": job.job_type.value,
                "status": job.status.value,
                "progress": job.progress or {},
                "error_message": job.error_message,
                "created_at": job.created_at.isoformat(),
                "updated_at": job.updated_at.isoformat(),
            }
            for job in jobs
        ]
    
    async def update_job_progress(
        self,
        job_id: UUID,
        progress_update: Dict[str, Any]
    ) -> None:
        """
        Update job progress information.
        
        Args:
            job_id: Collection job ID
            progress_update: Progress data to merge
        """
        result = await self.db.execute(
            select(CollectionJob).where(CollectionJob.id == job_id)
        )
        job = result.scalar_one_or_none()
        
        if not job:
            logger.error(f"Job {job_id} not found for progress update")
            return
        
        # Merge progress data
        if not job.progress:
            job.progress = {}
        job.progress.update(progress_update)
        job.progress["last_updated"] = datetime.utcnow().isoformat()
        
        await self.db.commit()
    
    async def _execute_job(self, job: CollectionJob) -> None:
        """
        Execute a collection job.
        
        Args:
            job: Collection job to execute
        """
        async with self._job_semaphore:
            try:
                logger.info(f"Executing job {job.id} (type={job.job_type})")
                
                # Get platform connection
                result = await self.db.execute(
                    select(PlatformConnection)
                    .where(PlatformConnection.id == job.connection_id)
                )
                connection = result.scalar_one_or_none()
                
                if not connection:
                    raise ValueError(f"Connection {job.connection_id} not found")
                
                if connection.status != ConnectionStatus.ACTIVE:
                    raise ValueError(
                        f"Connection {job.connection_id} is not active "
                        f"(status={connection.status})"
                    )
                
                # Execute based on job type
                if job.job_type == JobType.HISTORICAL:
                    await self._execute_historical_collection(job, connection)
                elif job.job_type == JobType.REALTIME:
                    await self._execute_realtime_collection(job, connection)
                elif job.job_type == JobType.INCREMENTAL:
                    await self._execute_incremental_collection(job, connection)
                else:
                    raise ValueError(f"Unknown job type: {job.job_type}")
                
                # Mark job as completed
                job.status = JobStatus.COMPLETED
                if not job.progress:
                    job.progress = {}
                job.progress["completed_at"] = datetime.utcnow().isoformat()
                await self.db.commit()
                
                # Publish completion event
                await self.event_bus.publish(
                    Event(
                        event_type=EventType.COLLECTION_COMPLETED,
                        source="collection_orchestrator",
                        payload={
                            "job_id": str(job.id),
                            "connection_id": str(job.connection_id),
                            "job_type": job.job_type.value,
                            "progress": job.progress,
                        }
                    )
                )
                
                logger.info(f"Completed job {job.id}")
            
            except asyncio.CancelledError:
                logger.info(f"Job {job.id} cancelled")
                raise
            
            except Exception as e:
                logger.error(f"Job {job.id} failed: {e}", exc_info=True)
                
                # Mark job as failed
                job.status = JobStatus.FAILED
                job.error_message = str(e)[:1000]
                await self.db.commit()
                
                # Publish error event
                await self.event_bus.publish(
                    Event(
                        event_type=EventType.COLLECTION_ERROR,
                        source="collection_orchestrator",
                        payload={
                            "job_id": str(job.id),
                            "connection_id": str(job.connection_id),
                            "error": str(e),
                        }
                    )
                )
            
            finally:
                # Remove from active jobs
                if job.id in self._active_jobs:
                    del self._active_jobs[job.id]
    
    async def _execute_historical_collection(
        self,
        job: CollectionJob,
        connection: PlatformConnection
    ) -> None:
        """
        Execute historical message collection.
        
        Args:
            job: Collection job
            connection: Platform connection
        """
        from services.historical_fetcher import HistoricalFetcher
        from services.platform_fetchers import get_platform_fetcher
        
        logger.info(
            f"Historical collection for {connection.platform} "
            f"(job={job.id})"
        )
        
        try:
            # Get platform-specific fetcher
            fetch_function = get_platform_fetcher(connection.platform)
            
            # Create connector instance (placeholder - will be improved)
            # TODO: Get connector from connector manager
            connector = None  # Placeholder
            
            # Create historical fetcher
            fetcher = HistoricalFetcher(
                db=self.db,
                event_bus=self.event_bus,
            )
            
            # Execute historical fetch
            stats = await fetcher.fetch_historical_messages(
                job=job,
                connection=connection,
                connector=connector,
                fetch_function=fetch_function,
            )
            
            # Update final progress
            await self.update_job_progress(
                job.id,
                {
                    "phase": "historical",
                    "status": "completed",
                    "stats": stats,
                }
            )
            
            logger.info(
                f"Historical collection completed for {connection.platform} "
                f"(job={job.id}): {stats.get('new_messages', 0)} messages"
            )
        
        except Exception as e:
            logger.error(
                f"Historical collection failed for {connection.platform} "
                f"(job={job.id}): {e}",
                exc_info=True
            )
            raise
    
    async def _execute_realtime_collection(
        self,
        job: CollectionJob,
        connection: PlatformConnection
    ) -> None:
        """
        Execute real-time message collection.
        
        Args:
            job: Collection job
            connection: Platform connection
        """
        # TODO: Implement real-time collection logic
        # This will be implemented in task 10 (Real-time message collection)
        logger.info(
            f"Real-time collection for {connection.platform} "
            f"(job={job.id}) - placeholder"
        )
        
        await self.update_job_progress(
            job.id,
            {
                "phase": "realtime",
                "listening": True,
            }
        )
    
    async def _execute_incremental_collection(
        self,
        job: CollectionJob,
        connection: PlatformConnection
    ) -> None:
        """
        Execute incremental message collection.
        
        Args:
            job: Collection job
            connection: Platform connection
        """
        # TODO: Implement incremental collection logic
        logger.info(
            f"Incremental collection for {connection.platform} "
            f"(job={job.id}) - placeholder"
        )
        
        await self.update_job_progress(
            job.id,
            {
                "phase": "incremental",
                "last_sync": connection.last_sync_at.isoformat() if connection.last_sync_at else None,
            }
        )
    
    async def _monitor_jobs(self) -> None:
        """
        Monitor running jobs and handle timeouts.
        
        Runs as a background task to:
        - Check for timed out jobs
        - Schedule pending jobs
        - Clean up completed jobs
        """
        logger.info("Job monitor started")
        
        try:
            while self._running:
                try:
                    # Check for timed out jobs
                    await self._check_timeouts()
                    
                    # Schedule pending jobs
                    await self._schedule_pending_jobs()
                    
                    # Sleep before next check
                    await asyncio.sleep(30)  # Check every 30 seconds
                
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Error in job monitor: {e}", exc_info=True)
                    await asyncio.sleep(5)
        
        finally:
            logger.info("Job monitor stopped")
    
    async def _check_timeouts(self) -> None:
        """Check for and handle timed out jobs."""
        timeout_threshold = datetime.utcnow() - self.job_timeout
        
        result = await self.db.execute(
            select(CollectionJob)
            .where(
                CollectionJob.status == JobStatus.RUNNING,
                CollectionJob.updated_at < timeout_threshold
            )
        )
        timed_out_jobs = result.scalars().all()
        
        for job in timed_out_jobs:
            logger.warning(f"Job {job.id} timed out")
            
            # Cancel if still in active jobs
            if job.id in self._active_jobs:
                task = self._active_jobs[job.id]
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                del self._active_jobs[job.id]
            
            # Mark as failed
            job.status = JobStatus.FAILED
            job.error_message = "Job timed out"
            await self.db.commit()
    
    async def _schedule_pending_jobs(self) -> None:
        """Schedule pending jobs based on priority and capacity."""
        # Check if we have capacity
        if len(self._active_jobs) >= self.max_concurrent_jobs:
            return
        
        # Get pending jobs ordered by priority
        result = await self.db.execute(
            select(CollectionJob)
            .where(CollectionJob.status == JobStatus.PENDING)
            .order_by(CollectionJob.created_at.asc())
            .limit(self.max_concurrent_jobs - len(self._active_jobs))
        )
        pending_jobs = result.scalars().all()
        
        # Start jobs
        for job in pending_jobs:
            await self.start_job(job.id)
