import pytest
from dgbit_core.backtesting.backtester import Backtester, BacktestConfig, BacktestResult


class TestBacktester:
    """Tests for Backtester class."""

    def test_backtester_creation(self, sample_backtest_config):
        """Test backtester can be created with config."""
        backtester = Backtester(config=sample_backtest_config)

        assert backtester.config.initial_capital == 10000.0
        assert backtester.config.transaction_fee == 0.001
        assert backtester.capital == 10000.0

    def test_backtester_default_config(self):
        """Test backtester uses sensible defaults."""
        backtester = Backtester()

        assert backtester.config.initial_capital == 10000.0
        assert backtester.config.transaction_fee == 0.001
        assert backtester.config.train_split == 0.7

    def test_run_returns_result(self, sample_market_data, sample_backtest_config):
        """Test run method returns a BacktestResult."""
        backtester = Backtester(config=sample_backtest_config)

        result = backtester.run(sample_market_data)

        assert isinstance(result, BacktestResult)
        assert isinstance(result.trades, list)
        assert isinstance(result.equity_curve, list)
        assert isinstance(result.metrics, dict)

    def test_run_validates_columns(self, sample_backtest_config):
        """Test run validates required data columns."""
        backtester = Backtester(config=sample_backtest_config)

        # Missing required columns
        bad_data = __import__('pandas').DataFrame({'timestamp': [], 'close': []})

        with pytest.raises(ValueError, match="Missing required column"):
            backtester.run(bad_data)

    def test_metrics_contain_required_keys(self, sample_market_data, sample_backtest_config):
        """Test metrics contain all required keys."""
        backtester = Backtester(config=sample_backtest_config)

        result = backtester.run(sample_market_data)

        required_keys = [
            'total_trades', 'win_rate', 'avg_return', 'avg_duration',
            'final_capital', 'total_return', 'max_drawdown', 'profit_factor'
        ]

        for key in required_keys:
            assert key in result.metrics, f"Missing key: {key}"

    def test_final_capital_is_number(self, sample_market_data, sample_backtest_config):
        """Test final_capital is a valid number."""
        backtester = Backtester(config=sample_backtest_config)

        result = backtester.run(sample_market_data)

        assert isinstance(result.metrics['final_capital'], (int, float))
        assert result.metrics['final_capital'] > 0

    def test_win_rate_in_valid_range(self, sample_market_data, sample_backtest_config):
        """Test win_rate is between 0 and 1."""
        backtester = Backtester(config=sample_backtest_config)

        result = backtester.run(sample_market_data)

        assert 0.0 <= result.metrics['win_rate'] <= 1.0

    def test_equity_curve_has_timestamps(self, sample_market_data, sample_backtest_config):
        """Test equity curve contains timestamps and capital values."""
        backtester = Backtester(config=sample_backtest_config)

        result = backtester.run(sample_market_data)

        if len(result.equity_curve) > 0:
            first = result.equity_curve[0]
            assert 'timestamp' in first
            assert 'capital' in first

    def test_no_trades_possible_with_low_data(self, sample_backtest_config):
        """Test backtest with very little data."""
        import pandas as pd

        backtester = Backtester(config=sample_backtest_config)

        # Very small dataset
        small_data = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=50, freq='1min'),
            'open': [50000 + i * 10 for i in range(50)],
            'high': [50000 + i * 10 + 50 for i in range(50)],
            'low': [50000 + i * 10 - 50 for i in range(50)],
            'close': [50000 + i * 10 for i in range(50)],
            'volume': [1000] * 50,
        })

        result = backtester.run(small_data)

        # Should complete without error
        assert isinstance(result, BacktestResult)
        assert 'total_trades' in result.metrics


class TestBacktestConfig:
    """Tests for BacktestConfig."""

    def test_config_creation(self):
        """Test config can be created."""
        config = BacktestConfig(
            initial_capital=50000.0,
            transaction_fee=0.002,
            train_split=0.8,
        )

        assert config.initial_capital == 50000.0
        assert config.transaction_fee == 0.002
        assert config.train_split == 0.8

    def test_config_defaults(self):
        """Test config has sensible defaults."""
        config = BacktestConfig()

        assert config.initial_capital == 10000.0
        assert config.transaction_fee == 0.001
        assert config.train_split == 0.7
        assert config.report_dir == "reports"
