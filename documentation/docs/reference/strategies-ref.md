# Built-in Strategies Reference

Detailed reference for all built-in trading strategies.

## Wavelet Reversal Strategy

**Name:** `wavelet_reversal`  
**Type:** Mean Reversion  
**Class:** `WaveletReversalStrategy`

### Description

Uses Daubechies wavelet decomposition to detect potential trend reversals. The strategy analyzes high-frequency detail coefficients to identify divergence patterns that often precede price reversals.

### Parameters

| Parameter | Type | Default | Range | Description |
|-----------|------|---------|-------|-------------|
| `min_signal_threshold` | float | `0.75` | 0.5-0.95 | Minimum signal strength to enter |
| `take_profit_pct` | float | `0.02` | 0.005-0.1 | Take profit percentage (2%) |
| `stop_loss_pct` | float | `0.01` | 0.003-0.05 | Stop loss percentage (1%) |
| `wavelet_level` | int | `3` | 1-5 | Wavelet decomposition level |
| `lookback_period` | int | `20` | 10-100 | Candles for analysis |

### Signal Logic

1. Decompose price series using Daubechies wavelet (db4)
2. Extract detail coefficients at specified level
3. Calculate divergence between price and wavelet reconstruction
4. Normalize to probability (0.0 to 1.0)

### Best Conditions

- Range-bound markets
- Low to medium volatility
- Sufficient liquidity

### Example

```python
from dgbit_core.trading.strategy import WaveletReversalStrategy

strategy = WaveletReversalStrategy(
    min_signal_threshold=0.80,
    take_profit_pct=0.015,
    stop_loss_pct=0.008,
    wavelet_level=3,
)
```

---

## MA Crossover Strategy

**Name:** `ma_crossover`  
**Type:** Trend Following  
**Class:** `MACrossoverStrategy`

### Description

Classic moving average crossover strategy using exponential moving averages (EMA). Generates buy signals when fast EMA crosses above slow EMA, sell signals on the opposite crossover.

### Parameters

| Parameter | Type | Default | Range | Description |
|-----------|------|---------|-------|-------------|
| `fast_period` | int | `12` | 5-50 | Fast EMA period |
| `slow_period` | int | `26` | 20-200 | Slow EMA period |
| `take_profit_pct` | float | `0.03` | 0.01-0.1 | Take profit percentage |
| `stop_loss_pct` | float | `0.015` | 0.005-0.05 | Stop loss percentage |

### Signal Logic

1. Calculate fast EMA (e.g., 12-period)
2. Calculate slow EMA (e.g., 26-period)
3. Buy signal: fast crosses above slow
4. Sell signal: fast crosses below slow
5. Signal strength based on crossover magnitude

### Best Conditions

- Trending markets
- Clear directional moves
- Lower timeframes for faster signals

### Example

```python
from dgbit_core.trading.strategy import MACrossoverStrategy

strategy = MACrossoverStrategy(
    fast_period=8,
    slow_period=21,
    take_profit_pct=0.025,
    stop_loss_pct=0.012,
)
```

---

## RSI Strategy

**Name:** `rsi`  
**Type:** Momentum  
**Class:** `RSIStrategy`

### Description

Relative Strength Index momentum strategy. Identifies overbought and oversold conditions to generate counter-trend signals.

### Parameters

| Parameter | Type | Default | Range | Description |
|-----------|------|---------|-------|-------------|
| `period` | int | `14` | 5-30 | RSI calculation period |
| `oversold` | int | `30` | 10-40 | Oversold threshold (buy) |
| `overbought` | int | `70` | 60-90 | Overbought threshold (sell) |
| `take_profit_pct` | float | `0.025` | 0.01-0.05 | Take profit percentage |
| `stop_loss_pct` | float | `0.012` | 0.005-0.03 | Stop loss percentage |

### Signal Logic

1. Calculate RSI over lookback period
2. RSI < oversold (30): Buy signal
3. RSI > overbought (70): Sell signal
4. Signal strength inversely proportional to RSI extremity

### Best Conditions

- Range-bound markets
- After extended moves (mean reversion expected)
- Higher timeframes for more reliable signals

### Example

```python
from dgbit_core.trading.strategy import RSIStrategy

strategy = RSIStrategy(
    period=14,
    oversold=25,
    overbought=75,
    take_profit_pct=0.02,
    stop_loss_pct=0.01,
)
```

---

## Bollinger Bands Strategy

**Name:** `bollinger_bands`  
**Type:** Volatility  
**Class:** `BollingerBandStrategy`

### Description

Uses Bollinger Bands to identify overbought/oversold conditions or breakout opportunities. Supports both mean reversion and breakout trading modes.

### Parameters

| Parameter | Type | Default | Range | Description |
|-----------|------|---------|-------|-------------|
| `period` | int | `20` | 10-50 | SMA period for middle band |
| `num_std` | float | `2.0` | 1.5-3.0 | Standard deviations for bands |
| `mode` | string | `mean_reversion` | - | Trading mode |
| `take_profit_pct` | float | `0.02` | 0.01-0.05 | Take profit percentage |
| `stop_loss_pct` | float | `0.01` | 0.005-0.03 | Stop loss percentage |

### Modes

**Mean Reversion (`mean_reversion`):**
- Buy when price touches lower band
- Sell when price touches upper band
- Targets middle band

**Breakout (`breakout`):**
- Buy when price breaks above upper band
- Sell when price breaks below lower band
- Targets continuation

### Signal Logic

1. Calculate 20-period SMA (middle band)
2. Calculate upper/lower bands (SMA ± 2 std)
3. Generate signals based on band touches/breaks
4. Signal strength based on distance from band

### Best Conditions

- Mean reversion: Range-bound, stable volatility
- Breakout: Consolidation before expansion
- Higher timeframes more reliable

### Example

```python
from dgbit_core.trading.strategy import BollingerBandStrategy

# Mean reversion mode
strategy = BollingerBandStrategy(
    period=20,
    num_std=2.0,
    mode="mean_reversion",
    take_profit_pct=0.02,
    stop_loss_pct=0.01,
)

# Breakout mode
strategy = BollingerBandStrategy(
    period=20,
    num_std=2.5,
    mode="breakout",
    take_profit_pct=0.04,
    stop_loss_pct=0.02,
)
```

---

## Strategy Comparison

| Strategy | Type | Win Rate* | Avg Return* | Best Market |
|----------|------|-----------|-------------|-------------|
| Wavelet Reversal | Mean Reversion | 55-65% | 0.8-1.2% | Range-bound |
| MA Crossover | Trend Following | 40-50% | 1.5-2.5% | Trending |
| RSI | Momentum | 50-60% | 0.6-1.0% | Range-bound |
| Bollinger Bands | Volatility | 45-55% | 1.0-1.8% | Variable |

*Approximate values; actual performance varies by market conditions.

## Combining Strategies

Example of combining multiple strategies:

```python
from dgbit_core.trading.strategy import (
    WaveletReversalStrategy,
    RSIStrategy,
)

wavelet = WaveletReversalStrategy()
rsi = RSIStrategy()

def combined_signal(data):
    w_signal = wavelet.generate_signal(data)
    r_signal = rsi.generate_signal(data)
    
    # Both must agree
    if w_signal > 0.7 and r_signal > 0.7:
        return (w_signal + r_signal) / 2
    elif w_signal < 0.3 and r_signal < 0.3:
        return (w_signal + r_signal) / 2
    else:
        return 0.5  # No clear signal
```
