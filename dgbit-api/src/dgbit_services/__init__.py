"""
dgbit Services - Core Service Framework

A comprehensive service bus framework using NNG for inter-process communication.

Architecture:
┌────────────────────────────────────────────────────────────────────────┐
│                           Service Bus                                   │
│                                                                        │
│  ┌──────────────────────────────────────────────────────────────────┐ │
│  │                    Command Channel (REQ/REP)                     │ │
│  │  - Synchronous request/response                                   │ │
│  │  - Used for: API calls, Worker commands                          │ │
│  └──────────────────────────────────────────────────────────────────┘ │
│                                                                        │
│  ┌──────────────────────────────────────────────────────────────────┐ │
│  │                    Event Channel (PUB/SUB)                       │ │
│  │  - Asynchronous event distribution                                │ │
│  │  - Used for: Real-time updates, Logging, Auditing                │ │
│  └──────────────────────────────────────────────────────────────────┘ │
│                                                                        │
│  ┌──────────────────────────────────────────────────────────────────┐ │
│  │                    Job Channel (PUSH/PULL)                       │ │
│  │  - Work distribution to workers                                   │ │
│  │  - Used for: Backtest jobs, Data fetches                         │ │
│  └──────────────────────────────────────────────────────────────────┘ │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Callable, Awaitable, TypeVar, Generic
from uuid import uuid4
import asyncio
import json
import sys
from pathlib import Path

# Add parent to path
SRC_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(SRC_DIR))


# =============================================================================
# Core Enums and Models
# =============================================================================

class ServiceType(str, Enum):
    """Types of services."""
    API = "api"
    DATA = "data"
    BACKTEST = "backtest"
    STRATEGY = "strategy"
    EXECUTION = "execution"
    JOB = "job"
    METRICS = "metrics"


class JobStatus(str, Enum):
    """Job status."""
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class EventType(str, Enum):
    """System events."""
    # Job events
    JOB_CREATED = "job.created"
    JOB_QUEUED = "job.queued"
    JOB_STARTED = "job.started"
    JOB_PROGRESS = "job.progress"
    JOB_COMPLETED = "job.completed"
    JOB_FAILED = "job.failed"
    JOB_CANCELLED = "job.cancelled"

    # Trade events
    TRADE_SIGNAL = "trade.signal"
    TRADE_ENTERED = "trade.entered"
    TRADE_EXITED = "trade.exited"
    TRADE_ERROR = "trade.error"

    # Data events
    DATA_FETCHED = "data.fetched"
    DATA_CACHED = "data.cached"
    DATA_ERROR = "data.error"

    # System events
    SERVICE_STARTED = "service.started"
    SERVICE_STOPPED = "service.stopped"
    HEALTH_CHECK = "health.check"


# =============================================================================
# Message Protocols
# =============================================================================

@dataclass
class Message:
    """Base message for all service communication."""
    command: str
    payload: Dict[str, Any] = field(default_factory=dict)
    request_id: str = field(default_factory=lambda: uuid4().hex)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    source: str = "unknown"
    priority: int = 0  # 0=normal, 1=high, 2=urgent

    def to_bytes(self) -> bytes:
        return json.dumps(self.model_dump()).encode("utf-8")

    @classmethod
    def from_bytes(cls, data: bytes) -> "Message":
        return cls(**json.loads(data.decode("utf-8")))

    def model_dump(self) -> Dict[str, Any]:
        return {
            "command": self.command,
            "payload": self.payload,
            "request_id": self.request_id,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
            "priority": self.priority,
        }


@dataclass
class Event:
    """Event for pub/sub communication."""
    event_type: str
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    source: str = "unknown"
    correlation_id: Optional[str] = None

    def to_bytes(self) -> bytes:
        return json.dumps(self.model_dump()).encode("utf-8")

    @classmethod
    def from_bytes(cls, data: bytes) -> "Event":
        return cls(**json.loads(data.decode("utf-8")))

    def model_dump(self) -> Dict[str, Any]:
        result = {
            "event_type": self.event_type,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
        }
        if self.correlation_id:
            result["correlation_id"] = self.correlation_id
        return result


@dataclass
class JobMessage:
    """Job message for worker distribution."""
    job_id: str
    job_type: str
    payload: Dict[str, Any]
    priority: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)
    retry_count: int = 0
    max_retries: int = 3

    def to_bytes(self) -> bytes:
        return json.dumps(self.model_dump()).encode("utf-8")

    @classmethod
    def from_bytes(cls, data: bytes) -> "JobMessage":
        return cls(**json.loads(data.decode("utf-8")))

    def model_dump(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "job_type": self.job_type,
            "payload": self.payload,
            "priority": self.priority,
            "created_at": self.created_at.isoformat(),
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
        }


# =============================================================================
# Service Base Classes
# =============================================================================

class ServiceBase(ABC):
    """Base class for all services."""

    def __init__(
        self,
        name: str,
        service_type: ServiceType,
        addresses: Dict[str, str],
    ):
        self.name = name
        self.service_type = service_type
        self.addresses = addresses
        self._running = False
        self._health = {"status": "healthy", "last_check": datetime.utcnow()}

    @property
    def is_running(self) -> bool:
        return self._running

    @abstractmethod
    async def start(self) -> None:
        """Start the service."""
        ...

    @abstractmethod
    async def stop(self) -> None:
        """Stop the service."""
        ...

    @abstractmethod
    async def handle_command(self, message: Message) -> Dict[str, Any]:
        """Handle a command message."""
        ...

    def health_check(self) -> Dict[str, Any]:
        """Return service health."""
        self._health["last_check"] = datetime.utcnow()
        return self._health


class ServiceClient:
    """Base client for communicating with services."""

    def __init__(
        self,
        name: str,
        addresses: Dict[str, str],
        timeout_ms: int = 30000,
    ):
        self.name = name
        self.addresses = addresses
        self.timeout_ms = timeout_ms
        self._sockets: Dict[str, Any] = {}

    def _get_socket(self, channel: str):
        """Get or create socket for channel."""
        if channel not in self._sockets:
            import pynng
            self._sockets[channel] = pynng.Req0(
                dial=self.addresses.get(channel, f"ipc:///tmp/dgbit_{channel}.ipc"),
                block=False
            )
        return self._sockets[channel]

    async def send_command(
        self,
        channel: str,
        command: str,
        payload: Dict[str, Any] = None,
        priority: int = 0,
    ) -> Dict[str, Any]:
        """Send a command and wait for response."""
        message = Message(
            command=command,
            payload=payload or {},
            source=self.name,
            priority=priority,
        )

        socket = self._get_socket(channel)

        def _sync_send():
            socket.send(message.to_bytes())
            return socket.recv()

        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, _sync_send)
        return json.loads(response.decode("utf-8"))

    def close(self):
        """Close all sockets."""
        for socket in self._sockets.values():
            socket.close()
        self._sockets.clear()


# =============================================================================
# Event Bus
# =============================================================================

class EventPublisher:
    """Publisher for events (PUB socket)."""

    def __init__(self, address: str = "ipc:///tmp/dgbit_evt.ipc"):
        self.address = address
        self._socket = None

    def connect(self):
        """Connect to the event bus."""
        import pynng
        self._socket = pynng.Pub0(listen=self.address)
        # Set subscription filter if needed
        self._socket.recv_timeout = 0  # Non-blocking

    def publish(self, event: Event) -> None:
        """Publish an event."""
        if self._socket is None:
            self.connect()
        self._socket.send(event.to_bytes())

    def close(self):
        """Close the publisher."""
        if self._socket:
            self._socket.close()
            self._socket = None


class EventSubscriber:
    """Subscriber for events (SUB socket)."""

    def __init__(self, address: str = "ipc:///tmp/dgbit_evt.ipc"):
        self.address = address
        self._socket = None
        self._handlers: Dict[str, Callable] = {}

    def connect(self):
        """Connect to the event bus."""
        import pynng
        self._socket = pynng.Sub0(dial=self.address)
        # Subscribe to all events by default
        self.subscribe("")

    def subscribe(self, event_type: str):
        """Subscribe to an event type."""
        if self._socket:
            self._socket.subscribe(event_type.encode("utf-8"))

    def unsubscribe(self, event_type: str):
        """Unsubscribe from an event type."""
        if self._socket:
            self._socket.unsubscribe(event_type.encode("utf-8"))

    def add_handler(self, event_type: str, handler: Callable):
        """Add a handler for an event type."""
        self._handlers[event_type] = handler
        self.subscribe(event_type)

    def remove_handler(self, event_type: str):
        """Remove a handler for an event type."""
        if event_type in self._handlers:
            del self._handlers[event_type]
            self.unsubscribe(event_type)

    async def listen(self):
        """Listen for events (blocking)."""
        if self._socket is None:
            self.connect()

        while self._running:
            try:
                def _recv():
                    return self._socket.recv()

                loop = asyncio.get_event_loop()
                message = await loop.run_in_executor(None, _recv)
                event = Event.from_bytes(message)

                # Call matching handler
                handler = self._handlers.get(event.event_type)
                if handler:
                    handler(event)
                elif "" in self._handlers:
                    self._handlers[""](event)

            except Exception as e:
                import sys
                from loguru import logger
                logger.error(f"Error processing event: {e}")

    def start_listening(self):
        """Start listening in the background."""
        import asyncio
        self._running = True
        asyncio.create_task(self.listen())

    def stop_listening(self):
        """Stop listening."""
        self._running = False

    def close(self):
        """Close the subscriber."""
        self.stop_listening()
        if self._socket:
            self._socket.close()
            self._socket = None


# =============================================================================
# Job Queue
# =============================================================================

class JobPublisher:
    """Publisher for job queue (PUSH socket)."""

    def __init__(self, address: str = "ipc:///tmp/dgbit_queue.ipc"):
        self.address = address
        self._socket = None

    def connect(self):
        """Connect to the job queue."""
        import pynng
        self._socket = pynng.Push0(dial=self.address)

    def publish(self, job: JobMessage) -> None:
        """Publish a job to the queue."""
        if self._socket is None:
            self.connect()
        self._socket.send(job.to_bytes())

    def close(self):
        """Close the publisher."""
        if self._socket:
            self._socket.close()
            self._socket = None


class JobWorker:
    """Worker for job queue (PULL socket)."""

    def __init__(self, name: str, address: str = "ipc:///tmp/dgbit_queue.ipc"):
        self.name = name
        self.address = address
        self._socket = None
        self._running = False
        self._handlers: Dict[str, Callable] = {}

    def connect(self):
        """Connect to the job queue."""
        import pynng
        self._socket = pynng.Pull0(listen=self.address)

    def register_handler(self, job_type: str, handler: Callable):
        """Register a handler for a job type."""
        self._handlers[job_type] = handler

    async def listen(self):
        """Listen for jobs (blocking)."""
        if self._socket is None:
            self.connect()

        while self._running:
            try:
                def _recv():
                    return self._socket.recv()

                loop = asyncio.get_event_loop()
                message = await loop.run_in_executor(None, _recv)
                job = JobMessage.from_bytes(message)

                # Call matching handler
                handler = self._handlers.get(job.job_type)
                if handler:
                    try:
                        result = await handler(job) if asyncio.iscoroutinefunction(handler) else handler(job)
                        await self._ack_job(job, result)
                    except Exception as e:
                        await self._fail_job(job, str(e))
                else:
                    await self._fail_job(job, f"No handler for job type: {job.job_type}")

            except Exception as e:
                from loguru import logger
                logger.error(f"Error processing job: {e}")

    async def _ack_job(self, job: JobMessage, result: Any):
        """Acknowledge job completion."""
        # In a real implementation, this would send to a result queue
        from dgbit_services import Event, EventPublisher
        publisher = EventPublisher()
        publisher.publish(Event(
            event_type=EventType.JOB_COMPLETED.value,
            data={"job_id": job.job_id, "result": result},
            source=self.name,
        ))

    async def _fail_job(self, job: JobMessage, error: str):
        """Acknowledge job failure."""
        from dgbit_services import Event, EventPublisher
        publisher = EventPublisher()
        publisher.publish(Event(
            event_type=EventType.JOB_FAILED.value,
            data={"job_id": job.job_id, "error": error},
            source=self.name,
        ))

    def start(self):
        """Start listening in the background."""
        import asyncio
        self._running = True
        asyncio.create_task(self.listen())

    def stop(self):
        """Stop listening."""
        self._running = False

    def close(self):
        """Close the worker."""
        self.stop()
        if self._socket:
            self._socket.close()
            self._socket = None


# =============================================================================
# Service Registry
# =============================================================================

class ServiceRegistry:
    """Registry for dynamic service discovery."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._services = {}
            cls._instance._address = "ipc:///tmp/dgbit_registry.ipc"
        return cls._instance

    def register(self, service: ServiceBase):
        """Register a service."""
        self._services[f"{service.service_type.value}:{service.name}"] = {
            "name": service.name,
            "type": service.service_type.value,
            "addresses": service.addresses,
            "health": service.health_check(),
            "registered_at": datetime.utcnow().isoformat(),
        }

    def unregister(self, name: str, service_type: ServiceType):
        """Unregister a service."""
        key = f"{service_type.value}:{name}"
        if key in self._services:
            del self._services[key]

    def get(self, name: str, service_type: ServiceType) -> Optional[Dict]:
        """Get service info."""
        return self._services.get(f"{service_type.value}:{name}")

    def list_by_type(self, service_type: ServiceType) -> List[Dict]:
        """List all services of a type."""
        prefix = f"{service_type.value}:"
        return [
            info for key, info in self._services.items()
            if key.startswith(prefix)
        ]

    def list_all(self) -> Dict[str, Dict]:
        """List all registered services."""
        return self._services.copy()

    def clear(self):
        """Clear all registrations."""
        self._services.clear()


# =============================================================================
# Import from submodules
# =============================================================================

# Import Job Queue classes
from dgbit_services.jobs import Job, JobStore, JobQueue, JobWorker

# Import Event Bus classes
from dgbit_services.events import EventBus, EventBusService

# Import Strategy classes
from dgbit_services.strategy import (
    StrategyConfig, Signal, StrategyMetrics,
    StrategyInterface, StrategyRegistry,
    StrategyService, StrategyClient
)

# Import Execution classes
from dgbit_services.execution import (
    OrderSide, OrderType, OrderStatus, PositionSide,
    Order, Position, Trade, ExecutionConfig,
    ExchangeAdapter, BybitAdapter, SimulatedAdapter,
    ExecutionService, ExecutionClient
)

# Import Data Service client
from dgbit_services.data import DataServiceClient, DataAPIHelper


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Enums
    "ServiceType",
    "JobStatus",
    "EventType",
    # Messages
    "Message",
    "Event",
    "JobMessage",
    # Service Base
    "ServiceBase",
    "ServiceClient",
    # Event Bus
    "EventPublisher",
    "EventSubscriber",
    # Job Queue
    "JobQueue",
    "JobStore",
    "JobWorker",
    "JobPublisher",
    # Registry
    "ServiceRegistry",
    # Data Service
    "DataServiceClient",
    "DataAPIHelper",
    # Execution
    "OrderSide",
    "OrderType",
    "OrderStatus",
    "PositionSide",
    "Order",
    "Position",
    "Trade",
    "ExecutionConfig",
    "ExchangeAdapter",
    "BybitAdapter",
    "SimulatedAdapter",
    "ExecutionService",
    "ExecutionClient",
    # Strategy
    "StrategyConfig",
    "Signal",
    "StrategyMetrics",
    "StrategyInterface",
    "StrategyRegistry",
    "StrategyService",
    "StrategyClient",
]
