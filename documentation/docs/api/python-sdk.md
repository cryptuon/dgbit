# Python SDK Reference

Direct Python interface to dgbit components.

## Core Modules

### dgbit_core

The core trading library containing strategies, backtesting, and data fetching.

```python
import dgbit_core
```

## Data Fetching

### BybitDataFetcher

Fetch market data from Bybit. `api_key` and `api_secret` are positional and required; pass empty strings if you only need the public kline endpoints.

```python
from dgbit_core.data.data_fetcher import BybitDataFetcher

fetcher = BybitDataFetcher(
    api_key="your_key",
    api_secret="your_secret",
    testnet=True,
)
```

For purely public data you can also use `BybitDataSource` from `dgbit_core.data.fetcher`, which defaults both API fields to `""`.

#### get_kline_data

```python
data = fetcher.get_kline_data(
    symbol="BTCUSDT",
    interval="15",   # minutes; "D" for daily on Bybit's kline API
    limit=1000,
)
```

The returned DataFrame has columns `timestamp, open, high, low, close, volume, turnover, price_change, volume_change, rolling_volatility, rolling_volume` and is sorted ascending by timestamp.

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `symbol` | str | Required | Trading pair (e.g. `"BTCUSDT"`) |
| `interval` | str | `"1"` | Candle interval |
| `lookback_hours` | int | `24` | Used to derive `limit` |
| `limit` | int | `1000` | Capped at `min(1000, lookback_hours * 60)` and Bybit's per-request maximum of 1000 |

The fetcher always calls the spot `get_kline` endpoint (`category="spot"`).

## Trading Strategies

### BaseStrategy

Abstract base class for all strategies.

```python
from dgbit_core.trading.strategy import BaseStrategy, StrategyMetadata

class MyStrategy(BaseStrategy):
    metadata = StrategyMetadata(
        name="my_strategy",
        description="My custom strategy",
        author="Your Name",
        version="1.0.0",
        signal_type=SignalType.MOMENTUM,
        parameters={},
    )
    
    def generate_signal(self, data: pd.DataFrame) -> float:
        # Return value between 0.0 and 1.0
        return 0.5
```

#### Methods

| Method | Description |
|--------|-------------|
| `generate_signal(data)` | Generate trading signal (0.0-1.0) |
| `train(data)` | Train strategy on historical data |
| `should_enter(data)` | Determine if should enter position |
| `calculate_exit_prices(entry, direction)` | Calculate TP/SL prices |

### Built-in Strategies

`WaveletReversalStrategy` lives in `dgbit_core.trading.strategy`; the other three are defined in `dgbit_core.trading.examples` and re-exported from `dgbit_core.trading`.

```python
from dgbit_core.trading import (
    WaveletReversalStrategy,
    MACrossoverStrategy,
    RSIStrategy,
    BollingerBandStrategy,
)

WaveletReversalStrategy(
    min_signal_threshold=0.75,
    take_profit_pct=0.002,
    stop_loss_pct=0.005,
)

MACrossoverStrategy(fast_period=10, slow_period=20, ma_type="sma")

RSIStrategy(period=14, oversold=30.0, overbought=70.0)

BollingerBandStrategy(period=20, std_dev=2.0)
```

### Strategy Registry

Manage strategies centrally.

```python
from dgbit_core.trading.strategy import strategy_registry

# List all strategies
strategies = strategy_registry.list_strategies()
for name, metadata in strategies.items():
    print(f"{name}: {metadata.description}")

# Create strategy by name
strategy = strategy_registry.create(
    "wavelet_reversal",
    min_signal_threshold=0.8,
)

# Register custom strategy
strategy_registry.register(MyStrategy)
```

## Backtesting

### BacktestConfig

Configure backtest parameters.

```python
from dgbit_core.backtesting import BacktestConfig

config = BacktestConfig(
    initial_capital=10000.0,    # Starting capital
    transaction_fee=0.001,      # 0.1% per trade
    train_split=0.7,            # 70% train, 30% test
    report_dir="reports",       # Report output directory
)
```

### Backtester

Run backtests on historical data.

```python
from dgbit_core.backtesting import Backtester

backtester = Backtester(config=config)
backtester.strategy = strategy

result = backtester.run(data)
```

### BacktestResult

Results from a backtest run.

```python
# Performance metrics
result.metrics['total_trades']      # Number of trades
result.metrics['win_rate']          # Win rate (0-1)
result.metrics['total_return']      # Total return percentage
result.metrics['max_drawdown']      # Maximum drawdown
result.metrics['profit_factor']     # Gross profit / gross loss
result.metrics['avg_return']        # Average return per trade
result.metrics['avg_duration']      # Average trade duration (minutes)
result.metrics['final_capital']     # Final capital amount

# Trade list
for trade in result.trades:
    print(f"{trade.timestamp}: {trade.action} @ {trade.price}")
    if trade.pnl:
        print(f"  PnL: {trade.pnl:.2f} ({trade.pnl_pct:.2%})")

# Equity curve
for point in result.equity_curve:
    print(f"{point['timestamp']}: ${point['capital']:.2f}")
```

## Position Management

### Position

```python
from datetime import datetime
from dgbit_core.trading.position import Position, PositionSide

position = Position(
    symbol="BTCUSDT",
    side=PositionSide.LONG,
    entry_price=42000.0,
    entry_time=datetime.utcnow(),
    quantity=0.001,
    take_profit_price=42840.0,
    stop_loss_price=41580.0,
)

# Unrealised PnL ratio (positive for an in-profit long)
pnl_ratio = position.calculate_pnl(current_price=42500.0)

# Close position
position.close(exit_price=42500.0, exit_time=datetime.utcnow())
print(f"Realized return: {position.return_pct():.2%}")
```

`return_pct` is a method (not a property), and `Position.duration` is the duration in minutes between entry and exit.

### Order

`Order` carries only the basic fields used by the backtester / live trader; advanced order types are handled in the Bybit adapter, not on this dataclass.

```python
from dgbit_core.trading.position import Order, OrderType, OrderStatus, PositionSide

Order(
    symbol="BTCUSDT",
    side=PositionSide.LONG,
    order_type=OrderType.MARKET,
    quantity=0.001,
)
```

`OrderType` exposes `MARKET` and `LIMIT`; `OrderStatus` exposes `PENDING`, `FILLED`, `CANCELLED`.

## Wavelet Predictor

Wavelet-based reversal probability used by `WaveletReversalStrategy`.

```python
from dgbit_core.models.predictor import PricePredictor

predictor = PricePredictor()  # uses 'db1' wavelet, level=3, window_size=60

# Pass the OHLCV DataFrame; returns a probability in [0.0, 1.0]
prob = predictor.predict(data)

# Lower-level helpers operate on numpy arrays
approximation, details = predictor.decompose_signal(data['close'].values)
```

Despite the strategy docstring mentioning "Daubechies 4" (db4), the shipped implementation uses `db1` (the Haar wavelet) at level 3 over a 60-sample window. Fewer than 60 rows of OHLCV data make `predict` return `0.0`.

## Service Clients

NNG-backed clients used by the FastAPI routes. Their public methods match the routes documented in [REST API](rest-api.md):

- `dgbit_services.DataServiceClient` (`get_klines`, `get_cache_status`, `clear_cache`)
- `dgbit_services.strategy.StrategyClient` (`list_strategies`, `generate_signal`)
- `dgbit_services.execution.ExecutionClient` (`get_orders`, `get_order`, `create_order`, `cancel_order`, `get_positions`, `get_balance`, `close_position`)

Refer to the source under `dgbit-api/src/dgbit_services/` for the exact signatures and async semantics of each method.

## Error Handling

There is no dedicated `dgbit_core.exceptions` module yet. The backtester raises plain `ValueError` for missing columns; the Bybit adapter and data fetcher log errors via `loguru` and return empty results. Catch the standard exception types when integrating:

```python
try:
    result = backtester.run(data)
except ValueError as e:
    print(f"Backtest failed: {e}")
```

## Type Hints

dgbit is fully typed. Use with mypy:

```bash
mypy your_script.py
```

Example with types:

```python
from dgbit_core.backtesting import Backtester, BacktestConfig, BacktestResult
from dgbit_core.trading.strategy import BaseStrategy
import pandas as pd

def run_backtest(
    data: pd.DataFrame,
    strategy: BaseStrategy,
    config: BacktestConfig,
) -> BacktestResult:
    backtester = Backtester(config=config)
    backtester.strategy = strategy
    return backtester.run(data)
```
