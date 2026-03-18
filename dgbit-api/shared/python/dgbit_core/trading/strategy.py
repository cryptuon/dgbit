"""
Strategy Architecture for dgbit

This module provides a flexible, extensible trading strategy framework.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        Strategy Interface                        │
│  ┌─────────────────┐    ┌─────────────────────────────────────┐  │
│  │   BaseStrategy  │───►│ SignalGenerator (optional mixin)    │  │
│  │   (Abstract)    │    │ - generate_signal()                 │  │
│  │                 │    │ - train()                           │  │
│  └────────┬────────┘    └─────────────────────────────────────┘  │
│           │                                                       │
│  ┌────────▼────────┐    ┌─────────────────────────────────────┐  │
│  │ Strategy Config │───►│ RiskManager (optional mixin)        │  │
│  │ - thresholds    │    │ - calculate_position_size()         │  │
│  │ - tp/sl params  │    │ - validate_trade()                  │  │
│  └─────────────────┘    └─────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Strategy Registry                           │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  STRATEGY_REGISTRY[name] = StrategyClass                  │  │
│  │  STRATEGY_FACTORY.create(name, **kwargs) -> Strategy      │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Concrete Strategies                           │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────────────────┐ │
│  │ Wavelet...   │ │ MAStrategy   │ │ CustomStrategy (you!)     │ │
│  │ Strategy     │ │              │ │                          │ │
│  └──────────────┘ └──────────────┘ └──────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import (
    Tuple, Protocol, Dict, Any, Optional, Type, Callable,
    TypeVar, Generic
)
from enum import Enum
import pandas as pd


# Type variable for strategy instances
StrategyT = TypeVar("StrategyT", bound="BaseStrategy")


class SignalType(str, Enum):
    """Types of trading signals."""
    REVERSAL = "reversal"
    MOMENTUM = "momentum"
    MEAN_REVERSION = "mean_reversion"
    BREAKOUT = "breakout"
    CUSTOM = "custom"


class TradeDirection(str, Enum):
    """Trade direction."""
    LONG = "long"
    SHORT = "short"
    BOTH = "both"


@dataclass
class StrategyMetadata:
    """Metadata describing a strategy."""
    name: str
    description: str
    author: str = "dgbit"
    version: str = "0.1.0"
    signal_type: SignalType = SignalType.CUSTOM
    default_direction: TradeDirection = TradeDirection.LONG
    parameters: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    requires_training: bool = False


class SignalGenerator(Protocol):
    """Protocol for signal generation components.

    Strategies can compose different signal generators
    to create hybrid approaches.
    """

    def predict(self, data: pd.DataFrame) -> float:
        """
        Generate a signal value.

        Returns:
            float: Signal value (typically 0.0 to 1.0 for probabilities,
                   or -1.0 to 1.0 for directional signals)
        """
        ...

    def train(self, data: pd.DataFrame) -> None:
        """Train the signal model if needed."""
        ...


class BaseStrategy(ABC):
    """Abstract base class for trading strategies.

    To create a new strategy:
    1. Inherit from BaseStrategy
    2. Implement generate_signal()
    3. Optionally override train()
    4. Register with @strategy_registry
    """

    # Class-level metadata (override in subclasses)
    metadata: StrategyMetadata = StrategyMetadata(
        name="base_strategy",
        description="Abstract base strategy",
    )

    def __init__(
        self,
        min_signal_threshold: float = 0.5,
        take_profit_pct: float = 0.002,
        stop_loss_pct: float = 0.005,
        position_size_pct: float = 1.0,
        **kwargs,
    ):
        self.min_signal_threshold = min_signal_threshold
        self.take_profit_pct = take_profit_pct
        self.stop_loss_pct = stop_loss_pct
        self.position_size_pct = position_size_pct

        # Store any extra kwargs for custom parameters
        self._extra_params = kwargs

    @property
    def name(self) -> str:
        """Strategy name from metadata."""
        return self.metadata.name

    @abstractmethod
    def generate_signal(self, data: pd.DataFrame) -> float:
        """Generate trading signal from market data.

        Args:
            data: DataFrame with OHLCV columns and features

        Returns:
            float: Signal value (typically 0.0 to 1.0 for probabilities)
        """
        ...

    def train(self, data: pd.DataFrame) -> None:
        """Train the strategy if needed.

        Args:
            data: Historical market data for training
        """
        pass

    def should_enter(self, data: pd.DataFrame) -> Tuple[bool, float, TradeDirection]:
        """
        Determine if we should enter a trade.

        Args:
            data: Current market data

        Returns:
            Tuple of (should_enter, signal_value, direction)
        """
        signal_value = self.generate_signal(data)
        should_enter = signal_value > self.min_signal_threshold
        direction = self.metadata.default_direction
        return should_enter, signal_value, direction

    def calculate_exit_prices(
        self,
        entry_price: float,
        direction: TradeDirection = TradeDirection.LONG,
    ) -> Tuple[float, float]:
        """Calculate take profit and stop loss prices.

        Args:
            entry_price: The price at which we enter the trade
            direction: Trade direction (long or short)

        Returns:
            Tuple of (take_profit_price, stop_loss_price)
        """
        if direction == TradeDirection.LONG:
            take_profit_price = entry_price * (1 + self.take_profit_pct)
            stop_loss_price = entry_price * (1 - self.stop_loss_pct)
        else:  # SHORT
            take_profit_price = entry_price * (1 - self.take_profit_pct)
            stop_loss_price = entry_price * (1 + self.stop_loss_pct)

        return take_profit_price, stop_loss_price

    def calculate_position_size(
        self,
        capital: float,
        signal_confidence: float = 1.0,
    ) -> float:
        """Calculate position size based on capital and confidence.

        Args:
            capital: Available capital
            signal_confidence: Confidence in the signal (0.0 to 1.0)

        Returns:
            Position size in base currency
        """
        return capital * self.position_size_pct * signal_confidence

    def validate_market_data(self, data: pd.DataFrame) -> bool:
        """Validate that market data has required columns.

        Args:
            data: Market data to validate

        Returns:
            True if valid, raises ValueError if not
        """
        required = ['open', 'high', 'low', 'close', 'volume', 'timestamp']
        missing = [col for col in required if col not in data.columns]
        if missing:
            raise ValueError(f"Missing required columns: {missing}")
        return True

    def get_config(self) -> Dict[str, Any]:
        """Return strategy configuration for serialization."""
        return {
            "name": self.name,
            "version": self.metadata.version,
            "min_signal_threshold": self.min_signal_threshold,
            "take_profit_pct": self.take_profit_pct,
            "stop_loss_pct": self.stop_loss_pct,
            "position_size_pct": self.position_size_pct,
            "extra_params": self._extra_params,
        }

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.get_config()})"


class WaveletReversalStrategy(BaseStrategy):
    """Trading strategy using Daubechies wavelet-based reversal detection.

    This strategy analyzes price data using wavelet decomposition to detect
    potential trend reversals. It looks for patterns where high-frequency
    components suggest increasing volatility near trend changes.
    """

    metadata = StrategyMetadata(
        name="wavelet_reversal",
        description="Daubechies wavelet-based reversal detection strategy",
        author="dgbit",
        version="0.1.0",
        signal_type=SignalType.REVERSAL,
        default_direction=TradeDirection.LONG,
        parameters={
            "min_signal_threshold": {
                "type": "float",
                "default": 0.75,
                "range": [0.0, 1.0],
                "description": "Minimum signal value to enter trade",
            },
            "take_profit_pct": {
                "type": "float",
                "default": 0.002,
                "range": [0.0, 0.1],
                "description": "Take profit as percentage of entry",
            },
            "stop_loss_pct": {
                "type": "float",
                "default": 0.005,
                "range": [0.0, 0.2],
                "description": "Stop loss as percentage of entry",
            },
        },
        requires_training=False,
    )

    def __init__(
        self,
        min_signal_threshold: float = 0.75,
        take_profit_pct: float = 0.002,
        stop_loss_pct: float = 0.005,
        **kwargs,
    ):
        super().__init__(min_signal_threshold, take_profit_pct, stop_loss_pct, **kwargs)

    def generate_signal(self, data: pd.DataFrame) -> float:
        """Generate wavelet-based reversal signal."""
        self.validate_market_data(data)
        from dgbit_core.models.predictor import PricePredictor
        predictor = PricePredictor()
        return predictor.predict(data)

    def train(self, data: pd.DataFrame) -> None:
        """Train the underlying predictor (no-op for wavelet)."""
        pass


# =============================================================================
# Strategy Registry
# =============================================================================

class StrategyRegistry:
    """Registry for trading strategies with factory pattern."""

    def __init__(self):
        self._registry: Dict[str, Type[BaseStrategy]] = {}
        self._metadata: Dict[str, StrategyMetadata] = {}

    def register(self, strategy_class: Type[BaseStrategy]) -> Type[BaseStrategy]:
        """Register a strategy class.

        Args:
            strategy_class: A BaseStrategy subclass

        Returns:
            The same class (for use as decorator)
        """
        name = strategy_class.metadata.name
        if name in self._registry:
            raise ValueError(f"Strategy '{name}' is already registered")

        self._registry[name] = strategy_class
        self._metadata[name] = strategy_class.metadata
        return strategy_class

    def get(self, name: str) -> Optional[Type[BaseStrategy]]:
        """Get a strategy class by name."""
        return self._registry.get(name)

    def create(self, name: str, **kwargs) -> BaseStrategy:
        """Create a strategy instance by name.

        Args:
            name: Strategy name
            **kwargs: Strategy constructor arguments

        Returns:
            Configured strategy instance

        Raises:
            ValueError: If strategy not found
        """
        strategy_class = self._registry.get(name)
        if strategy_class is None:
            available = list(self._registry.keys())
            raise ValueError(
                f"Strategy '{name}' not found. Available: {available}"
            )
        return strategy_class(**kwargs)

    def list_strategies(self) -> Dict[str, StrategyMetadata]:
        """List all registered strategies with their metadata."""
        return self._metadata.copy()

    def get_params_schema(self, name: str) -> Dict[str, Any]:
        """Get the parameters schema for a strategy."""
        strategy_class = self._registry.get(name)
        if strategy_class is None:
            raise ValueError(f"Strategy '{name}' not found")
        return strategy_class.metadata.parameters


# Global registry instance
strategy_registry = StrategyRegistry()

# Decorator for easy registration
strategy_registry.register(WaveletReversalStrategy)


def create_strategy(name: str, **kwargs) -> BaseStrategy:
    """Factory function for creating strategies.

    Example:
        >>> strategy = create_strategy("wavelet_reversal", min_signal_threshold=0.8)
        >>> strategy = create_strategy("ma_crossover", fast_period=10, slow_period=20)
    """
    return strategy_registry.create(name, **kwargs)


def list_available_strategies() -> Dict[str, StrategyMetadata]:
    """List all available strategies."""
    return strategy_registry.list_strategies()


# Alias for backward compatibility
TradingStrategy = WaveletReversalStrategy
