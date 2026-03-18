from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
from tortoise import fields, models
from pydantic import BaseModel


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobType(str, Enum):
    BACKTEST = "backtest"
    DATA_SYNC = "data_sync"
    SIGNAL = "signal"


class Job(models.Model):
    """Job entity for tracking background tasks."""

    id: int = fields.IntField(pk=True, generated=True)
    uuid: str = fields.CharField(max_length=36, unique=True, index=True)
    job_type: str = fields.CharField(max_length=50)
    status: str = fields.CharField(max_length=20, default=JobStatus.PENDING.value)
    payload: str = fields.TextField()  # JSON string
    result: Optional[str] = fields.TextField(null=True)  # JSON string
    error: Optional[str] = fields.TextField(null=True)
    created_at: datetime = fields.DatetimeField(auto_now_add=True)
    updated_at: datetime = fields.DatetimeField(auto_now=True)
    started_at: Optional[datetime] = fields.DatetimeField(null=True)
    completed_at: Optional[datetime] = fields.DatetimeField(null=True)

    class Meta:
        table = "jobs"
        ordering = ["-created_at"]

    def mark_running(self) -> None:
        self.status = JobStatus.RUNNING.value
        self.started_at = datetime.utcnow()

    def mark_complete(self, result: Dict[str, Any]) -> None:
        self.status = JobStatus.COMPLETED.value
        self.result = str(result)
        self.completed_at = datetime.utcnow()

    def mark_failed(self, reason: str) -> None:
        self.status = JobStatus.FAILED.value
        self.error = reason
        self.completed_at = datetime.utcnow()


# Pydantic schemas for API
class JobCreateSchema(BaseModel):
    job_type: JobType
    payload: Dict[str, Any]


class JobResponseSchema(BaseModel):
    id: int
    uuid: str
    job_type: str
    status: str
    payload: Dict[str, Any]
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class BacktestPayloadSchema(BaseModel):
    symbol: str = "BTCUSDT"
    interval: str = "1"
    limit: int = 1000
    initial_capital: float = 10000.0
    transaction_fee: float = 0.001


class BacktestResponseSchema(BaseModel):
    job_uuid: str
    symbol: str
    metrics: Dict[str, Any]
    results: list[Dict[str, Any]]
