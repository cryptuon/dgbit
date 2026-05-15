# Built-in Strategies Reference

Reference for the four strategies that register themselves with `strategy_registry` on import.

`WaveletReversalStrategy` is defined in `dgbit_core.trading.strategy`. The other three live in `dgbit_core.trading.examples` and are re-exported by `dgbit_core.trading`. Registration happens at module import time, so a single `import dgbit_core.trading` is enough to populate the registry with all four entries.

## Wavelet Reversal Strategy

- Registry name: `wavelet_reversal`
- Class: `WaveletReversalStrategy`
- `metadata.signal_type`: `SignalType.REVERSAL`
- `metadata.default_direction`: `TradeDirection.LONG`

### Constructor

```python
WaveletReversalStrategy(
    min_signal_threshold: float = 0.75,
    take_profit_pct: float = 0.002,
    stop_loss_pct: float = 0.005,
    **kwargs,
)
```

### Signal logic

`generate_signal(data)` calls `PricePredictor().predict(data)`. The predictor:

1. Normalises the last 60 closes.
2. Decomposes them with the `db1` wavelet at level 3 (`pywt.wavedec`).
3. Combines the latest approximation slope and the share of detail energy in the highest-frequency band into a reversal probability.

`train()` is a no-op.

## MA Crossover Strategy

- Registry name: `ma_crossover`
- Class: `MACrossoverStrategy`
- `metadata.signal_type`: `SignalType.MOMENTUM`

### Constructor

```python
MACrossoverStrategy(
    fast_period: int = 10,
    slow_period: int = 20,
    ma_type: str = "sma",   # "sma", "ema", or "wma"
    **kwargs,
)
```

`metadata.parameters` declares ranges `fast_period: [2, 100]` and `slow_period: [5, 200]`.

### Signal logic

1. Compute fast and slow moving averages using `ma_type`.
2. Normalise the relative gap: `diff = (fast - slow) / slow`.
3. Map to `[0, 1]` with `signal = clamp(0.5 + diff * 10, 0.0, 1.0)`.

`train()` is a no-op.

## RSI Strategy

- Registry name: `rsi`
- Class: `RSIStrategy`
- `metadata.signal_type`: `SignalType.MEAN_REVERSION`

### Constructor

```python
RSIStrategy(
    period: int = 14,
    oversold: float = 30.0,
    overbought: float = 70.0,
    **kwargs,
)
```

### Signal logic

1. Compute RSI over `period` bars.
2. If `rsi <= oversold` return `0.0`; if `rsi >= overbought` return `1.0`; otherwise linearly interpolate between them.

So lower values mean "oversold / buy candidate" and higher values mean "overbought / sell candidate" — the opposite convention from the wavelet and Bollinger strategies. Compose accordingly.

## Bollinger Bands Strategy

- Registry name: `bollinger_bands`
- Class: `BollingerBandStrategy`
- `metadata.signal_type`: `SignalType.BREAKOUT`
- `metadata.default_direction`: `TradeDirection.BOTH`

### Constructor

```python
BollingerBandStrategy(
    period: int = 20,
    std_dev: float = 2.0,
    **kwargs,
)
```

The keyword is `std_dev`, not `num_std`. There is **no** `mode` parameter; the strategy reports the close's relative position within the bands.

### Signal logic

1. Compute the `period`-SMA (middle band) and rolling standard deviation.
2. Upper band = middle + `std_dev * std`, lower band = middle - `std_dev * std`.
3. Signal = clamp(`(close - lower) / (upper - lower)`, 0.0, 1.0); equal upper/lower bands return `0.5`.

## Registry helpers

```python
from dgbit_core.trading.strategy import (
    strategy_registry,
    create_strategy,
    list_available_strategies,
)

# All four built-ins after `import dgbit_core.trading`
names = list(list_available_strategies().keys())

strategy = create_strategy("ma_crossover", fast_period=8, slow_period=21)
schema = strategy_registry.get_params_schema("rsi")
```

`strategy_registry.register(cls)` raises `ValueError` if the metadata name is already taken.

## Combining strategies

There is no built-in composite strategy. Compose manually by calling `generate_signal` on each instance and combining the results. Note the inverted convention of the RSI strategy when doing so.
