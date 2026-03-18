# Strategy Architecture

This document describes the extensible strategy architecture for dgbit.

## Overview

The strategy system is designed to be easily extensible - you can add new trading strategies without modifying core backtesting or execution code.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Strategy Interface                           │
│  ┌─────────────────┐    ┌─────────────────────────────────────┐ │
│  │   BaseStrategy  │───►│ SignalGenerator Protocol           │ │
│  │   (Abstract)    │    │ - predict()                        │ │
│  │                 │    │ - train()                          │ │
│  └────────┬────────┘    └─────────────────────────────────────┘ │
│           │                                                      │
│  ┌────────▼────────┐    ┌─────────────────────────────────────┐ │
│  │ Strategy Config │    │ Position Management                 │ │
│  │ - thresholds    │    │ - calculate_position_size()        │ │
│  │ - tp/sl params  │    │ - validate_market_data()           │ │
│  └─────────────────┘    └─────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Strategy Registry                           │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  strategy_registry.create(name, **kwargs) -> Strategy     │  │
│  │  strategy_registry.list_strategies() -> dict              │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Quick Start

### Creating a Strategy

```python
from dgbit_core.trading.strategy import (
    BaseStrategy, StrategyMetadata, TradeDirection, SignalType,
    STRATEGY_REGISTRY, STRATEGY_FACTORY
)

# Or import from the full path
from dgbit_api.shared.python.dgbit_core.trading.strategy import (
    BaseStrategy, StrategyMetadata, TradeDirection, SignalType,
    STRATEGY_REGISTRY, STRATEGY_FACTORY
)

class MyCustomStrategy(BaseStrategy):
    """My custom trading strategy."""

    # Define metadata for the registry
    metadata = StrategyMetadata(
        name="my_custom",
        description="A custom momentum strategy",
        author="Your Name",
        version="0.1.0",
        signal_type=SignalType.MOMENTUM,
        default_direction=TradeDirection.LONG,
        parameters={
            "my_param": {
                "type": "float",
                "default": 1.0,
                "range": [0.0, 10.0],
                "description": "My custom parameter",
            },
        },
        requires_training=False,
    )

    def __init__(self, my_param: float = 1.0, **kwargs):
        super().__init__(**kwargs)
        self.my_param = my_param

    def generate_signal(self, data):
        """Generate trading signal from market data."""
        self.validate_market_data(data)

        # Your signal generation logic here
        close = data['close']

        # Example: Simple momentum
        momentum = close.pct_change(periods=5).iloc[-1]

        # Normalize to 0-1 range (higher = more bullish)
        signal = (momentum + 1) / 2
        return max(0.0, min(1.0, signal))

    def train(self, data):
        """Train the strategy if needed."""
        pass

# Register the strategy
STRATEGY_REGISTRY.register(MyCustomStrategy)
```

### Using Strategies

```python
from dgbit_core.trading.strategy import STRATEGY_REGISTRY, STRATEGY_FACTORY, list_strategies

# List all available strategies
strategies = list_strategies()
print("Available strategies:", list(strategies.keys()))
# Output: ['wavelet_reversal', 'ma_crossover', 'rsi', 'bollinger_bands', 'my_custom']

# Create a strategy instance
strategy = STRATEGY_FACTORY.create(
    name="my_custom",
    my_param=2.0,
    min_signal_threshold=0.6,
    take_profit_pct=0.005,
    stop_loss_pct=0.01,
)

# Use the strategy
should_enter, signal, direction = strategy.should_enter(market_data)
print(f"Should enter: {should_enter}, Signal: {signal}, Direction: {direction}")

# Get configuration
config = strategy.get_config()
print(config)
```

## Built-in Strategies

### 1. Wavelet Reversal Strategy

```python
# Create strategy
strategy = create_strategy(
    "wavelet_reversal",
    min_signal_threshold=0.75,
    take_profit_pct=0.002,
    stop_loss_pct=0.005,
)
```

**Parameters:**
- `min_signal_threshold`: Minimum signal value to enter trade (0.0-1.0, default: 0.75)
- `take_profit_pct`: Take profit as percentage (default: 0.002 = 0.2%)
- `stop_loss_pct`: Stop loss as percentage (default: 0.005 = 0.5%)

### 2. MA Crossover Strategy

```python
# Create strategy
strategy = create_strategy(
    "ma_crossover",
    fast_period=10,
    slow_period=20,
    ma_type="sma",  # or "ema", "wma"
    min_signal_threshold=0.55,
)
```

**Parameters:**
- `fast_period`: Fast MA period (default: 10)
- `slow_period`: Slow MA period (default: 20)
- `ma_type`: Moving average type (default: "sma")
- `min_signal_threshold`: Threshold for signal (default: 0.55)

### 3. RSI Strategy

```python
# Create strategy
strategy = create_strategy(
    "rsi",
    period=14,
    oversold=30.0,
    overbought=70.0,
    min_signal_threshold=0.3,
)
```

**Parameters:**
- `period`: RSI period (default: 14)
- `oversold`: Oversold threshold (default: 30.0)
- `overbought`: Overbought threshold (default: 70.0)
- `min_signal_threshold`: Signal threshold (default: 0.3)

### 4. Bollinger Bands Strategy

```python
# Create strategy
strategy = create_strategy(
    "bollinger_bands",
    period=20,
    std_dev=2.0,
    min_signal_threshold=0.3,
)
```

**Parameters:**
- `period`: MA period for bands (default: 20)
- `std_dev`: Standard deviation multiplier (default: 2.0)
- `min_signal_threshold`: Signal threshold (default: 0.3)

## Signal Types

Strategies can use different signal types for categorization:

- `SignalType.REVERSAL`: Detects trend reversals
- `SignalType.MOMENTUM`: Follows momentum trends
- `SignalType.MEAN_REVERSION`: Expects price to return to mean
- `SignalType.BREAKOUT`: Detects price breakouts
- `SignalType.CUSTOM`: Custom signal type

## Trade Directions

Strategies can specify default trade directions:

- `TradeDirection.LONG`: Long positions only
- `TradeDirection.SHORT`: Short positions only
- `TradeDirection.BOTH`: Can trade both directions

## Backtesting with Custom Strategies

```python
from dgbit_core.backtesting.backtester import Backtester, BacktestConfig
from dgbit_core.trading.strategy import STRATEGY_FACTORY

# Create strategy
strategy = STRATEGY_FACTORY.create("my_custom", min_signal_threshold=0.6)

# Configure backtest
config = BacktestConfig(
    initial_capital=10000.0,
    transaction_fee=0.001,
    train_split=0.7,
)

# Create backtester
backtester = Backtester(config=config)
backtester.strategy = strategy

# Run backtest
result = backtester.run(market_data)

# Get results
print(f"Win Rate: {result.metrics['win_rate']:.2%}")
print(f"Total Return: {result.metrics['total_return']:.2%}")
print(f"Number of Trades: {result.metrics['total_trades']}")
```

## Best Practices

1. **Use the registry**: Always register strategies with `STRATEGY_REGISTRY.register()`
2. **Define metadata**: Include clear descriptions and parameter schemas
3. **Validate input**: Use `validate_market_data()` before processing
4. **Return normalized signals**: Signals should be between 0.0 and 1.0
5. **Handle edge cases**: Return sensible defaults for insufficient data
6. **Document parameters**: Define clear parameter ranges and defaults
