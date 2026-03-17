from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from uuid import UUID, uuid4


class JobType(str, Enum):
    BACKTEST = "backtest"
    DATA_SYNC = "data_sync"
    SIGNAL = "signal"


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(kw_only=True)
class Job:
    """Represents a long-running task executed by a background worker."""

    job_type: JobType
    payload: Dict[str, Any]
    id: UUID = field(default_factory=uuid4)
    status: JobStatus = JobStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    error: Optional[str] = None

    def mark_running(self) -> None:
        self.status = JobStatus.RUNNING
        self.updated_at = datetime.utcnow()

    def mark_complete(self) -> None:
        self.status = JobStatus.COMPLETED
        self.updated_at = datetime.utcnow()

    def mark_failed(self, reason: str) -> None:
        self.status = JobStatus.FAILED
        self.error = reason
        self.updated_at = datetime.utcnow()
