# Custom Strategies

Learn how to build your own trading strategies with dgbit's strategy framework.

## Strategy Architecture

All strategies inherit from `BaseStrategy` (defined in `dgbit_core.trading.strategy`). The framework exposes:

- `SignalType` enum with values: `REVERSAL`, `MOMENTUM`, `MEAN_REVERSION`, `BREAKOUT`, `CUSTOM`.
- `TradeDirection` enum with values: `LONG`, `SHORT`, `BOTH`.
- `StrategyMetadata` dataclass with fields `name`, `description`, `author`, `version`, `signal_type`, `default_direction`, `parameters`, and `requires_training`.

`BaseStrategy` provides concrete implementations of `should_enter`, `calculate_exit_prices`, `calculate_position_size`, and `validate_market_data`. Subclasses must implement `generate_signal(data) -> float` and may override `train(data)`.

The base constructor accepts `min_signal_threshold`, `take_profit_pct`, `stop_loss_pct`, and `position_size_pct`. Any subclass that adds its own constructor parameters should call `super().__init__(**kwargs)` to keep these in sync.

## Creating a Simple Strategy

### Example: MACD Strategy

```python
from dgbit_core.trading.strategy import (
    BaseStrategy,
    StrategyMetadata,
    SignalType,
    TradeDirection,
    strategy_registry,
)
import pandas as pd
import numpy as np

class MACDStrategy(BaseStrategy):
    """
    MACD (Moving Average Convergence Divergence) Strategy.
    
    Generates signals based on MACD line crossing the signal line.
    """
    
    metadata = StrategyMetadata(
        name="macd",
        description="MACD crossover strategy",
        author="Your Name",
        version="1.0.0",
        signal_type=SignalType.MOMENTUM,
        default_direction=TradeDirection.LONG,
        parameters={
            "fast_period": {"type": "int", "default": 12, "range": [5, 50]},
            "slow_period": {"type": "int", "default": 26, "range": [10, 100]},
            "signal_period": {"type": "int", "default": 9, "range": [3, 20]},
        },
    )

    def __init__(
        self,
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period
    
    def _calculate_ema(self, data: pd.Series, period: int) -> pd.Series:
        """Calculate Exponential Moving Average."""
        return data.ewm(span=period, adjust=False).mean()
    
    def _calculate_macd(self, data: pd.DataFrame) -> tuple[pd.Series, pd.Series, pd.Series]:
        """Calculate MACD, Signal line, and Histogram."""
        close = data['close']
        
        fast_ema = self._calculate_ema(close, self.fast_period)
        slow_ema = self._calculate_ema(close, self.slow_period)
        
        macd_line = fast_ema - slow_ema
        signal_line = self._calculate_ema(macd_line, self.signal_period)
        histogram = macd_line - signal_line
        
        return macd_line, signal_line, histogram
    
    def generate_signal(self, data: pd.DataFrame) -> float:
        """
        Generate signal based on MACD.
        
        Returns:
            float: Signal from 0.0 (strong sell) to 1.0 (strong buy)
        """
        if len(data) < self.slow_period + self.signal_period:
            return 0.5  # Not enough data, neutral
        
        macd, signal, histogram = self._calculate_macd(data)
        
        current_hist = histogram.iloc[-1]
        prev_hist = histogram.iloc[-2]
        
        # Normalize histogram to signal range
        hist_std = histogram.std()
        if hist_std == 0:
            return 0.5
        
        normalized = current_hist / (hist_std * 3)  # Scale to roughly -1 to 1
        
        # Check for crossover
        if prev_hist < 0 and current_hist > 0:
            # Bullish crossover
            return min(0.9, 0.7 + abs(normalized) * 0.2)
        elif prev_hist > 0 and current_hist < 0:
            # Bearish crossover
            return max(0.1, 0.3 - abs(normalized) * 0.2)
        
        # Convert to 0-1 range
        return np.clip(0.5 + normalized * 0.3, 0.0, 1.0)
    
    def should_enter(self, data: pd.DataFrame) -> tuple[bool, float, TradeDirection]:
        """Determine if should enter a position."""
        signal = self.generate_signal(data)
        
        if signal > 0.7:
            return True, signal, TradeDirection.LONG
        elif signal < 0.3:
            return True, signal, TradeDirection.SHORT
        
        return False, signal, TradeDirection.LONG
    
    def calculate_exit_prices(
        self, entry_price: float, direction: TradeDirection
    ) -> tuple[float, float]:
        """Calculate take profit and stop loss prices."""
        if direction == TradeDirection.LONG:
            take_profit = entry_price * (1 + self.take_profit_pct)
            stop_loss = entry_price * (1 - self.stop_loss_pct)
        else:
            take_profit = entry_price * (1 - self.take_profit_pct)
            stop_loss = entry_price * (1 + self.stop_loss_pct)
        
        return take_profit, stop_loss


# Register the strategy
strategy_registry.register(MACDStrategy)
```

### Using Your Strategy

```python
from dgbit_core.trading.strategy import strategy_registry
from dgbit_core.backtesting import Backtester, BacktestConfig

# Create via registry
strategy = strategy_registry.create("macd", fast_period=8, slow_period=21)

# Or instantiate directly
strategy = MACDStrategy(fast_period=8, slow_period=21)

# Use in backtesting
backtester = Backtester(config=BacktestConfig())
backtester.strategy = strategy
result = backtester.run(data)
```

## Advanced Techniques

### Machine Learning Strategy

```python
import numpy as np
from sklearn.ensemble import RandomForestClassifier

class MLStrategy(BaseStrategy):
    """Strategy using machine learning for signal generation."""
    
    metadata = StrategyMetadata(
        name="ml_random_forest",
        description="Random Forest classifier strategy",
        author="Your Name",
        version="1.0.0",
        signal_type=SignalType.CUSTOM,
        requires_training=True,
        parameters={
            "lookback": {"type": "int", "default": 20},
            "n_estimators": {"type": "int", "default": 100},
        },
    )

    def __init__(self, lookback: int = 20, n_estimators: int = 100, **kwargs):
        super().__init__(**kwargs)
        self.lookback = lookback
        self.n_estimators = n_estimators
        self.model = RandomForestClassifier(n_estimators=n_estimators)
        self.is_trained = False
    
    def _create_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """Create features for ML model."""
        features = pd.DataFrame(index=data.index)
        
        # Price-based features
        features['return_1'] = data['close'].pct_change(1)
        features['return_5'] = data['close'].pct_change(5)
        features['return_10'] = data['close'].pct_change(10)
        
        # Volatility
        features['volatility'] = data['close'].rolling(self.lookback).std()
        
        # Volume
        features['volume_sma'] = data['volume'].rolling(self.lookback).mean()
        features['volume_ratio'] = data['volume'] / features['volume_sma']
        
        # Technical indicators
        features['rsi'] = self._calculate_rsi(data['close'], 14)
        features['sma_ratio'] = data['close'] / data['close'].rolling(20).mean()
        
        return features.dropna()
    
    def _calculate_rsi(self, prices: pd.Series, period: int) -> pd.Series:
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    def train(self, data: pd.DataFrame) -> None:
        """Train the ML model."""
        features = self._create_features(data)
        
        # Create labels: 1 if price goes up in next period, 0 otherwise
        future_return = data['close'].shift(-1) / data['close'] - 1
        labels = (future_return > 0).astype(int)
        
        # Align features and labels
        common_idx = features.index.intersection(labels.dropna().index)
        X = features.loc[common_idx]
        y = labels.loc[common_idx]
        
        # Train model
        self.model.fit(X, y)
        self.is_trained = True
    
    def generate_signal(self, data: pd.DataFrame) -> float:
        if not self.is_trained:
            return 0.5
        
        features = self._create_features(data)
        if len(features) == 0:
            return 0.5
        
        # Get probability of price going up
        X = features.iloc[[-1]]
        prob = self.model.predict_proba(X)[0][1]
        
        return prob

strategy_registry.register(MLStrategy)
```

### Multi-Timeframe Strategy

```python
class MultiTimeframeStrategy(BaseStrategy):
    """Strategy that considers multiple timeframes."""
    
    metadata = StrategyMetadata(
        name="multi_timeframe",
        description="Multi-timeframe trend alignment strategy",
        author="Your Name",
        version="1.0.0",
        signal_type=SignalType.MOMENTUM,
        parameters={},
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def _resample_to_higher_tf(self, data: pd.DataFrame, factor: int) -> pd.DataFrame:
        """Resample data to higher timeframe."""
        resampled = data.groupby(data.index // factor).agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum',
        })
        return resampled
    
    def _get_trend(self, data: pd.DataFrame, period: int = 20) -> int:
        """Get trend direction: 1 (up), -1 (down), 0 (neutral)."""
        sma = data['close'].rolling(period).mean()
        current_price = data['close'].iloc[-1]
        sma_value = sma.iloc[-1]
        
        if current_price > sma_value * 1.01:
            return 1
        elif current_price < sma_value * 0.99:
            return -1
        return 0
    
    def generate_signal(self, data: pd.DataFrame) -> float:
        if len(data) < 100:
            return 0.5
        
        # Get trends at different timeframes
        tf1_trend = self._get_trend(data)  # Base timeframe
        
        tf4_data = self._resample_to_higher_tf(data, 4)
        tf4_trend = self._get_trend(tf4_data)
        
        tf16_data = self._resample_to_higher_tf(data, 16)
        tf16_trend = self._get_trend(tf16_data)
        
        # Combine signals
        total_trend = tf1_trend + tf4_trend * 1.5 + tf16_trend * 2
        
        # Normalize to 0-1
        signal = (total_trend + 4.5) / 9  # Range -4.5 to 4.5 -> 0 to 1
        
        return np.clip(signal, 0.0, 1.0)

strategy_registry.register(MultiTimeframeStrategy)
```

## Strategy Best Practices

### 1. Parameter Validation

```python
def __init__(self, period: int = 14, **kwargs):
    if period < 2:
        raise ValueError("Period must be at least 2")
    if period > 200:
        raise ValueError("Period too large, may cause issues")
    self.period = period
```

### 2. Handle Edge Cases

```python
def generate_signal(self, data: pd.DataFrame) -> float:
    # Not enough data
    if len(data) < self.min_required_candles:
        return 0.5
    
    # Handle NaN values
    if data['close'].isna().any():
        return 0.5
    
    # Actual calculation...
```

### 3. Document Parameters

```python
metadata = StrategyMetadata(
    name="my_strategy",
    description="Detailed description of how the strategy works",
    parameters={
        "period": {
            "type": "int",
            "default": 14,
            "min": 2,
            "max": 200,
            "description": "Lookback period for indicator calculation",
        },
    },
)
```

### 4. Write Tests

```python
import pytest
# MACDStrategy is the custom class defined above; adjust the import to wherever
# you placed it.
from my_strategies import MACDStrategy

def test_macd_signal_range():
    strategy = MACDStrategy()
    # Create sample data
    data = create_sample_data(100)

    signal = strategy.generate_signal(data)

    assert 0.0 <= signal <= 1.0

def test_macd_insufficient_data():
    strategy = MACDStrategy()
    data = create_sample_data(10)  # Not enough data
    
    signal = strategy.generate_signal(data)
    
    assert signal == 0.5  # Should return neutral
```

## Next Steps

- [Backtesting Guide](backtesting.md) - Test your custom strategy
- [Strategy Reference](../reference/strategies-ref.md) - See built-in implementations
- [Live Trading](live-trading.md) - Deploy your strategy
