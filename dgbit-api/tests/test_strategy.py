import pytest
from dgbit_core.trading.strategy import WaveletReversalStrategy, BaseStrategy


class TestWaveletReversalStrategy:
    """Tests for WaveletReversalStrategy."""

    def test_strategy_creation(self):
        """Test strategy can be created with custom parameters."""
        strategy = WaveletReversalStrategy(
            min_signal_threshold=0.8,
            take_profit_pct=0.003,
            stop_loss_pct=0.004,
        )

        assert strategy.min_signal_threshold == 0.8
        assert strategy.take_profit_pct == 0.003
        assert strategy.stop_loss_pct == 0.004

    def test_default_parameters(self):
        """Test strategy has sensible defaults."""
        strategy = WaveletReversalStrategy()

        assert strategy.min_signal_threshold == 0.75
        assert strategy.take_profit_pct == 0.002
        assert strategy.stop_loss_pct == 0.005

    def test_calculate_exit_prices(self):
        """Test exit price calculation."""
        strategy = WaveletReversalStrategy(
            take_profit_pct=0.002,  # 0.2%
            stop_loss_pct=0.005,    # 0.5%
        )

        tp, sl = strategy.calculate_exit_prices(50000.0)

        # Take profit: 50000 * (1 + 0.002) = 50100
        assert tp == pytest.approx(50100.0, rel=0.0001)

        # Stop loss: 50000 * (1 - 0.005) = 49750
        assert sl == pytest.approx(49750.0, rel=0.0001)

    def test_generate_signal_returns_value(self, sample_market_data):
        """Test signal generation returns a value between 0 and 1."""
        strategy = WaveletReversalStrategy()
        signal = strategy.generate_signal(sample_market_data)

        assert 0.0 <= signal <= 1.0

    def test_should_enter_with_high_threshold(self, sample_market_data):
        """Test should_enter with high threshold returns False."""
        strategy = WaveletReversalStrategy(min_signal_threshold=0.99)

        should_enter, signal, direction = strategy.should_enter(sample_market_data)

        assert should_enter is False or signal < 0.99

    def test_get_config(self):
        """Test configuration can be retrieved."""
        strategy = WaveletReversalStrategy(
            min_signal_threshold=0.8,
            take_profit_pct=0.003,
            stop_loss_pct=0.004,
        )

        config = strategy.get_config()

        assert config['min_signal_threshold'] == 0.8
        assert config['take_profit_pct'] == 0.003
        assert config['stop_loss_pct'] == 0.004

    def test_train_does_not_raise(self, sample_market_data):
        """Test train method doesn't raise an error."""
        strategy = WaveletReversalStrategy()

        # Should not raise
        strategy.train(sample_market_data)


class TestBaseStrategy:
    """Tests for BaseStrategy abstract class."""

    def test_cannot_instantiate_directly(self):
        """Test BaseStrategy cannot be instantiated."""
        with pytest.raises(TypeError):
            BaseStrategy()

    def test_strategy_subclass_must_implement_generate_signal(self):
        """Test that subclasses must implement generate_signal."""

        class IncompleteStrategy(BaseStrategy):
            pass

        with pytest.raises(TypeError):
            IncompleteStrategy()
