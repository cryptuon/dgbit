"""Tests for strategy registry and factory patterns."""

import pytest
from dgbit_core.trading.strategy import (
    BaseStrategy, StrategyMetadata, SignalType, TradeDirection,
    strategy_registry, create_strategy, list_available_strategies,
    WaveletReversalStrategy,
)
from dgbit_core.trading.examples import (
    MACrossoverStrategy, RSIStrategy, BollingerBandStrategy,
)


class TestStrategyRegistry:
    """Tests for StrategyRegistry."""

    def test_list_strategies(self):
        """Test listing available strategies."""
        strategies = list_available_strategies()

        assert isinstance(strategies, dict)
        assert len(strategies) >= 4  # wavelet, ma_crossover, rsi, bollinger

        # Check metadata structure
        for name, meta in strategies.items():
            assert isinstance(meta, StrategyMetadata)
            assert meta.name == name
            assert meta.description

    def test_create_wavelet_strategy(self):
        """Test creating wavelet reversal strategy."""
        strategy = create_strategy(
            "wavelet_reversal",
            min_signal_threshold=0.8,
            take_profit_pct=0.003,
        )

        assert strategy.name == "wavelet_reversal"
        assert strategy.min_signal_threshold == 0.8
        assert strategy.take_profit_pct == 0.003

    def test_create_ma_strategy(self):
        """Test creating MA crossover strategy."""
        strategy = create_strategy(
            "ma_crossover",
            fast_period=5,
            slow_period=15,
            ma_type="ema",
        )

        assert strategy.name == "ma_crossover"
        assert strategy.fast_period == 5
        assert strategy.slow_period == 15
        assert strategy.ma_type == "ema"

    def test_create_rsi_strategy(self):
        """Test creating RSI strategy."""
        strategy = create_strategy(
            "rsi",
            period=7,
            oversold=25.0,
            overbought=75.0,
        )

        assert strategy.name == "rsi"
        assert strategy.period == 7
        assert strategy.oversold == 25.0
        assert strategy.overbought == 75.0

    def test_create_bollinger_strategy(self):
        """Test creating Bollinger Bands strategy."""
        strategy = create_strategy(
            "bollinger_bands",
            period=30,
            std_dev=2.5,
        )

        assert strategy.name == "bollinger_bands"
        assert strategy.period == 30
        assert strategy.std_dev == 2.5

    def test_create_unknown_strategy_raises(self):
        """Test that creating unknown strategy raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            create_strategy("unknown_strategy")

        assert "not found" in str(exc_info.value).lower()
        assert "unknown_strategy" in str(exc_info.value)

    def test_get_params_schema(self):
        """Test getting parameters schema for a strategy."""
        schema = strategy_registry.get_params_schema("ma_crossover")

        assert "fast_period" in schema
        assert "slow_period" in schema
        assert schema["fast_period"]["type"] == "int"

    def test_get_unknown_params_schema_raises(self):
        """Test that getting schema for unknown strategy raises ValueError."""
        with pytest.raises(ValueError):
            strategy_registry.get_params_schema("nonexistent")


class TestStrategyMetadata:
    """Tests for StrategyMetadata."""

    def test_wavelet_metadata(self):
        """Test wavelet strategy metadata."""
        meta = WaveletReversalStrategy.metadata

        assert meta.name == "wavelet_reversal"
        assert meta.signal_type == SignalType.REVERSAL
        assert meta.default_direction == TradeDirection.LONG
        assert "min_signal_threshold" in meta.parameters

    def test_ma_metadata(self):
        """Test MA crossover strategy metadata."""
        meta = MACrossoverStrategy.metadata

        assert meta.name == "ma_crossover"
        assert meta.signal_type == SignalType.MOMENTUM
        assert meta.default_direction == TradeDirection.LONG
        assert "fast_period" in meta.parameters

    def test_rsi_metadata(self):
        """Test RSI strategy metadata."""
        meta = RSIStrategy.metadata

        assert meta.name == "rsi"
        assert meta.signal_type == SignalType.MEAN_REVERSION
        assert meta.default_direction == TradeDirection.LONG


class TestStrategyInterface:
    """Tests for strategy interface compliance."""

    def test_all_strategies_have_validate_method(self, sample_market_data):
        """Test all strategies can validate market data."""
        strategies = [
            create_strategy("wavelet_reversal"),
            create_strategy("ma_crossover"),
            create_strategy("rsi"),
            create_strategy("bollinger_bands"),
        ]

        for strategy in strategies:
            # Should not raise
            result = strategy.validate_market_data(sample_market_data)
            assert result is True

    def test_all_strategies_have_get_config(self):
        """Test all strategies return config."""
        strategies = [
            create_strategy("wavelet_reversal"),
            create_strategy("ma_crossover"),
            create_strategy("rsi"),
            create_strategy("bollinger_bands"),
        ]

        for strategy in strategies:
            config = strategy.get_config()
            assert isinstance(config, dict)
            assert "name" in config
            assert config["name"] == strategy.name

    def test_all_strategies_have_should_enter(self, sample_market_data):
        """Test all strategies implement should_enter."""
        strategies = [
            create_strategy("wavelet_reversal"),
            create_strategy("ma_crossover"),
            create_strategy("rsi"),
            create_strategy("bollinger_bands"),
        ]

        for strategy in strategies:
            result = strategy.should_enter(sample_market_data)
            # Handle both old (2-tuple) and new (3-tuple) interface
            if len(result) == 2:
                should_enter, signal = result
                direction = TradeDirection.LONG
            else:
                should_enter, signal, direction = result
            # Use bool() to convert numpy bool to Python bool
            should_enter_bool = bool(should_enter)
            assert isinstance(should_enter_bool, bool)
            assert isinstance(signal, (int, float))
            assert 0.0 <= signal <= 1.0
            assert direction in [TradeDirection.LONG, TradeDirection.SHORT, TradeDirection.BOTH]


class TestCustomStrategy:
    """Example of how to create and register a custom strategy."""

    def test_custom_strategy_registration(self):
        """Test creating and registering a custom strategy."""

        class CustomMomentumStrategy(BaseStrategy):
            metadata = StrategyMetadata(
                name="custom_momentum",
                description="A custom momentum strategy",
                author="Test",
                version="0.1.0",
                signal_type=SignalType.MOMENTUM,
            )

            def __init__(self, momentum_period: int = 5, **kwargs):
                super().__init__(**kwargs)
                self.momentum_period = momentum_period

            def generate_signal(self, data):
                self.validate_market_data(data)
                close = data['close']
                momentum = close.pct_change(periods=self.momentum_period)
                return float(momentum.iloc[-1] + 1) / 2  # Normalize to 0-1

        # Register the strategy
        strategy_registry.register(CustomMomentumStrategy)

        try:
            # Create an instance
            strategy = create_strategy(
                "custom_momentum",
                momentum_period=10,
                min_signal_threshold=0.6,
            )

            assert strategy.name == "custom_momentum"
            assert strategy.momentum_period == 10
        finally:
            # Clean up: remove the custom strategy
            strategy_registry._registry.pop("custom_momentum", None)
            strategy_registry._metadata.pop("custom_momentum", None)
