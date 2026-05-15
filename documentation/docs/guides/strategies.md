# Trading Strategies

dgbit ships four registered strategies and a framework for adding more.

The base strategy class (`BaseStrategy`) and `WaveletReversalStrategy` live in `dgbit_core.trading.strategy`. The three example strategies (`MACrossoverStrategy`, `RSIStrategy`, `BollingerBandStrategy`) live in `dgbit_core.trading.examples` and are re-exported from `dgbit_core.trading`.

## Built-in Strategies

### Wavelet Reversal Strategy

Registry name: `wavelet_reversal`. `generate_signal()` delegates to `dgbit_core.models.predictor.PricePredictor`, which performs a Daubechies wavelet decomposition.

```python
from dgbit_core.trading.strategy import WaveletReversalStrategy

# Constructor signature: (min_signal_threshold, take_profit_pct, stop_loss_pct, **kwargs)
strategy = WaveletReversalStrategy(
    min_signal_threshold=0.75,
    take_profit_pct=0.002,
    stop_loss_pct=0.005,
)
```

Extra keyword arguments are stored on `self._extra_params` but are not consumed by the strategy itself.

---

### MA Crossover Strategy

Registry name: `ma_crossover`. Uses SMA, EMA, or WMA depending on `ma_type` (default `"sma"`). The signal is a normalised, clamped function of the percentage gap between fast and slow MAs (above 0.5 = fast above slow).

```python
from dgbit_core.trading import MACrossoverStrategy

strategy = MACrossoverStrategy(
    fast_period=10,
    slow_period=20,
    ma_type="ema",   # one of: "sma", "ema", "wma"
)
```

---

### RSI Strategy

Registry name: `rsi`. Returns `0.0` when RSI <= `oversold`, `1.0` when RSI >= `overbought`, and a linear interpolation between them otherwise.

```python
from dgbit_core.trading import RSIStrategy

strategy = RSIStrategy(
    period=14,
    oversold=30.0,
    overbought=70.0,
)
```

---

### Bollinger Bands Strategy

Registry name: `bollinger_bands`. Computes the close price's relative position within a `period`-SMA Bollinger Band (with `std_dev` standard deviations). The signal is the clamped ratio `(close - lower) / (upper - lower)`. There is **no** separate `breakout` mode in the current implementation.

```python
from dgbit_core.trading import BollingerBandStrategy

strategy = BollingerBandStrategy(
    period=20,
    std_dev=2.0,
)
```

## Using Strategies

### With Backtesting

```python
from dgbit_core.backtesting import Backtester, BacktestConfig
from dgbit_core.trading.strategy import WaveletReversalStrategy
from dgbit_core.data.data_fetcher import BybitDataFetcher

fetcher = BybitDataFetcher(api_key="", api_secret="", testnet=True)
data = fetcher.get_kline_data("BTCUSDT", interval="15", limit=1000)

config = BacktestConfig(initial_capital=10000.0)
backtester = Backtester(config=config)
backtester.strategy = WaveletReversalStrategy()

result = backtester.run(data)
print(f"Win Rate: {result.metrics['win_rate']:.2%}")
```

### With the API

The `/api/strategies/{strategy_name}/signal` endpoint accepts only a `symbol` query parameter and proxies the request to the strategy service over NNG:

```python
import httpx

response = httpx.post(
    "http://localhost:8000/api/strategies/wavelet_reversal/signal",
    params={"symbol": "BTCUSDT"},
)
print(response.json())
```

The response shape is whatever the strategy service returns over the bus; consult `dgbit_services.strategy` for the current schema.

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

| Strategy | `SignalType` | Default direction | Notes |
|----------|--------------|-------------------|-------|
| Wavelet Reversal | `REVERSAL` | `LONG` | Wraps `PricePredictor` |
| MA Crossover | `MOMENTUM` | `LONG` | Configurable MA type |
| RSI | `MEAN_REVERSION` | `LONG` | Returns 0/1 at thresholds |
| Bollinger Bands | `BREAKOUT` | `BOTH` | Reports position within bands |

## Combining Strategies

You can combine signals from multiple strategies manually:

```python
from dgbit_core.trading import WaveletReversalStrategy, RSIStrategy

wavelet = WaveletReversalStrategy()
rsi = RSIStrategy()

wavelet_signal = wavelet.generate_signal(data)
rsi_signal = rsi.generate_signal(data)

# Note: RSI emits 0.0 at oversold and 1.0 at overbought, so the
# directional meaning of "agreement" depends on the strategy semantics.
combined_signal = (wavelet_signal + rsi_signal) / 2
```

## Next Steps

- [Backtesting Guide](backtesting.md) - Test strategy performance
- [Custom Strategies](custom-strategies.md) - Build your own
- [Strategy Reference](../reference/strategies-ref.md) - Complete parameter reference
