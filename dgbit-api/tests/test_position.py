import pytest
from datetime import datetime
from dgbit_core.trading.position import Position, PositionSide, Order, OrderType, OrderStatus


class TestPosition:
    """Tests for Position class."""

    def test_position_creation(self, sample_position):
        """Test position is created correctly."""
        assert sample_position.symbol == "BTCUSDT"
        assert sample_position.side == PositionSide.LONG
        assert sample_position.entry_price == 50000.0
        assert sample_position.is_open is True

    def test_position_close(self, sample_position):
        """Test position can be closed."""
        exit_time = datetime.utcnow()
        sample_position.close(50200.0, exit_time)

        assert sample_position.exit_price == 50200.0
        assert sample_position.exit_time == exit_time
        assert sample_position.is_open is False

    def test_position_return_pct(self, sample_position):
        """Test return percentage calculation."""
        exit_time = datetime.utcnow()
        sample_position.close(50200.0, exit_time)

        # (50200 - 50000) / 50000 = 0.004 = 0.4%
        expected_return = (50200.0 - 50000.0) / 50000.0
        assert abs(sample_position.return_pct() - expected_return) < 0.0001

    def test_short_position_return(self):
        """Test return calculation for short positions."""
        position = Position(
            symbol="BTCUSDT",
            side=PositionSide.SHORT,
            entry_price=50000.0,
            entry_time=datetime.utcnow(),
            quantity=10000.0,
            take_profit_price=49900.0,
            stop_loss_price=50250.0,
        )

        exit_time = datetime.utcnow()
        position.close(49800.0, exit_time)

        # Short position: (entry - exit) / entry = (50000 - 49800) / 50000 = 0.004
        expected_return = (50000.0 - 49800.0) / 50000.0
        assert abs(position.return_pct() - expected_return) < 0.0001

    def test_position_duration(self, sample_position_with_duration):
        """Test position duration calculation."""
        position, exit_time = sample_position_with_duration

        position.close(50200.0, exit_time)

        # Duration should be ~60 minutes
        assert position.duration == pytest.approx(60, abs=1)


class TestOrder:
    """Tests for Order class."""

    def test_order_creation(self):
        """Test order creation."""
        order = Order(
            symbol="BTCUSDT",
            side=PositionSide.LONG,
            order_type=OrderType.MARKET,
            quantity=1.5,
        )

        assert order.symbol == "BTCUSDT"
        assert order.status == OrderStatus.PENDING
        assert order.created_at is not None

    def test_order_fill(self):
        """Test order can be filled."""
        order = Order(
            symbol="BTCUSDT",
            side=PositionSide.LONG,
            order_type=OrderType.LIMIT,
            quantity=1.0,
            price=50000.0,
        )

        order.filled_price = 50000.0
        order.filled_quantity = 1.0
        order.status = OrderStatus.FILLED
        order.filled_at = datetime.utcnow()

        assert order.status == OrderStatus.FILLED
        assert order.filled_price == 50000.0
