import pytest
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

# Add paths for imports
SHARED_DIR = Path(__file__).parent.parent / "shared" / "python"
SRC_DIR = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(SRC_DIR))
sys.path.insert(0, str(SHARED_DIR))


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture
def sample_market_data():
    """Generate sample market data for testing."""
    import pandas as pd
    import numpy as np

    np.random.seed(42)
    n = 500

    # Generate timestamps
    base_time = pd.Timestamp("2024-01-01")
    timestamps = [base_time + pd.Timedelta(minutes=i) for i in range(n)]

    # Generate price data with some trend
    returns = np.random.randn(n) * 0.02 + 0.0005  # Slight upward trend
    prices = 50000 * np.cumprod(1 + returns)

    # Generate OHLCV data
    data = pd.DataFrame({
        'timestamp': timestamps,
        'open': prices * (1 + np.random.randn(n) * 0.001),
        'high': prices * (1 + np.abs(np.random.randn(n)) * 0.002),
        'low': prices * (1 - np.abs(np.random.randn(n)) * 0.002),
        'close': prices,
        'volume': np.abs(np.random.randn(n) * 1000 + 5000),
    })

    return data


@pytest.fixture
def sample_position():
    """Create a sample position for testing."""
    from dgbit_core.trading.position import Position, PositionSide
    from datetime import datetime, timedelta

    return Position(
        symbol="BTCUSDT",
        side=PositionSide.LONG,
        entry_price=50000.0,
        entry_time=datetime.utcnow(),
        quantity=10000.0,
        take_profit_price=50100.0,
        stop_loss_price=49750.0,
    )


@pytest.fixture
def sample_position_with_duration():
    """Create a sample position with known duration for testing."""
    from dgbit_core.trading.position import Position, PositionSide
    from datetime import datetime, timedelta

    entry_time = datetime.utcnow()
    exit_time = entry_time + timedelta(minutes=60)

    return Position(
        symbol="BTCUSDT",
        side=PositionSide.LONG,
        entry_price=50000.0,
        entry_time=entry_time,
        quantity=10000.0,
        take_profit_price=50100.0,
        stop_loss_price=49750.0,
    ), exit_time


@pytest.fixture
def sample_backtest_config():
    """Create a sample backtest configuration."""
    from dgbit_core.backtesting.backtester import BacktestConfig

    return BacktestConfig(
        initial_capital=10000.0,
        transaction_fee=0.001,
        train_split=0.7,
    )


@pytest.fixture
def mock_db_init():
    """Mock database initialization for API tests."""
    with patch('dgbit_api.db.connection.init_db', new_callable=AsyncMock) as mock_init, \
         patch('dgbit_api.db.connection.close_db', new_callable=AsyncMock) as mock_close:
        mock_init.return_value = None
        mock_close.return_value = None
        yield {"init": mock_init, "close": mock_close}
