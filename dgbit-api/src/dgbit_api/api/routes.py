from fastapi import APIRouter

from dgbit_api.core.config import settings
from dgbit_api.domain.jobs import Job, JobType
from dgbit_api.services.job_service import JobService

router = APIRouter(prefix=settings.api_prefix)
job_service = JobService()


@router.get("/health", tags=["system"], summary="Service health")
async def health() -> dict:
    """Basic health and metadata endpoint."""
    return {
        "service": settings.app_name,
        "environment": settings.environment,
        "status": "ok",
    }


@router.post(
    "/backtests",
    tags=["backtests"],
    summary="Schedule a backtest",
)
async def schedule_backtest(payload: dict) -> dict:
    """
    Register a backtest job.
    Later iterations will push commands onto the worker bus.
    """

    job = Job(job_type=JobType.BACKTEST, payload=payload)
    job_service.register(job)
    return {"job_id": str(job.id), "status": job.status}


@router.get(
    "/jobs",
    tags=["jobs"],
    summary="List jobs",
)
async def list_jobs() -> list[dict]:
    """Return all known jobs (temporary in-memory store)."""
    return [
        {
            "id": str(job.id),
            "type": job.job_type,
            "status": job.status,
            "created_at": job.created_at,
            "payload": job.payload,
        }
        for job in job_service.list_jobs()
    ]
