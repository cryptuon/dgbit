"""
Trading module for dgbit.

This module provides:
- BaseStrategy: Abstract base class for trading strategies
- StrategyRegistry: Factory for creating strategy instances
- Concrete strategies: WaveletReversalStrategy, MACrossoverStrategy, RSIStrategy, BollingerBandStrategy

## Quick Start

```python
from dgbit_core.trading.strategy import (
    create_strategy, list_available_strategies
)

# List all available strategies
strategies = list_available_strategies()
print("Available strategies:", list(strategies.keys()))

# Create a strategy instance
strategy = create_strategy(
    name="ma_crossover",
    fast_period=10,
    slow_period=20,
    min_signal_threshold=0.6,
)
```

## Creating Custom Strategies

See `dgbit_core.trading.examples` for detailed examples.
"""

from dgbit_core.trading.strategy import (
    BaseStrategy,
    SignalGenerator,
    StrategyMetadata,
    SignalType,
    TradeDirection,
    WaveletReversalStrategy,
    TradingStrategy,
    strategy_registry,
    create_strategy,
    list_available_strategies,
)

from dgbit_core.trading.position import (
    Position,
    PositionSide,
    Order,
    OrderType,
    OrderStatus,
)

from dgbit_core.trading.examples import (
    MACrossoverStrategy,
    RSIStrategy,
    BollingerBandStrategy,
    create_ma_strategy,
    create_rsi_strategy,
    create_bollinger_strategy,
)

__all__ = [
    # Strategy framework
    "BaseStrategy",
    "SignalGenerator",
    "StrategyMetadata",
    "SignalType",
    "TradeDirection",
    "WaveletReversalStrategy",
    "TradingStrategy",
    "strategy_registry",
    "create_strategy",
    "list_available_strategies",
    # Position management
    "Position",
    "PositionSide",
    "Order",
    "OrderType",
    "OrderStatus",
    # Example strategies
    "MACrossoverStrategy",
    "RSIStrategy",
    "BollingerBandStrategy",
    "create_ma_strategy",
    "create_rsi_strategy",
    "create_bollinger_strategy",
]
