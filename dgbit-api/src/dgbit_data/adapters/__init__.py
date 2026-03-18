"""
Exchange Adapters

Provides a unified interface for accessing multiple cryptocurrency exchanges.
Each adapter implements a common interface, allowing seamless switching.

Supported Exchanges:
- Bybit (spot, futures) - using pybit
- Binance (spot, futures) - using ccxt
- Coinbase (spot) - using ccxt
- OKX (spot, futures) - using ccxt

Usage:
    from dgbit_data.adapters import AdapterFactory, Exchange

    # Create adapter
    adapter = AdapterFactory.create_data_adapter(
        exchange=Exchange.BINANCE,
        config=ExchangeConfig(api_key="...", api_secret="...")
    )

    # Fetch klines
    klines = adapter.get_klines("BTCUSDT", Interval.H1, limit=100)
"""

from .base import (
    DataAdapter,
    ExecutionAdapter,
    ExchangeConfig,
    KlineData,
    Kline,
    Ticker,
    Symbol,
    OrderBook,
    Order,
    Position,
    Trade,
    Exchange,
    Interval,
    Side,
    OrderType,
    OrderStatus,
    PositionSide,
)
from .bybit import BybitAdapter
from .binance import BinanceAdapter
from .coinbase import CoinbaseAdapter
from .okx import OKXAdapter
from .factory import AdapterFactory

__all__ = [
    # Base interfaces
    "DataAdapter",
    "ExecutionAdapter",
    "ExchangeConfig",
    "KlineData",
    "Kline",
    "Ticker",
    "Symbol",
    "OrderBook",
    "Order",
    "Position",
    "Trade",
    # Enums
    "Exchange",
    "Interval",
    "Side",
    "OrderType",
    "OrderStatus",
    "PositionSide",
    # Adapters
    "BybitAdapter",
    "BinanceAdapter",
    "CoinbaseAdapter",
    "OKXAdapter",
    # Factory
    "AdapterFactory",
]
