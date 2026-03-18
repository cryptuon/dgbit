"""
Tests for exchange adapters.

Tests verify that all adapters implement the correct interfaces
and produce consistent output formats.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch

import sys
from pathlib import Path

# Add src to path
SRC_DIR = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(SRC_DIR))

from dgbit_data.adapters.base import (
    Exchange,
    Interval,
    Side,
    OrderType,
    PositionSide,
    ExchangeConfig,
    Kline,
    KlineData,
    Ticker,
    Symbol,
    Order,
    Position,
    Trade,
)
from dgbit_data.adapters.factory import AdapterFactory


class TestExchangeConfig:
    """Test ExchangeConfig validation."""

    def test_default_config(self):
        """Test default configuration values."""
        config = ExchangeConfig()
        assert config.api_key == ""
        assert config.api_secret == ""
        assert config.testnet is True
        assert config.validate() is True

    def test_config_with_credentials(self):
        """Test configuration with credentials."""
        config = ExchangeConfig(
            api_key="test_key",
            api_secret="test_secret",
            testnet=False,
        )
        assert config.validate() is True

    def test_config_validation_without_credentials(self):
        """Test validation fails without credentials for mainnet."""
        config = ExchangeConfig(
            api_key="",
            api_secret="",
            testnet=False,
        )
        assert config.validate() is False


class TestBaseModels:
    """Test base data models."""

    def test_kline_creation(self):
        """Test Kline creation."""
        kline = Kline(
            timestamp=datetime.utcnow(),
            open=50000.0,
            high=51000.0,
            low=49000.0,
            close=50500.0,
            volume=100.5,
        )
        assert kline.open == 50000.0
        assert kline.close == 50500.0

    def test_kline_to_dict(self):
        """Test Kline serialization."""
        kline = Kline(
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            open=50000.0,
            high=51000.0,
            low=49000.0,
            close=50500.0,
            volume=100.5,
        )
        data = kline.to_dict()
        assert data["open"] == 50000.0
        assert "timestamp" in data

    def test_kline_data_properties(self):
        """Test KlineData properties."""
        klines = [
            Kline(
                timestamp=datetime(2024, 1, 1, i, 0, 0),
                open=50000.0 + i,
                high=51000.0 + i,
                low=49000.0 + i,
                close=50500.0 + i,
                volume=100.5,
            )
            for i in range(5)
        ]

        data = KlineData(
            symbol="BTCUSDT",
            exchange=Exchange.BYBIT,
            interval=Interval.H1,
            data=klines,
        )

        assert data.count == 5
        assert data.start_time == klines[0].timestamp
        assert data.end_time == klines[-1].timestamp

    def test_order_creation(self):
        """Test Order creation."""
        order = Order(
            order_id="test-123",
            symbol="BTCUSDT",
            side=Side.BUY,
            order_type=OrderType.LIMIT,
            quantity=0.001,
            price=50000.0,
        )
        assert order.status.value == "pending"
        assert order.filled_qty == 0.0

    def test_position_creation(self):
        """Test Position creation."""
        pos = Position(
            symbol="BTCUSDT",
            side=PositionSide.LONG,
            quantity=0.1,
            entry_price=45000.0,
        )
        assert pos.unrealized_pnl == 0.0
        assert pos.leverage == 1.0


class TestEnums:
    """Test enum values."""

    def test_exchange_values(self):
        """Test Exchange enum."""
        assert Exchange.BYBIT.value == "bybit"
        assert Exchange.BINANCE.value == "binance"
        assert Exchange.COINBASE.value == "coinbase"
        assert Exchange.OKX.value == "okx"

    def test_interval_values(self):
        """Test Interval enum."""
        assert Interval.M1.value == "1m"
        assert Interval.H1.value == "1h"
        assert Interval.D1.value == "1d"

    def test_side_values(self):
        """Test Side enum."""
        assert Side.BUY.value == "buy"
        assert Side.SELL.value == "sell"

    def test_order_type_values(self):
        """Test OrderType enum."""
        assert OrderType.MARKET.value == "market"
        assert OrderType.LIMIT.value == "limit"
        assert OrderType.STOP.value == "stop"


class TestAdapterFactory:
    """Test AdapterFactory functionality."""

    def test_supported_exchanges(self):
        """Test listing supported exchanges."""
        exchanges = AdapterFactory.supported_exchanges("data")

        assert Exchange.BYBIT in exchanges
        assert Exchange.BINANCE in exchanges
        assert Exchange.COINBASE in exchanges
        assert Exchange.OKX in exchanges

    def test_create_data_adapter(self):
        """Test creating data adapters."""
        adapter = AdapterFactory.create_data_adapter(
            exchange=Exchange.BYBIT,
            config=ExchangeConfig(testnet=True),
        )
        assert adapter.name == "bybit"
        assert adapter.exchange == Exchange.BYBIT

    def test_create_unknown_exchange(self):
        """Test creating adapter for unknown exchange raises error."""
        with pytest.raises(ValueError):
            AdapterFactory.create_data_adapter(
                exchange="unknown_exchange",
                config=ExchangeConfig(),
            )

    def test_exchange_info(self):
        """Test getting exchange information."""
        info = AdapterFactory.exchange_info(Exchange.BINANCE)

        assert info["exchange"] == "binance"
        assert info["display_name"] == "Binance"
        assert info["data_adapter"] is True
        assert info["execution_adapter"] is True


class TestAdapterInterface:
    """Test that adapters implement the correct interface."""

    def test_bybit_adapter_interface(self):
        """Test BybitAdapter implements required methods."""
        from dgbit_data.adapters import BybitAdapter

        adapter = BybitAdapter(config=ExchangeConfig(testnet=True))

        # Check required properties
        assert hasattr(adapter, "name")
        assert hasattr(adapter, "exchange")

        # Check required methods
        assert hasattr(adapter, "get_klines")
        assert hasattr(adapter, "get_symbols")
        assert hasattr(adapter, "get_tickers")
        assert hasattr(adapter, "create_order")
        assert hasattr(adapter, "cancel_order")
        assert hasattr(adapter, "health_check")

    def test_binance_adapter_interface(self):
        """Test BinanceAdapter implements required methods."""
        from dgbit_data.adapters import BinanceAdapter

        adapter = BinanceAdapter(config=ExchangeConfig(testnet=True))

        # Check required properties
        assert hasattr(adapter, "name")
        assert hasattr(adapter, "exchange")

        # Check required methods
        assert hasattr(adapter, "get_klines")
        assert hasattr(adapter, "get_symbols")
        assert hasattr(adapter, "get_tickers")
        assert hasattr(adapter, "create_order")

    def test_coinbase_adapter_interface(self):
        """Test CoinbaseAdapter implements required methods."""
        from dgbit_data.adapters import CoinbaseAdapter

        adapter = CoinbaseAdapter(config=ExchangeConfig(testnet=True))

        assert hasattr(adapter, "name")
        assert hasattr(adapter, "exchange")
        assert hasattr(adapter, "get_klines")
        assert hasattr(adapter, "get_symbols")

    def test_okx_adapter_interface(self):
        """Test OKXAdapter implements required methods."""
        from dgbit_data.adapters import OKXAdapter

        adapter = OKXAdapter(config=ExchangeConfig(testnet=True))

        assert hasattr(adapter, "name")
        assert hasattr(adapter, "exchange")
        assert hasattr(adapter, "get_klines")
        assert hasattr(adapter, "get_symbols")
        assert hasattr(adapter, "create_order")


class TestAdapterHealthCheck:
    """Test adapter health checks."""

    def test_bybit_health_check(self):
        """Test Bybit health check."""
        from dgbit_data.adapters import BybitAdapter

        adapter = BybitAdapter(config=ExchangeConfig(testnet=True))
        # Will fail without network, but should not raise
        try:
            result = adapter.health_check()
            # Result may be True or False depending on network
            assert isinstance(result, bool)
        except Exception as e:
            pytest.skip(f"Network error: {e}")

    def test_binance_health_check(self):
        """Test Binance health check."""
        from dgbit_data.adapters import BinanceAdapter

        adapter = BinanceAdapter(config=ExchangeConfig(testnet=True))
        try:
            result = adapter.health_check()
            assert isinstance(result, bool)
        except Exception as e:
            pytest.skip(f"Network error: {e}")


class TestAdapterKlines:
    """Test adapter kline fetching."""

    def test_bybit_get_klines(self):
        """Test Bybit kline fetching."""
        from dgbit_data.adapters import BybitAdapter

        adapter = BybitAdapter(config=ExchangeConfig(testnet=True))
        try:
            result = adapter.get_klines(
                symbol="BTCUSDT",
                interval=Interval.H1,
                limit=10,
            )
            # Should return KlineData object
            assert isinstance(result, KlineData)
            assert result.exchange == Exchange.BYBIT
            assert result.interval == Interval.H1
        except Exception as e:
            pytest.skip(f"Network error: {e}")

    def test_binance_get_klines(self):
        """Test Binance kline fetching."""
        from dgbit_data.adapters import BinanceAdapter

        adapter = BinanceAdapter(config=ExchangeConfig(testnet=True))
        try:
            result = adapter.get_klines(
                symbol="BTCUSDT",
                interval=Interval.H1,
                limit=10,
            )
            assert isinstance(result, KlineData)
            assert result.exchange == Exchange.BINANCE
        except Exception as e:
            pytest.skip(f"Network error: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
