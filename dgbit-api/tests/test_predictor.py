import pytest
import numpy as np
import pandas as pd


class TestPricePredictor:
    """Tests for PricePredictor class."""

    def test_predictor_creation(self):
        """Test predictor can be created."""
        from dgbit_core.models.predictor import PricePredictor

        predictor = PricePredictor()

        assert predictor.wavelet == 'db1'
        assert predictor.level == 3
        assert predictor.window_size == 60

    def test_predict_returns_zero_for_short_data(self):
        """Test predict returns 0 for insufficient data."""
        from dgbit_core.models.predictor import PricePredictor

        predictor = PricePredictor()

        # Data shorter than window_size
        short_data = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=30, freq='1min'),
            'close': np.random.randn(30) * 100 + 50000,
        })

        result = predictor.predict(short_data)

        assert result == 0.0

    def test_predict_returns_value_for_sufficient_data(self, sample_market_data):
        """Test predict returns a value for sufficient data."""
        from dgbit_core.models.predictor import PricePredictor

        predictor = PricePredictor()
        result = predictor.predict(sample_market_data)

        assert 0.0 <= result <= 1.0

    def test_decompose_signal(self):
        """Test wavelet decomposition."""
        from dgbit_core.models.predictor import PricePredictor

        predictor = PricePredictor()

        # Create simple test signal
        test_signal = np.sin(np.linspace(0, 10, 100))

        approximation, details = predictor.decompose_signal(test_signal)

        assert isinstance(approximation, np.ndarray)
        assert isinstance(details, list)
        assert len(details) == predictor.level

    def test_train_does_nothing(self, sample_market_data):
        """Test train method exists but does nothing for wavelet-based predictor."""
        from dgbit_core.models.predictor import PricePredictor

        predictor = PricePredictor()

        # Should not raise
        predictor.train(sample_market_data)

    def test_detect_trend_change_with_insufficient_data(self):
        """Test trend change detection with insufficient data."""
        from dgbit_core.models.predictor import PricePredictor

        predictor = PricePredictor()

        # Very short arrays
        short_approx = np.array([1, 2, 3])
        short_details = [np.array([1, 2])]

        result = predictor.detect_trend_change(short_approx, short_details)

        assert result == 0.0
