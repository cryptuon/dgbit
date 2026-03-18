import json
from datetime import datetime
from typing import Optional, List, Dict, Any

from loguru import logger
from tortoise.expressions import Q

from dgbit_api.db.models import Job, JobStatus, JobType


class JobService:
    """Async service for managing jobs with TortoiseORM."""

    @staticmethod
    async def create(job_type: JobType, payload: Dict[str, Any]) -> Job:
        """Create a new job."""
        import uuid
        job = Job(
            uuid=str(uuid.uuid4()),
            job_type=job_type.value,
            payload=json.dumps(payload),
        )
        await job.save()
        logger.info(f"Created job {job.uuid} of type {job_type.value}")
        return job

    @staticmethod
    async def get_by_uuid(uuid: str) -> Optional[Job]:
        """Get a job by UUID."""
        return await Job.get_or_none(uuid=uuid)

    @staticmethod
    async def get_by_id(job_id: int) -> Optional[Job]:
        """Get a job by ID."""
        return await Job.get_or_none(id=job_id)

    @staticmethod
    async def list_jobs(
        status: Optional[JobStatus] = None,
        job_type: Optional[JobType] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Job]:
        """List jobs with optional filters."""
        query = Q()
        if status:
            query &= Q(status=status.value)
        if job_type:
            query &= Q(job_type=job_type.value)

        return await Job.filter(query).limit(limit).offset(offset).order_by("-created_at")

    @staticmethod
    async def list_all(limit: int = 100) -> List[Job]:
        """List all jobs."""
        return await Job.all().limit(limit).order_by("-created_at")

    @staticmethod
    async def mark_running(job_uuid: str) -> Optional[Job]:
        """Mark a job as running."""
        job = await JobService.get_by_uuid(job_uuid)
        if job:
            job.mark_running()
            await job.save()
            logger.info(f"Job {job_uuid} marked as running")
        return job

    @staticmethod
    async def mark_complete(job_uuid: str, result: Dict[str, Any]) -> Optional[Job]:
        """Mark a job as completed with results."""
        job = await JobService.get_by_uuid(job_uuid)
        if job:
            job.mark_complete(result)
            await job.save()
            logger.info(f"Job {job_uuid} marked as completed")
        return job

    @staticmethod
    async def mark_failed(job_uuid: str, reason: str) -> Optional[Job]:
        """Mark a job as failed with error message."""
        job = await JobService.get_by_uuid(job_uuid)
        if job:
            job.mark_failed(reason)
            await job.save()
            logger.error(f"Job {job_uuid} marked as failed: {reason}")
        return job

    @staticmethod
    async def pending_jobs() -> List[Job]:
        """Get all pending jobs."""
        return await Job.filter(status=JobStatus.PENDING.value).order_by("created_at")

    @staticmethod
    async def running_jobs() -> List[Job]:
        """Get all running jobs."""
        return await Job.filter(status=JobStatus.RUNNING.value)

    @staticmethod
    async def get_stats() -> Dict[str, Any]:
        """Get job statistics."""
        total = await Job.all().count()
        pending = await Job.filter(status=JobStatus.PENDING.value).count()
        running = await Job.filter(status=JobStatus.RUNNING.value).count()
        completed = await Job.filter(status=JobStatus.COMPLETED.value).count()
        failed = await Job.filter(status=JobStatus.FAILED.value).count()

        return {
            "total": total,
            "pending": pending,
            "running": running,
            "completed": completed,
            "failed": failed,
        }
