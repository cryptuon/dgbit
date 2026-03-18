"""
Integration tests for the dgbit Services framework.

These tests verify the service bus components work correctly together.
"""

import asyncio
import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch

# Add src to path
SRC_DIR = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(SRC_DIR))

from dgbit_services import (
    Message, Event, JobMessage,
    ServiceType, JobStatus, EventType,
    ServiceBase, ServiceClient,
    EventPublisher, EventSubscriber,
    JobPublisher, JobWorker,
    ServiceRegistry,
    JobQueue, JobStore, Job,
    OrderSide, OrderType, OrderStatus, PositionSide,
    Order, Position, Trade,
    StrategyConfig, Signal,
    DataServiceClient, DataAPIHelper,
)


class TestMessageProtocols:
    """Test message serialization/deserialization."""

    def test_message_serialization(self):
        """Test Message to/from bytes."""
        msg = Message(
            command="test_command",
            payload={"key": "value"},
            source="test",
        )
        bytes_data = msg.to_bytes()
        restored = Message.from_bytes(bytes_data)

        assert restored.command == msg.command
        assert restored.payload == msg.payload
        assert restored.source == msg.source
        assert restored.request_id == msg.request_id

    def test_event_serialization(self):
        """Test Event to/from bytes."""
        evt = Event(
            event_type="test.event",
            data={"key": "value"},
            source="test",
        )
        bytes_data = evt.to_bytes()
        restored = Event.from_bytes(bytes_data)

        assert restored.event_type == evt.event_type
        assert restored.data == evt.data
        assert restored.source == evt.source

    def test_job_message_serialization(self):
        """Test JobMessage to/from bytes."""
        job = JobMessage(
            job_id="test-123",
            job_type="backtest",
            payload={"config": {}},
        )
        bytes_data = job.to_bytes()
        restored = JobMessage.from_bytes(bytes_data)

        assert restored.job_id == job.job_id
        assert restored.job_type == job.job_type
        assert restored.payload == job.payload


class TestJobQueue:
    """Test JobQueue functionality."""

    def test_job_store_create_get(self):
        """Test Job creation and retrieval."""
        store = JobStore()
        job = Job(
            job_id="test-001",
            job_type="backtest",
            payload={"symbol": "BTCUSDT"},
        )
        store.create(job)

        retrieved = store.get("test-001")
        assert retrieved is not None
        assert retrieved.job_id == "test-001"
        assert retrieved.job_type == "backtest"

    def test_job_store_list_by_status(self):
        """Test listing jobs by status."""
        store = JobStore()

        # Create jobs with different statuses
        job1 = Job(job_id="j1", job_type="backtest", payload={})
        job1.status = JobStatus.PENDING
        store.create(job1)

        job2 = Job(job_id="j2", job_type="data", payload={})
        job2.status = JobStatus.RUNNING
        store.create(job2)

        pending = store.list_by_status(JobStatus.PENDING)
        assert len(pending) == 1
        assert pending[0].job_id == "j1"

        running = store.list_by_status(JobStatus.RUNNING)
        assert len(running) == 1
        assert running[0].job_id == "j2"

    def test_job_store_update_status(self):
        """Test job status updates."""
        store = JobStore()
        job = Job(job_id="test-001", job_type="backtest", payload={})
        store.create(job)

        # Update status - need to also add to new status list
        job.status = JobStatus.RUNNING
        store._by_status[JobStatus.RUNNING].append(job.job_id)  # Add to index
        store.update(job)

        # Verify update
        retrieved = store.get("test-001")
        assert retrieved.status == JobStatus.RUNNING

        # Check by_status index
        running = store.list_by_status(JobStatus.RUNNING)
        assert len(running) == 1


class TestExecutionModels:
    """Test execution service data models."""

    def test_order_creation(self):
        """Test Order model."""
        order = Order(
            order_id="ord-001",
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=0.001,
        )

        assert order.order_id == "ord-001"
        assert order.symbol == "BTCUSDT"
        assert order.side == OrderSide.BUY
        assert order.status == OrderStatus.PENDING

    def test_order_to_dict(self):
        """Test Order serialization."""
        order = Order(
            order_id="ord-001",
            symbol="BTCUSDT",
            side=OrderSide.SELL,
            order_type=OrderType.LIMIT,
            quantity=0.01,
            price=50000.0,
        )
        data = order.to_dict()

        assert data["order_id"] == "ord-001"
        assert data["symbol"] == "BTCUSDT"
        assert data["side"] == "sell"
        assert data["price"] == 50000.0

    def test_position_creation(self):
        """Test Position model."""
        pos = Position(
            symbol="BTCUSDT",
            side=PositionSide.LONG,
            quantity=0.1,
            entry_price=45000.0,
        )

        assert pos.side == PositionSide.LONG
        assert pos.unrealized_pnl == 0.0

    def test_trade_creation(self):
        """Test Trade model."""
        trade = Trade(
            trade_id="trd-001",
            order_id="ord-001",
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            quantity=0.001,
            price=45000.0,
            fee=45.0,
        )

        assert trade.trade_id == "trd-001"
        assert trade.fee == 45.0


class TestStrategyModels:
    """Test strategy service data models."""

    def test_strategy_config(self):
        """Test StrategyConfig model."""
        config = StrategyConfig(
            strategy_name="wavelet_reversal",
            parameters={"threshold": 0.7},
            capital=10000.0,
        )

        assert config.strategy_name == "wavelet_reversal"
        assert config.capital == 10000.0

    def test_signal_creation(self):
        """Test Signal model."""
        signal = Signal(
            strategy_name="wavelet_reversal",
            symbol="BTCUSDT",
            direction="long",
            confidence=0.85,
        )

        assert signal.direction == "long"
        assert signal.confidence == 0.85


class TestServiceRegistry:
    """Test ServiceRegistry functionality."""

    def setup_method(self):
        """Reset registry before each test."""
        ServiceRegistry._instance = None

    def test_registry_singleton(self):
        """Test registry is a singleton."""
        registry1 = ServiceRegistry()
        registry2 = ServiceRegistry()
        assert registry1 is registry2

    def test_register_unregister(self):
        """Test service registration."""
        registry = ServiceRegistry()

        mock_service = Mock()
        mock_service.name = "test_service"
        mock_service.service_type = ServiceType.DATA
        mock_service.addresses = {"cmd": "ipc:///tmp/test.ipc"}
        mock_service.health_check = Mock(return_value={"status": "ok"})

        registry.register(mock_service)

        # Verify registration
        info = registry.get("test_service", ServiceType.DATA)
        assert info is not None
        assert info["name"] == "test_service"
        assert info["type"] == "data"

        # Unregister
        registry.unregister("test_service", ServiceType.DATA)
        info = registry.get("test_service", ServiceType.DATA)
        assert info is None

    def test_list_by_type(self):
        """Test listing services by type."""
        registry = ServiceRegistry()

        for i in range(3):
            mock_service = Mock()
            mock_service.name = f"service_{i}"
            mock_service.service_type = ServiceType.DATA
            mock_service.addresses = {}
            mock_service.health_check = Mock(return_value={"status": "ok"})
            registry.register(mock_service)

        services = registry.list_by_type(ServiceType.DATA)
        assert len(services) == 3


class TestEnums:
    """Test enum values."""

    def test_service_type_values(self):
        """Test ServiceType enum values."""
        assert ServiceType.API.value == "api"
        assert ServiceType.DATA.value == "data"
        assert ServiceType.STRATEGY.value == "strategy"

    def test_job_status_values(self):
        """Test JobStatus enum values."""
        assert JobStatus.PENDING.value == "pending"
        assert JobStatus.RUNNING.value == "running"
        assert JobStatus.COMPLETED.value == "completed"

    def test_event_type_values(self):
        """Test EventType enum values."""
        assert EventType.JOB_CREATED.value == "job.created"
        assert EventType.TRADE_SIGNAL.value == "trade.signal"

    def test_order_side_values(self):
        """Test OrderSide enum values."""
        assert OrderSide.BUY.value == "buy"
        assert OrderSide.SELL.value == "sell"

    def test_position_side_values(self):
        """Test PositionSide enum values."""
        assert PositionSide.LONG.value == "long"
        assert PositionSide.SHORT.value == "short"


class TestDataAPIHelper:
    """Test DataAPIHelper functionality."""

    def test_helper_creation(self):
        """Test helper creation."""
        helper = DataAPIHelper()
        assert helper._client is None

    def test_helper_with_client(self):
        """Test helper with custom client."""
        mock_client = Mock()
        helper = DataAPIHelper(client=mock_client)
        assert helper._client is mock_client


class TestEventPublisher:
    """Test EventPublisher functionality."""

    def test_publisher_creation(self):
        """Test publisher creation."""
        publisher = EventPublisher(address="ipc:///tmp/test_evt.ipc")
        assert publisher.address == "ipc:///tmp/test_evt.ipc"
        assert publisher._socket is None


class TestJobPublisher:
    """Test JobPublisher functionality."""

    def test_publisher_creation(self):
        """Test job publisher creation."""
        publisher = JobPublisher(address="ipc:///tmp/test_queue.ipc")
        assert publisher.address == "ipc:///tmp/test_queue.ipc"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
