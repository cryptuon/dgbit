"""
Job Queue Service - PUSH/PULL for distributed job processing

Provides work distribution across multiple workers with:
- Priority queuing
- Retry logic
- Dead letter queue
- Job status tracking
"""

import asyncio
import json
import logging
import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

# Add parent to path
SRC_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(SRC_DIR))

import pynng
from loguru import logger

from dgbit_services import (
    JobMessage, JobStatus, Event, EventType,
    ServiceBase, ServiceType, ServiceRegistry
)


@dataclass
class Job:
    """Represents a job in the system."""
    job_id: str
    job_type: str
    payload: Dict[str, Any]
    status: JobStatus = JobStatus.PENDING
    priority: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    worker_id: Optional[str] = None
    progress: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_job_message(self) -> JobMessage:
        return JobMessage(
            job_id=self.job_id,
            job_type=self.job_type,
            payload=self.payload,
            priority=self.priority,
            retry_count=self.retry_count,
            max_retries=self.max_retries,
        )


class JobStore:
    """In-memory job storage (replace with database in production)."""

    def __init__(self):
        self._jobs: Dict[str, Job] = {}
        self._by_status: Dict[JobStatus, List[str]] = {
            status: [] for status in JobStatus
        }
        self._by_type: Dict[str, List[str]] = {}

    def create(self, job: Job) -> Job:
        """Create a new job."""
        self._jobs[job.job_id] = job
        self._by_status[job.status].append(job.job_id)
        if job.job_type not in self._by_type:
            self._by_type[job.job_type] = []
        self._by_type[job.job_type].append(job.job_id)
        return job

    def get(self, job_id: str) -> Optional[Job]:
        """Get a job by ID."""
        return self._jobs.get(job_id)

    def update(self, job: Job) -> Job:
        """Update a job."""
        old_status = self._jobs[job.job_id].status
        if old_status != job.status:
            if job.job_id in self._by_status[old_status]:
                self._by_status[old_status].remove(job.job_id)
            self._by_status[job.status].append(job.job_id)
        self._jobs[job.job_id] = job
        return job

    def list_by_status(self, status: JobStatus) -> List[Job]:
        """List jobs by status."""
        return [self._jobs[jid] for jid in self._by_status[status]]

    def list_by_type(self, job_type: str) -> List[Job]:
        """List jobs by type."""
        return [self._jobs[jid] for jid in self._by_type.get(job_type, [])]

    def list_all(self, limit: int = 100) -> List[Job]:
        """List all jobs."""
        return list(self._jobs.values())[:limit]

    def count(self, status: Optional[JobStatus] = None) -> int:
        """Count jobs."""
        if status:
            return len(self._by_status[status])
        return len(self._jobs)


class JobQueue:
    """
    Job queue with PUSH/PULL for distributed workers.

    Usage:
        # Publisher (API)
        queue = JobQueue()
        queue.publish(job_message)

        # Worker
        worker = JobWorker("worker1")
        worker.register_handler("backtest", backtest_handler)
        worker.start()
    """

    PUSH_ADDRESS = "ipc:///tmp/dgbit_queue.ipc"
    RESULTS_ADDRESS = "ipc:///tmp/dgbit_results.ipc"

    def __init__(
        self,
        push_address: str = None,
        results_address: str = None,
    ):
        self.push_address = push_address or self.PUSH_ADDRESS
        self.results_address = results_address or self.RESULTS_ADDRESS
        self._push_socket = None
        self._store = JobStore()
        self._event_bus = None

    def _ensure_push_socket(self):
        """Ensure push socket is connected."""
        if self._push_socket is None:
            self._push_socket = pynng.Push0(dial=self.push_address)
            logger.info(f"Job queue publisher connected to {self.push_address}")

    def set_event_bus(self, event_bus):
        """Set event bus for publishing events."""
        self._event_bus = event_bus

    def _publish_event(self, event_type: str, data: Dict[str, Any]):
        """Publish event if event bus is set."""
        if self._event_bus:
            self._event_bus.publish_sync(event_type, data, source="job_queue")

    def create_job(
        self,
        job_type: str,
        payload: Dict[str, Any],
        priority: int = 0,
        max_retries: int = 3,
        metadata: Dict[str, Any] = None,
    ) -> Job:
        """Create and enqueue a job."""
        job_id = str(uuid.uuid4())

        job = Job(
            job_id=job_id,
            job_type=job_type,
            payload=payload,
            priority=priority,
            max_retries=max_retries,
            metadata=metadata or {},
        )

        self._store.create(job)
        self._publish_event(EventType.JOB_CREATED.value, {
            "job_id": job_id,
            "job_type": job_type,
            "priority": priority,
        })

        return job

    def enqueue(self, job_id: str) -> bool:
        """Enqueue a pending job."""
        job = self._store.get(job_id)
        if not job:
            return False

        self._ensure_push_socket()

        job.status = JobStatus.QUEUED
        self._store.update(job)

        try:
            self._push_socket.send(job.to_job_message().to_bytes())
            self._publish_event(EventType.JOB_QUEUED.value, {"job_id": job_id})
            logger.info(f"Enqueued job {job_id}")
            return True
        except Exception as e:
            job.status = JobStatus.PENDING
            self._store.update(job)
            logger.error(f"Failed to enqueue job {job_id}: {e}")
            return False

    def publish(self, job_message: JobMessage) -> None:
        """Publish a job message directly."""
        self._ensure_push_socket()
        self._push_socket.send(job_message.to_bytes())

    def get_job(self, job_id: str) -> Optional[Job]:
        """Get a job by ID."""
        return self._store.get(job_id)

    def update_job(self, job: Job) -> Job:
        """Update a job and publish events."""
        old_status = self._store.get(job.job_id).status if self._store.get(job.job_id) else None

        job = self._store.update(job)

        # Publish status change events
        if old_status and old_status != job.status:
            if job.status == JobStatus.RUNNING:
                self._publish_event(EventType.JOB_STARTED.value, {"job_id": job.job_id})
            elif job.status == JobStatus.COMPLETED:
                self._publish_event(EventType.JOB_COMPLETED.value, {"job_id": job.job_id})
            elif job.status == JobStatus.FAILED:
                self._publish_event(EventType.JOB_FAILED.value, {
                    "job_id": job.job_id,
                    "error": job.error,
                })

        return job

    def mark_running(self, job_id: str, worker_id: str) -> Optional[Job]:
        """Mark a job as running."""
        job = self._store.get(job_id)
        if job:
            job.status = JobStatus.RUNNING
            job.started_at = datetime.utcnow()
            job.worker_id = worker_id
            return self.update_job(job)
        return None

    def mark_completed(self, job_id: str, result: Any) -> Optional[Job]:
        """Mark a job as completed."""
        job = self._store.get(job_id)
        if job:
            job.status = JobStatus.COMPLETED
            job.completed_at = datetime.utcnow()
            job.result = result
            return self.update_job(job)
        return None

    def mark_failed(self, job_id: str, error: str) -> Optional[Job]:
        """Mark a job as failed."""
        job = self._store.get(job_id)
        if job:
            job.status = JobStatus.FAILED
            job.completed_at = datetime.utcnow()
            job.error = error

            # Retry if allowed
            if job.retry_count < job.max_retries:
                job.retry_count += 1
                job.status = JobStatus.PENDING
                logger.info(f"Retrying job {job_id} ({job.retry_count}/{job.max_retries})")
            else:
                job.status = JobStatus.FAILED

            return self.update_job(job)
        return None

    def cancel(self, job_id: str) -> Optional[Job]:
        """Cancel a job."""
        job = self._store.get(job_id)
        if job and job.status in [JobStatus.PENDING, JobStatus.QUEUED]:
            job.status = JobStatus.CANCELLED
            job.completed_at = datetime.utcnow()
            self._publish_event(EventType.JOB_CANCELLED.value, {"job_id": job_id})
            return self.update_job(job)
        return None

    def get_stats(self) -> Dict[str, Any]:
        """Get queue statistics."""
        return {
            "total": self._store.count(),
            "pending": self._store.count(JobStatus.PENDING),
            "queued": self._store.count(JobStatus.QUEUED),
            "running": self._store.count(JobStatus.RUNNING),
            "completed": self._store.count(JobStatus.COMPLETED),
            "failed": self._store.count(JobStatus.FAILED),
        }

    def list_jobs(
        self,
        status: Optional[JobStatus] = None,
        job_type: Optional[str] = None,
        limit: int = 50,
    ) -> List[Job]:
        """List jobs with filters."""
        if status:
            jobs = self._store.list_by_status(status)
        elif job_type:
            jobs = self._store.list_by_type(job_type)
        else:
            jobs = self._store.list_all(limit)
        return jobs[:limit]

    def close(self):
        """Close connections."""
        if self._push_socket:
            self._push_socket.close()
            self._push_socket = None


class JobWorker:
    """
    Worker that pulls jobs from the queue.

    Usage:
        worker = JobWorker("backtest_worker")

        @worker.handler("backtest")
        async def handle_backtest(job: JobMessage):
            # Do work
            return {"result": "success"}

        worker.start()
    """

    PULL_ADDRESS = "ipc:///tmp/dgbit_queue.ipc"

    def __init__(
        self,
        worker_id: str,
        pull_address: str = None,
    ):
        self.worker_id = worker_id
        self.pull_address = pull_address or self.PULL_ADDRESS
        self._socket = None
        self._running = False
        self._handlers: Dict[str, Callable] = {}
        self._job_queue = None

    def set_job_queue(self, job_queue: JobQueue):
        """Set the job queue for status updates."""
        self._job_queue = job_queue

    def handler(self, job_type: str):
        """Decorator to register a job handler."""
        def decorator(func):
            self.register_handler(job_type, func)
            return func
        return decorator

    def register_handler(self, job_type: str, handler: Callable):
        """Register a handler for a job type."""
        self._handlers[job_type] = handler
        logger.info(f"Registered handler for {job_type}")

    async def _process_job(self, job_message: JobMessage) -> Any:
        """Process a single job."""
        handler = self._handlers.get(job_message.job_type)

        if not handler:
            raise ValueError(f"No handler for job type: {job_message.job_type}")

        # Mark job as running
        if self._job_queue:
            self._job_queue.mark_running(job_message.job_id, self.worker_id)

        # Call handler
        if asyncio.iscoroutinefunction(handler):
            result = await handler(job_message)
        else:
            result = handler(job_message)

        return result

    async def listen(self):
        """Listen for jobs (blocking)."""
        import pynng

        self._socket = pynng.Pull0(listen=self.pull_address)
        logger.info(f"Job worker {self.worker_id} listening on {self.pull_address}")

        while self._running:
            try:
                def _recv():
                    return self._socket.recv()

                loop = asyncio.get_event_loop()
                message = await loop.run_in_executor(None, _recv)
                job_message = JobMessage.from_bytes(message)

                logger.info(f"Received job {job_message.job_id} ({job_message.job_type})")

                try:
                    result = await self._process_job(job_message)

                    if self._job_queue:
                        self._job_queue.mark_completed(job_message.job_id, result)

                    logger.info(f"Job {job_message.job_id} completed")

                except Exception as e:
                    logger.error(f"Job {job_message.job_id} failed: {e}")

                    if self._job_queue:
                        self._job_queue.mark_failed(job_message.job_id, str(e))

            except pynng.Timeout:
                await asyncio.sleep(0.01)
            except Exception as e:
                logger.error(f"Worker error: {e}")

    def start(self):
        """Start the worker in background."""
        self._running = True
        asyncio.create_task(self.listen())
        logger.info(f"Worker {self.worker_id} started")

    def stop(self):
        """Stop the worker."""
        self._running = False
        if self._socket:
            self._socket.close()
            self._socket = None
        logger.info(f"Worker {self.worker_id} stopped")


# =============================================================================
# Job Queue Service (Coordinator)
# =============================================================================

class JobQueueService(ServiceBase):
    """
    Standalone job queue service that manages:
    - Job creation and enqueueing
    - Job status tracking
    - Statistics
    """

    def __init__(
        self,
        name: str = "job_queue",
        queue_address: str = "ipc:///tmp/dgbit_queue.ipc",
    ):
        super().__init__(
            name=name,
            service_type=ServiceType.JOB,
            addresses={"queue": queue_address}
        )

        self._queue = JobQueue(push_address=queue_address)
        self._running = False

    async def start(self):
        """Start the job queue service."""
        from dgbit_services import ServiceRegistry, Event, EventType

        self._running = True

        # Register in service registry
        registry = ServiceRegistry()
        registry.register(self)

        # Publish startup event
        from dgbit_services.events import EventBus
        bus = EventBus()
        bus.publish_sync(EventType.SERVICE_STARTED.value, {
            "service": self.name,
            "address": self.addresses["queue"],
        }, source=self.name)

        logger.info(f"Job queue service started on {self.addresses['queue']}")

    async def stop(self):
        """Stop the job queue service."""
        from dgbit_services import ServiceRegistry, Event, EventType

        self._running = False

        # Unregister
        registry = ServiceRegistry()
        registry.unregister(self.name, self.service_type)

        self._queue.close()
        logger.info("Job queue service stopped")

    async def handle_command(self, message) -> Dict[str, Any]:
        """Handle admin commands."""
        from dgbit_services import JobStatus

        command = message.command
        payload = message.payload

        if command == "create_job":
            job = self._queue.create_job(
                job_type=payload["job_type"],
                payload=payload["payload"],
                priority=payload.get("priority", 0),
                max_retries=payload.get("max_retries", 3),
            )
            self._queue.enqueue(job.job_id)
            return {"job_id": job.job_id, "status": job.status.value}

        elif command == "get_job":
            job = self._queue.get_job(payload["job_id"])
            if job:
                return {"job": {
                    "job_id": job.job_id,
                    "job_type": job.job_type,
                    "status": job.status.value,
                    "created_at": job.created_at.isoformat(),
                }}
            return {"error": "Job not found"}

        elif command == "list_jobs":
            status = JobStatus(payload["status"]) if payload.get("status") else None
            jobs = self._queue.list_jobs(status=status, limit=payload.get("limit", 50))
            return {"jobs": [
                {"job_id": j.job_id, "job_type": j.job_type, "status": j.status.value}
                for j in jobs
            ]}

        elif command == "cancel_job":
            job = self._queue.cancel(payload["job_id"])
            return {"success": job is not None}

        elif command == "stats":
            return self._queue.get_stats()

        elif command == "ping":
            return {"status": "ok"}

        else:
            return {"error": f"Unknown command: {command}"}


# =============================================================================
# Run as Service
# =============================================================================

async def run_job_queue_service():
    """Run the job queue service as a standalone process."""
    import argparse

    parser = argparse.ArgumentParser(description="dgbit Job Queue Service")
    parser.add_argument("--address", default="ipc:///tmp/dgbit_queue.ipc")
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()

    # Setup logging
    logger.remove()
    logger.add(sys.stdout, level=args.log_level)

    # Create and run service
    service = JobQueueService(queue_address=args.address)

    try:
        await service.start()
    except KeyboardInterrupt:
        await service.stop()


if __name__ == "__main__":
    asyncio.run(run_job_queue_service())
