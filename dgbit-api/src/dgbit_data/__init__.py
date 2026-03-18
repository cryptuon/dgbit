"""
dgbit Data Service

A standalone service for fetching, caching, and serving market data.

Usage:
    # Start the data service
    python -m dgbit_data.service --api-key YOUR_KEY --api-secret YOUR_SECRET

    # Use the client
    from dgbit_data.client import DataServiceClient

    client = DataServiceClient()
    klines = client.get_klines("BTCUSDT", "1")
"""

from dgbit_data.models import (
    KlineData,
    KlineBase,
    Interval,
    Exchange,
    DataSource,
    SymbolInfo,
    SymbolStatus,
    MarketSummary,
    CacheInfo,
    CacheStatus,
    GetKlinesRequest,
    BackfillRequest,
)

from dgbit_data.cache import CacheManager
from dgbit_data.adapters import (
    DataAdapter,
    BybitAdapter,
    AdapterFactory,
)

from dgbit_data.service import DataService
from dgbit_data.client import DataServiceClient, get_klines, get_symbols

__version__ = "0.1.0"

__all__ = [
    # Models
    "KlineData",
    "KlineBase",
    "Interval",
    "Exchange",
    "DataSource",
    "SymbolInfo",
    "SymbolStatus",
    "MarketSummary",
    "CacheInfo",
    "CacheStatus",
    "GetKlinesRequest",
    "BackfillRequest",
    # Cache
    "CacheManager",
    # Adapters
    "DataAdapter",
    "BybitAdapter",
    "AdapterFactory",
    # Service
    "DataService",
    "DataServiceClient",
    # Convenience
    "get_klines",
    "get_symbols",
]
