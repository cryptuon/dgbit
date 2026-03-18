"""
Example Strategies for dgbit

This module provides example strategies that demonstrate how to create
custom trading strategies for the dgbit platform.

## Quick Start: Creating a Custom Strategy

```python
from dgbit_core.trading.strategy import (
    BaseStrategy, StrategyMetadata, TradeDirection, SignalType,
    strategy_registry
)

class MyCustomStrategy(BaseStrategy):
    # Define strategy metadata
    metadata = StrategyMetadata(
        name="my_custom",
        description="My custom trading strategy",
        author="Your Name",
        version="0.1.0",
        signal_type=SignalType.MOMENTUM,
        default_direction=TradeDirection.LONG,
    )

    def __init__(self, my_param: float = 1.0, **kwargs):
        super().__init__(**kwargs)
        self.my_param = my_param

    def generate_signal(self, data):
        # Your signal generation logic here
        signal = ...  # 0.0 to 1.0
        return signal

# Register the strategy
strategy_registry.register(MyCustomStrategy)
```

## Available Example Strategies

1. MACrossoverStrategy - Moving Average crossover
2. RSIStrategy - RSI-based overbought/oversold
3. BollingerBandStrategy - Bollinger Bands breakout
"""

from typing import Tuple
import pandas as pd
import numpy as np

from dgbit_core.trading.strategy import (
    BaseStrategy, StrategyMetadata, TradeDirection, SignalType,
    strategy_registry
)


# =============================================================================
# Example 1: Moving Average Crossover Strategy
# =============================================================================

class MACrossoverStrategy(BaseStrategy):
    """Moving Average Crossover Strategy.

    This strategy generates signals based on the crossover of fast and slow
    moving averages. When the fast MA crosses above the slow MA, it signals
    a potential uptrend.

    Parameters:
        fast_period: Period for the fast MA (default: 10)
        slow_period: Period for the slow MA (default: 20)
        ma_type: Type of moving average ('sma', 'ema', 'wma') (default: 'sma')
    """

    metadata = StrategyMetadata(
        name="ma_crossover",
        description="Moving Average Crossover strategy",
        author="dgbit",
        version="0.1.0",
        signal_type=SignalType.MOMENTUM,
        default_direction=TradeDirection.LONG,
        parameters={
            "fast_period": {
                "type": "int",
                "default": 10,
                "range": [2, 100],
                "description": "Fast MA period",
            },
            "slow_period": {
                "type": "int",
                "default": 20,
                "range": [5, 200],
                "description": "Slow MA period",
            },
            "ma_type": {
                "type": "str",
                "default": "sma",
                "options": ["sma", "ema", "wma"],
                "description": "Moving average type",
            },
        },
        requires_training=False,
    )

    def __init__(
        self,
        fast_period: int = 10,
        slow_period: int = 20,
        ma_type: str = "sma",
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.ma_type = ma_type

    def _calculate_ma(self, series: pd.Series, period: int) -> pd.Series:
        """Calculate moving average based on type."""
        if self.ma_type == "sma":
            return series.rolling(period).mean()
        elif self.ma_type == "ema":
            return series.ewm(span=period, adjust=False).mean()
        elif self.ma_type == "wma":
            weights = np.arange(1, period + 1)
            return series.rolling(period).apply(
                lambda x: np.dot(x, weights) / weights.sum(), raw=True
            )
        else:
            return series.rolling(period).mean()

    def generate_signal(self, data: pd.DataFrame) -> float:
        """Generate MA crossover signal.

        Returns:
            float: Signal between 0 and 1
            - Values near 1: Fast MA well above slow MA (strong uptrend)
            - Values near 0: Fast MA well below slow MA (strong downtrend)
            - Values near 0.5: MAs are close together (uncertainty)
        """
        self.validate_market_data(data)

        close = data['close']

        fast_ma = self._calculate_ma(close, self.fast_period)
        slow_ma = self._calculate_ma(close, self.slow_period)

        # Get the latest values
        current_fast = fast_ma.iloc[-1]
        current_slow = slow_ma.iloc[-1]

        # Calculate normalized signal
        # Normalize by slow MA to get percentage difference
        diff = (current_fast - current_slow) / current_slow

        # Convert to 0-1 range with 0.5 as neutral
        signal = 0.5 + diff * 10  # Scale factor
        signal = max(0.0, min(1.0, signal))  # Clamp to 0-1

        return signal

    def train(self, data: pd.DataFrame) -> None:
        """No training needed for MA crossover."""
        pass

    def get_config(self) -> dict:
        """Return extended configuration."""
        config = super().get_config()
        config.update({
            "fast_period": self.fast_period,
            "slow_period": self.slow_period,
            "ma_type": self.ma_type,
        })
        return config


# Register the strategy
strategy_registry.register(MACrossoverStrategy)


# =============================================================================
# Example 2: RSI Strategy
# =============================================================================

class RSIStrategy(BaseStrategy):
    """RSI-based Overbought/Oversold Strategy.

    This strategy uses the Relative Strength Index to identify overbought
    and oversold conditions. Low RSI values suggest oversold (buy signal),
    high RSI values suggest overbought (sell signal).

    Parameters:
        period: RSI period (default: 14)
        oversold: Oversold threshold (default: 30)
        overbought: Overbought threshold (default: 70)
    """

    metadata = StrategyMetadata(
        name="rsi",
        description="RSI-based overbought/oversold strategy",
        author="dgbit",
        version="0.1.0",
        signal_type=SignalType.MEAN_REVERSION,
        default_direction=TradeDirection.LONG,
        parameters={
            "period": {
                "type": "int",
                "default": 14,
                "range": [2, 50],
                "description": "RSI period",
            },
            "oversold": {
                "type": "float",
                "default": 30.0,
                "range": [10, 40],
                "description": "Oversold threshold",
            },
            "overbought": {
                "type": "float",
                "default": 70.0,
                "range": [60, 90],
                "description": "Overbought threshold",
            },
        },
        requires_training=False,
    )

    def __init__(
        self,
        period: int = 14,
        oversold: float = 30.0,
        overbought: float = 70.0,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.period = period
        self.oversold = oversold
        self.overbought = overbought

    def _calculate_rsi(self, data: pd.DataFrame, period: int) -> pd.Series:
        """Calculate RSI series."""
        close = data['close']
        delta = close.diff()

        gain = delta.where(delta > 0, 0.0)
        loss = (-delta).where(delta < 0, 0.0)

        avg_gain = gain.rolling(period).mean()
        avg_loss = loss.rolling(period).mean()

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def generate_signal(self, data: pd.DataFrame) -> float:
        """Generate RSI signal.

        Returns:
            float: Signal between 0 and 1
            - Low values (< oversold): Strong buy signal (near 0)
            - High values (> overbought): Strong sell signal (near 1)
            - Values near 0.5: Neutral
        """
        self.validate_market_data(data)

        rsi = self._calculate_rsi(data, self.period)
        current_rsi = rsi.iloc[-1]

        # Convert RSI to signal (0 = oversold/bullish, 1 = overbought/bearish)
        if current_rsi <= self.oversold:
            return 0.0  # Strong buy signal
        elif current_rsi >= self.overbought:
            return 1.0  # Strong sell signal
        else:
            # Linear interpolation in the middle range
            return (current_rsi - self.oversold) / (self.overbought - self.oversold)

    def train(self, data: pd.DataFrame) -> None:
        """No training needed for RSI."""
        pass

    def get_config(self) -> dict:
        """Return extended configuration."""
        config = super().get_config()
        config.update({
            "period": self.period,
            "oversold": self.oversold,
            "overbought": self.overbought,
        })
        return config


# Register the strategy
strategy_registry.register(RSIStrategy)


# =============================================================================
# Example 3: Bollinger Bands Strategy
# =============================================================================

class BollingerBandStrategy(BaseStrategy):
    """Bollinger Bands Breakout Strategy.

    This strategy uses Bollinger Bands to identify price breakouts.
    When price touches the lower band, it's oversold (buy signal).
    When price touches the upper band, it's overbought (sell signal).

    Parameters:
        period: MA period for bands (default: 20)
        std_dev: Number of standard deviations (default: 2.0)
    """

    metadata = StrategyMetadata(
        name="bollinger_bands",
        description="Bollinger Bands breakout strategy",
        author="dgbit",
        version="0.1.0",
        signal_type=SignalType.BREAKOUT,
        default_direction=TradeDirection.BOTH,
        parameters={
            "period": {
                "type": "int",
                "default": 20,
                "range": [5, 100],
                "description": "MA period for bands",
            },
            "std_dev": {
                "type": "float",
                "default": 2.0,
                "range": [1.0, 3.0],
                "description": "Standard deviation multiplier",
            },
        },
        requires_training=False,
    )

    def __init__(
        self,
        period: int = 20,
        std_dev: float = 2.0,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.period = period
        self.std_dev = std_dev

    def generate_signal(self, data: pd.DataFrame) -> float:
        """Generate Bollinger Bands signal.

        Returns:
            float: Signal between 0 and 1
            - Near 0: Price at lower band (oversold)
            - Near 0.5: Price near middle band (neutral)
            - Near 1: Price at upper band (overbought)
        """
        self.validate_market_data(data)

        close = data['close']

        # Calculate Bollinger Bands
        middle = close.rolling(self.period).mean()
        std = close.rolling(self.period).std()
        upper = middle + (self.std_dev * std)
        lower = middle - (self.std_dev * std)

        current_close = close.iloc[-1]
        current_upper = upper.iloc[-1]
        current_lower = lower.iloc[-1]

        # Calculate position within bands (0 to 1)
        if current_upper == current_lower:
            return 0.5

        position = (current_close - current_lower) / (current_upper - current_lower)
        return max(0.0, min(1.0, position))

    def train(self, data: pd.DataFrame) -> None:
        """No training needed for Bollinger Bands."""
        pass

    def get_config(self) -> dict:
        """Return extended configuration."""
        config = super().get_config()
        config.update({
            "period": self.period,
            "std_dev": self.std_dev,
        })
        return config


# Register the strategy
strategy_registry.register(BollingerBandStrategy)


# =============================================================================
# Convenience Functions
# =============================================================================

def create_ma_strategy(fast_period: int = 10, slow_period: int = 20, **kwargs):
    """Create a Moving Average crossover strategy."""
    return MACrossoverStrategy(fast_period=fast_period, slow_period=slow_period, **kwargs)


def create_rsi_strategy(period: int = 14, oversold: float = 30.0, **kwargs):
    """Create an RSI strategy."""
    return RSIStrategy(period=period, oversold=oversold, **kwargs)


def create_bollinger_strategy(period: int = 20, std_dev: float = 2.0, **kwargs):
    """Create a Bollinger Bands strategy."""
    return BollingerBandStrategy(period=period, std_dev=std_dev, **kwargs)
