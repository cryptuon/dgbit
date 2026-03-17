from typing import Dict, Iterable

from dgbit_api.domain.jobs import Job, JobStatus


class JobService:
    """Temporary in-memory job registry until persistence is wired."""

    def __init__(self) -> None:
        self._jobs: Dict[str, Job] = {}

    def register(self, job: Job) -> Job:
        self._jobs[str(job.id)] = job
        return job

    def list_jobs(self) -> Iterable[Job]:
        return self._jobs.values()

    def get_job(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)

    def mark_running(self, job_id: str) -> None:
        job = self._jobs[job_id]
        job.mark_running()

    def mark_complete(self, job_id: str) -> None:
        job = self._jobs[job_id]
        job.mark_complete()

    def mark_failed(self, job_id: str, reason: str) -> None:
        job = self._jobs[job_id]
        job.mark_failed(reason)

    def pending_jobs(self) -> list[Job]:
        return [job for job in self._jobs.values() if job.status == JobStatus.PENDING]
