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

Fetch market data from Bybit.

```python
from dgbit_core.data.data_fetcher import BybitDataFetcher

# Public data (no API keys needed)
fetcher = BybitDataFetcher()

# With API keys (for private endpoints)
fetcher = BybitDataFetcher(
    api_key="your_key",
    api_secret="your_secret",
    testnet=True,
)
```

#### get_kline_data

Fetch OHLCV candlestick data.

```python
data = fetcher.get_kline_data(
    symbol="BTCUSDT",     # Trading pair
    interval="15",        # Interval in minutes
    limit=1000,           # Number of candles
)

# Returns pandas DataFrame with columns:
# timestamp, open, high, low, close, volume
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `symbol` | str | Required | Trading pair (e.g., "BTCUSDT") |
| `interval` | str | "1" | Candle interval in minutes |
| `limit` | int | 200 | Number of candles (max 1000) |
| `start_time` | datetime | None | Start time for historical data |
| `end_time` | datetime | None | End time for historical data |

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

```python
from dgbit_core.trading.strategy import (
    WaveletReversalStrategy,
    MACrossoverStrategy,
    RSIStrategy,
    BollingerBandStrategy,
)

# Wavelet Reversal
strategy = WaveletReversalStrategy(
    min_signal_threshold=0.75,
    take_profit_pct=0.02,
    stop_loss_pct=0.01,
)

# MA Crossover
strategy = MACrossoverStrategy(
    fast_period=12,
    slow_period=26,
)

# RSI
strategy = RSIStrategy(
    period=14,
    oversold=30,
    overbought=70,
)

# Bollinger Bands
strategy = BollingerBandStrategy(
    period=20,
    num_std=2.0,
)
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

Track trading positions.

```python
from dgbit_core.trading.position import Position, PositionSide

position = Position(
    symbol="BTCUSDT",
    side=PositionSide.LONG,
    entry_price=42000.0,
    quantity=0.001,
    entry_time=datetime.now(),
    take_profit_price=42840.0,
    stop_loss_price=41580.0,
)

# Check position status
print(f"Is open: {position.is_open}")
print(f"Entry: {position.entry_price}")

# Calculate unrealized PnL
current_price = 42500.0
pnl = position.calculate_pnl(current_price)
print(f"Unrealized PnL: {pnl:.2f}")

# Close position
position.close(exit_price=42500.0, exit_time=datetime.now())
print(f"Realized PnL: {position.return_pct:.2%}")
```

### Order

Represent trading orders.

```python
from dgbit_core.trading.position import Order, OrderType, OrderStatus

order = Order(
    symbol="BTCUSDT",
    side=PositionSide.LONG,
    order_type=OrderType.MARKET,
    quantity=0.001,
    price=None,  # Market order
)

# Limit order
order = Order(
    symbol="BTCUSDT",
    side=PositionSide.LONG,
    order_type=OrderType.LIMIT,
    quantity=0.001,
    price=41500.0,
)
```

## Wavelet Predictor

ML-based price prediction using wavelets.

```python
from dgbit_core.models.predictor import PricePredictor

predictor = PricePredictor()

# Get reversal probability
probability = predictor.get_reversal_probability(data['close'].values)
print(f"Reversal probability: {probability:.2%}")

# Decompose signal
coefficients = predictor.decompose_signal(data['close'].values)
```

## Service Clients

### DataServiceClient

Access the data service via NNG.

```python
from dgbit_services import DataServiceClient

client = DataServiceClient()
await client.connect()

# Fetch data
data = await client.fetch_klines("BTCUSDT", interval="15", limit=100)

await client.close()
```

### StrategyClient

Access the strategy service.

```python
from dgbit_services.strategy import StrategyClient

client = StrategyClient()
await client.connect()

# Generate signal
signal = await client.generate_signal(
    strategy="wavelet_reversal",
    symbol="BTCUSDT",
)

await client.close()
```

### ExecutionClient

Access the execution service.

```python
from dgbit_services.execution import ExecutionClient

client = ExecutionClient()
await client.connect()

# Place order
order = await client.place_order(
    symbol="BTCUSDT",
    side="buy",
    quantity=0.001,
)

# Get positions
positions = await client.get_positions()

await client.close()
```

## Error Handling

```python
from dgbit_core.exceptions import (
    DGBitError,
    DataFetchError,
    StrategyError,
    BacktestError,
)

try:
    result = backtester.run(data)
except BacktestError as e:
    print(f"Backtest failed: {e}")
except DGBitError as e:
    print(f"General error: {e}")
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
