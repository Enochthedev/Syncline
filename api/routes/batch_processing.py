"""
API routes for batch processing management.

Provides endpoints for:
- Job scheduling and management
- Digest generation requests
- Entity graph building
- Memory optimization
- Data retention policies
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, Field

from config.config import settings
from api.dependencies import get_current_user
from services.batch_processing import BatchScheduler
from services.batch_processing.types import (
    BatchJob,
    BatchJobType,
    BatchJobStatus,
    DigestType,
    EntityGraphScope,
    MemoryOptimizationType,
    RetentionPolicy,
    ScheduleConfig
)

router = APIRouter(prefix="/batch", tags=["batch_processing"])

# Global batch scheduler instance
batch_scheduler: Optional[BatchScheduler] = None


async def get_batch_scheduler() -> BatchScheduler:
    """Get the global batch scheduler instance."""
    global batch_scheduler
    if batch_scheduler is None:
        batch_scheduler = BatchScheduler()
        await batch_scheduler.start()
    return batch_scheduler


# Request/Response Models
class JobScheduleRequest(BaseModel):
    """Request to schedule a batch job."""
    job_type: BatchJobType
    tenant_id: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    scheduled_at: Optional[datetime] = None
    max_retries: int = 3


class JobStatusResponse(BaseModel):
    """Response with job status information."""
    job_id: str
    job_type: BatchJobType
    status: BatchJobStatus
    progress: float
    scheduled_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    error_message: Optional[str]
    result_summary: Optional[str]


class DigestGenerationRequest(BaseModel):
    """Request for digest generation."""
    digest_types: List[DigestType]
    tenant_id: str
    user_id: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    schedule_immediately: bool = True


class EntityGraphRequest(BaseModel):
    """Request for entity graph building."""
    scope: EntityGraphScope
    tenant_id: str
    scope_id: Optional[str] = None
    include_relationships: bool = True
    min_confidence: float = 0.5
    schedule_immediately: bool = True


class MemoryOptimizationRequest(BaseModel):
    """Request for memory optimization."""
    optimization_types: List[MemoryOptimizationType]
    tenant_id: str
    dry_run: bool = False
    backup_before: bool = True
    schedule_immediately: bool = True


class RetentionPolicyRequest(BaseModel):
    """Request for retention policy application."""
    policies: List[RetentionPolicy]
    tenant_id: str
    dry_run: bool = True
    backup_before: bool = True
    force_delete: bool = False
    schedule_immediately: bool = True


class SchedulerStatsResponse(BaseModel):
    """Response with scheduler statistics."""
    is_running: bool
    jobs_scheduled: int
    jobs_completed: int
    jobs_failed: int
    running_jobs: int
    pending_jobs: int
    total_jobs: int
    schedules_configured: int
    total_runtime_seconds: float
    last_schedule_check: Optional[datetime]


# Job Management Endpoints
@router.post("/jobs/schedule", response_model=Dict[str, str])
async def schedule_job(
    request: JobScheduleRequest,
    scheduler: BatchScheduler = Depends(get_batch_scheduler),
    current_user: Dict = Depends(get_current_user)
):
    """Schedule a batch processing job."""
    try:
        job = BatchJob(
            type=request.job_type,
            tenant_id=request.tenant_id,
            parameters=request.parameters,
            scheduled_at=request.scheduled_at or datetime.utcnow(),
            max_retries=request.max_retries
        )

        job_id = await scheduler.schedule_job(job)

        return {"job_id": job_id, "message": "Job scheduled successfully"}

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to schedule job: {str(e)}")


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(
    job_id: str,
    scheduler: BatchScheduler = Depends(get_batch_scheduler),
    current_user: Dict = Depends(get_current_user)
):
    """Get the status of a specific job."""
    job = scheduler.get_job_status(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return JobStatusResponse(
        job_id=job.id,
        job_type=job.type,
        status=job.status,
        progress=job.progress,
        scheduled_at=job.scheduled_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        error_message=job.error_message,
        result_summary=job.result_data.get(
            'summary') if job.result_data else None
    )


@router.delete("/jobs/{job_id}")
async def cancel_job(
    job_id: str,
    scheduler: BatchScheduler = Depends(get_batch_scheduler),
    current_user: Dict = Depends(get_current_user)
):
    """Cancel a scheduled or running job."""
    success = await scheduler.cancel_job(job_id)

    if not success:
        raise HTTPException(status_code=400, detail="Job cannot be cancelled")

    return {"message": "Job cancelled successfully"}


@router.get("/jobs", response_model=List[JobStatusResponse])
async def list_jobs(
    job_type: Optional[BatchJobType] = None,
    status: Optional[BatchJobStatus] = None,
    limit: int = 50,
    scheduler: BatchScheduler = Depends(get_batch_scheduler),
    current_user: Dict = Depends(get_current_user)
):
    """List batch processing jobs with optional filtering."""
    jobs = list(scheduler._jobs.values())

    # Apply filters
    if job_type:
        jobs = [job for job in jobs if job.type == job_type]

    if status:
        jobs = [job for job in jobs if job.status == status]

    # Sort by scheduled time (newest first)
    jobs.sort(key=lambda j: j.scheduled_at, reverse=True)

    # Apply limit
    jobs = jobs[:limit]

    return [
        JobStatusResponse(
            job_id=job.id,
            job_type=job.type,
            status=job.status,
            progress=job.progress,
            scheduled_at=job.scheduled_at,
            started_at=job.started_at,
            completed_at=job.completed_at,
            error_message=job.error_message,
            result_summary=job.result_data.get(
                'summary') if job.result_data else None
        )
        for job in jobs
    ]


# Digest Generation Endpoints
@router.post("/digests/generate")
async def generate_digest(
    request: DigestGenerationRequest,
    background_tasks: BackgroundTasks,
    scheduler: BatchScheduler = Depends(get_batch_scheduler),
    current_user: Dict = Depends(get_current_user)
):
    """Generate digest summaries."""
    try:
        # Determine job type based on digest types
        job_type = BatchJobType.DAILY_DIGEST
        if any(dt.value.startswith('weekly') for dt in request.digest_types):
            job_type = BatchJobType.WEEKLY_DIGEST

        # Set default date range if not provided
        end_date = request.end_date or datetime.utcnow()
        if job_type == BatchJobType.DAILY_DIGEST:
            start_date = request.start_date or (end_date - timedelta(days=1))
        else:
            start_date = request.start_date or (end_date - timedelta(weeks=1))

        job = BatchJob(
            type=job_type,
            tenant_id=request.tenant_id,
            parameters={
                'digest_types': [dt.value for dt in request.digest_types],
                'user_id': request.user_id,
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat()
            },
            scheduled_at=datetime.utcnow() if request.schedule_immediately else None
        )

        job_id = await scheduler.schedule_job(job)

        return {
            "job_id": job_id,
            "message": "Digest generation scheduled",
            "digest_types": [dt.value for dt in request.digest_types],
            "date_range": f"{start_date.date()} to {end_date.date()}"
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to schedule digest generation: {str(e)}")


# Entity Graph Endpoints
@router.post("/entity-graph/build")
async def build_entity_graph(
    request: EntityGraphRequest,
    scheduler: BatchScheduler = Depends(get_batch_scheduler),
    current_user: Dict = Depends(get_current_user)
):
    """Build entity relationship graph."""
    try:
        job = BatchJob(
            type=BatchJobType.ENTITY_GRAPH_BUILD,
            tenant_id=request.tenant_id,
            parameters={
                'scope': request.scope.value,
                'scope_id': request.scope_id,
                'include_relationships': request.include_relationships,
                'min_confidence': request.min_confidence,
                'detect_communities': True,
                'calculate_centrality': True,
                'find_key_entities': True
            },
            scheduled_at=datetime.utcnow() if request.schedule_immediately else None
        )

        job_id = await scheduler.schedule_job(job)

        return {
            "job_id": job_id,
            "message": "Entity graph building scheduled",
            "scope": request.scope.value,
            "scope_id": request.scope_id
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to schedule entity graph building: {str(e)}")


# Memory Optimization Endpoints
@router.post("/memory/optimize")
async def optimize_memory(
    request: MemoryOptimizationRequest,
    scheduler: BatchScheduler = Depends(get_batch_scheduler),
    current_user: Dict = Depends(get_current_user)
):
    """Optimize memory usage and storage."""
    try:
        job = BatchJob(
            type=BatchJobType.MEMORY_OPTIMIZATION,
            tenant_id=request.tenant_id,
            parameters={
                'optimization_types': [ot.value for ot in request.optimization_types],
                'dry_run': request.dry_run,
                'backup_before': request.backup_before
            },
            scheduled_at=datetime.utcnow() if request.schedule_immediately else None
        )

        job_id = await scheduler.schedule_job(job)

        return {
            "job_id": job_id,
            "message": "Memory optimization scheduled",
            "optimization_types": [ot.value for ot in request.optimization_types],
            "dry_run": request.dry_run
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to schedule memory optimization: {str(e)}")


# Data Retention Endpoints
@router.post("/retention/apply")
async def apply_retention_policies(
    request: RetentionPolicyRequest,
    scheduler: BatchScheduler = Depends(get_batch_scheduler),
    current_user: Dict = Depends(get_current_user)
):
    """Apply data retention policies."""
    try:
        job = BatchJob(
            type=BatchJobType.DATA_RETENTION,
            tenant_id=request.tenant_id,
            parameters={
                'policies': [p.value for p in request.policies],
                'dry_run': request.dry_run,
                'backup_before': request.backup_before,
                'force_delete': request.force_delete
            },
            scheduled_at=datetime.utcnow() if request.schedule_immediately else None
        )

        job_id = await scheduler.schedule_job(job)

        return {
            "job_id": job_id,
            "message": "Retention policy application scheduled",
            "policies": [p.value for p in request.policies],
            "dry_run": request.dry_run
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to schedule retention policy application: {str(e)}")


# Scheduler Management Endpoints
@router.get("/scheduler/stats", response_model=SchedulerStatsResponse)
async def get_scheduler_stats(
    scheduler: BatchScheduler = Depends(get_batch_scheduler),
    current_user: Dict = Depends(get_current_user)
):
    """Get batch scheduler statistics."""
    stats = scheduler.get_scheduler_stats()

    return SchedulerStatsResponse(**stats)


@router.post("/scheduler/start")
async def start_scheduler(
    scheduler: BatchScheduler = Depends(get_batch_scheduler),
    current_user: Dict = Depends(get_current_user)
):
    """Start the batch scheduler."""
    try:
        await scheduler.start()
        return {"message": "Batch scheduler started"}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to start scheduler: {str(e)}")


@router.post("/scheduler/stop")
async def stop_scheduler(
    scheduler: BatchScheduler = Depends(get_batch_scheduler),
    current_user: Dict = Depends(get_current_user)
):
    """Stop the batch scheduler."""
    try:
        await scheduler.stop()
        return {"message": "Batch scheduler stopped"}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to stop scheduler: {str(e)}")


# Utility Endpoints
@router.get("/job-types")
async def get_job_types():
    """Get available batch job types."""
    return {
        "job_types": [
            {
                "type": job_type.value,
                "description": _get_job_type_description(job_type)
            }
            for job_type in BatchJobType
        ]
    }


@router.get("/digest-types")
async def get_digest_types():
    """Get available digest types."""
    return {
        "digest_types": [
            {
                "type": digest_type.value,
                "description": _get_digest_type_description(digest_type)
            }
            for digest_type in DigestType
        ]
    }


@router.get("/retention-policies")
async def get_retention_policies():
    """Get available retention policies."""
    from services.batch_processing.retention_manager import RetentionManager

    retention_manager = RetentionManager()

    return {
        "retention_policies": [
            retention_manager.get_retention_policy_info(policy)
            for policy in RetentionPolicy
        ]
    }


# Helper functions
def _get_job_type_description(job_type: BatchJobType) -> str:
    """Get description for a job type."""
    descriptions = {
        BatchJobType.DAILY_DIGEST: "Generate daily summary digests",
        BatchJobType.WEEKLY_DIGEST: "Generate weekly summary digests",
        BatchJobType.ENTITY_GRAPH_BUILD: "Build entity relationship graphs",
        BatchJobType.MEMORY_OPTIMIZATION: "Optimize memory usage and storage",
        BatchJobType.DATA_RETENTION: "Apply data retention policies",
        BatchJobType.SUMMARY_CLEANUP: "Clean up old summaries",
        BatchJobType.VECTOR_REINDEX: "Reindex vector embeddings"
    }
    return descriptions.get(job_type, "Unknown job type")


def _get_digest_type_description(digest_type: DigestType) -> str:
    """Get description for a digest type."""
    descriptions = {
        DigestType.DAILY_PERSONAL: "Personal daily activity summary",
        DigestType.DAILY_CONTACT: "Daily summaries per contact",
        DigestType.DAILY_THREAD: "Daily summaries per conversation thread",
        DigestType.WEEKLY_OVERVIEW: "Weekly activity overview",
        DigestType.WEEKLY_TRENDS: "Weekly trends and patterns analysis",
        DigestType.WEEKLY_RELATIONSHIPS: "Weekly relationship insights"
    }
    return descriptions.get(digest_type, "Unknown digest type")
