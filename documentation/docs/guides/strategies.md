# Trading Strategies

dgbit includes several built-in trading strategies and provides a framework for creating custom ones.

## Built-in Strategies

### Wavelet Reversal Strategy

The flagship strategy uses Daubechies wavelet decomposition to detect potential trend reversals.

**How it works:**

1. Decomposes price data using wavelet transform
2. Analyzes high-frequency detail coefficients
3. Detects divergence indicating potential reversal
4. Generates signal strength (0.0 to 1.0)

```python
from dgbit_core.trading.strategy import WaveletReversalStrategy

strategy = WaveletReversalStrategy(
    min_signal_threshold=0.75,  # Enter only on strong signals
    take_profit_pct=0.02,       # 2% take profit
    stop_loss_pct=0.01,         # 1% stop loss
    wavelet_level=3,            # Decomposition level
)
```

**Best for:** Range-bound markets, mean reversion

---

### MA Crossover Strategy

Classic moving average crossover strategy using fast and slow EMAs.

**How it works:**

1. Calculates fast EMA (e.g., 12 periods)
2. Calculates slow EMA (e.g., 26 periods)
3. Generates buy signal when fast crosses above slow
4. Generates sell signal when fast crosses below slow

```python
from dgbit_core.trading.strategy import MACrossoverStrategy

strategy = MACrossoverStrategy(
    fast_period=12,
    slow_period=26,
    take_profit_pct=0.03,
    stop_loss_pct=0.015,
)
```

**Best for:** Trending markets

---

### RSI Strategy

Relative Strength Index momentum strategy.

**How it works:**

1. Calculates RSI over lookback period
2. Buy signal when RSI < oversold threshold (e.g., 30)
3. Sell signal when RSI > overbought threshold (e.g., 70)

```python
from dgbit_core.trading.strategy import RSIStrategy

strategy = RSIStrategy(
    period=14,
    oversold=30,
    overbought=70,
    take_profit_pct=0.025,
    stop_loss_pct=0.012,
)
```

**Best for:** Range-bound markets, counter-trend trading

---

### Bollinger Bands Strategy

Volatility-based breakout strategy.

**How it works:**

1. Calculates Bollinger Bands (middle, upper, lower)
2. Buy signal when price touches lower band
3. Sell signal when price touches upper band
4. Can also trade breakouts above/below bands

```python
from dgbit_core.trading.strategy import BollingerBandStrategy

strategy = BollingerBandStrategy(
    period=20,
    num_std=2.0,
    mode="mean_reversion",  # or "breakout"
    take_profit_pct=0.02,
    stop_loss_pct=0.01,
)
```

**Best for:** High volatility markets

## Using Strategies

### With Backtesting

```python
from dgbit_core.backtesting import Backtester, BacktestConfig
from dgbit_core.trading.strategy import WaveletReversalStrategy
from dgbit_core.data.data_fetcher import BybitDataFetcher

# Fetch data
fetcher = BybitDataFetcher()
data = fetcher.get_kline_data("BTCUSDT", interval="15", limit=1000)

# Create backtester
config = BacktestConfig(initial_capital=10000.0)
backtester = Backtester(config=config)
backtester.strategy = WaveletReversalStrategy()

# Run backtest
result = backtester.run(data)
print(f"Win Rate: {result.metrics['win_rate']:.2%}")
```

### With the API

```python
import httpx

# Generate a signal
response = httpx.post(
    "http://localhost:8000/api/strategies/wavelet_reversal/signal",
    json={
        "symbol": "BTCUSDT",
        "interval": "15",
        "limit": 100,
    }
)

signal = response.json()
print(f"Signal strength: {signal['value']}")
print(f"Direction: {signal['direction']}")
```

### Strategy Registry

All strategies are registered in the global registry:

```python
from dgbit_core.trading.strategy import strategy_registry

# List all available strategies
strategies = strategy_registry.list_strategies()
for name, metadata in strategies.items():
    print(f"{name}: {metadata.description}")

# Create a strategy by name
strategy = strategy_registry.create(
    "wavelet_reversal",
    min_signal_threshold=0.8
)
```

## Strategy Comparison

| Strategy | Type | Best Market | Risk Level |
|----------|------|-------------|------------|
| Wavelet Reversal | Mean Reversion | Range-bound | Medium |
| MA Crossover | Trend Following | Trending | Low |
| RSI | Momentum | Range-bound | Medium |
| Bollinger Bands | Volatility | High Volatility | Medium-High |

## Combining Strategies

You can combine signals from multiple strategies:

```python
from dgbit_core.trading.strategy import (
    WaveletReversalStrategy,
    RSIStrategy,
    strategy_registry,
)

# Create strategies
wavelet = WaveletReversalStrategy()
rsi = RSIStrategy()

# Generate signals
wavelet_signal = wavelet.generate_signal(data)
rsi_signal = rsi.generate_signal(data)

# Combine signals (example: average)
combined_signal = (wavelet_signal + rsi_signal) / 2

# Or require agreement
if wavelet_signal > 0.7 and rsi_signal > 0.7:
    print("Strong buy signal from both strategies")
```

## Next Steps

- [Backtesting Guide](backtesting.md) - Test strategy performance
- [Custom Strategies](custom-strategies.md) - Build your own
- [Strategy Reference](../reference/strategies-ref.md) - Complete parameter reference
