"""
Data adapters for fetching market data from exchanges.

Each adapter implements a common interface for fetching klines,
symbols, and market data.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import pandas as pd
from loguru import logger

from dgbit_data.models import (
    KlineData, SymbolInfo, MarketSummary, Exchange, Interval, DataSource
)


class DataAdapter(ABC):
    """Abstract base class for data adapters."""

    def __init__(self, api_key: str = "", api_secret: str = "", testnet: bool = False):
        """
        Initialize adapter.

        Args:
            api_key: API key for authenticated requests
            api_secret: API secret for authenticated requests
            testnet: Use testnet instead of mainnet
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet

    @property
    @abstractmethod
    def exchange(self) -> Exchange:
        """Return the exchange this adapter supports."""
        ...

    @abstractmethod
    def get_klines(
        self,
        symbol: str,
        interval: Interval,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000,
    ) -> KlineData:
        """
        Fetch kline data.

        Args:
            symbol: Trading pair symbol (e.g., BTCUSDT)
            interval: Kline interval
            start_time: Start time (optional)
            end_time: End time (optional)
            limit: Maximum records to fetch

        Returns:
            KlineData with fetched data
        """
        ...

    @abstractmethod
    def get_symbols(self) -> List[SymbolInfo]:
        """Get list of available symbols."""
        ...

    @abstractmethod
    def get_market_summary(self, symbol: str) -> MarketSummary:
        """Get market summary for a symbol."""
        ...

    @abstractmethod
    def get_tickers(self) -> List[MarketSummary]:
        """Get tickers for all symbols."""
        ...

    def validate_symbol(self, symbol: str) -> bool:
        """Check if symbol exists on exchange."""
        try:
            symbols = self.get_symbols()
            return any(s.symbol == symbol.upper() for s in symbols)
        except Exception:
            return False


class BybitAdapter(DataAdapter):
    """Data adapter for Bybit exchange."""

    @property
    def exchange(self) -> Exchange:
        return Exchange.BYBIT

    def __init__(self, api_key: str = "", api_secret: str = "", testnet: bool = False):
        super().__init__(api_key, api_secret, testnet)
        self._session = None
        self._ws_session = None

    def _get_session(self):
        """Get or create HTTP session."""
        if self._session is None:
            from pybit.unified_trading import HTTP
            self._session = HTTP(
                testnet=self.testnet,
                api_key=self.api_key,
                api_secret=self.api_secret,
            )
        return self._session

    def get_klines(
        self,
        symbol: str,
        interval: Interval,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000,
    ) -> KlineData:
        """Fetch kline data from Bybit."""
        session = self._get_session()

        # Map interval to Bybit format
        interval_map = {
            Interval.M1: "1",
            Interval.M5: "5",
            Interval.M15: "15",
            Interval.M30: "30",
            Interval.H1: "60",
            Interval.H4: "240",
            Interval.D1: "D",
        }
        bybit_interval = interval_map.get(interval, "1")

        # Build request parameters
        params = {
            "category": "spot",
            "symbol": symbol.upper(),
            "interval": bybit_interval,
            "limit": min(limit, 1000),  # Bybit max is 1000
        }

        if start_time:
            params["start"] = int(start_time.timestamp() * 1000)
        if end_time:
            params["end"] = int(end_time.timestamp() * 1000)

        # Fetch data
        response = session.get_kline(**params)

        if "result" not in response or "list" not in response["result"]:
            raise ValueError(f"Invalid response from Bybit: {response}")

        raw_data = response["result"]["list"]

        # Convert to DataFrame
        df = pd.DataFrame(raw_data)
        df.columns = ["timestamp", "open", "high", "low", "close", "volume", "turnover"]
        df = df.astype(float)
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df = df.sort_values("timestamp").reset_index(drop=True)

        # Filter by time range if specified
        if start_time:
            df = df[df["timestamp"] >= start_time]
        if end_time:
            df = df[df["timestamp"] <= end_time]

        # Apply limit
        if len(df) > limit:
            df = df.tail(limit)

        # Create KlineData
        kline_data = KlineData.from_dataframe(
            df,
            symbol=symbol.upper(),
            exchange=self.exchange,
            interval=interval,
            source=DataSource.LIVE,
        )

        logger.debug(f"Fetched {len(df)} klines for {symbol} from Bybit")
        return kline_data

    def get_symbols(self) -> List[SymbolInfo]:
        """Get list of available symbols from Bybit."""
        session = self._get_session()
        response = session.get_symbols(category="spot")

        symbols = []
        for s in response.get("result", {}).get("list", []):
            symbols.append(SymbolInfo(
                symbol=s["symbol"],
                base_asset=s["baseCoin"],
                quote_asset=s["quoteCoin"],
                exchange=self.exchange,
                status=SymbolInfo.TradingStatus.TRADING if s["status"] == "Trading" else SymbolInfo.TradingStatus.BREAK,
                min_price=float(s["priceFilter"]["minPrice"]),
                max_price=float(s["priceFilter"]["maxPrice"]),
                min_quantity=float(s["lotSizeFilter"]["minOrderQty"]),
                max_quantity=float(s["lotSizeFilter"]["maxOrderQty"]),
                tick_size=float(s["priceFilter"]["tickSize"]),
                step_size=float(s["lotSizeFilter"]["qtyStep"]),
            ))

        return symbols

    def get_market_summary(self, symbol: str) -> MarketSummary:
        """Get market summary for a symbol."""
        session = self._get_session()
        response = session.get_tickers(category="spot", symbol=symbol.upper())

        ticker = response["result"]["list"][0]

        return MarketSummary(
            symbol=symbol.upper(),
            exchange=self.exchange,
            price_24h=float(ticker["price24h"]),
            price_24h_change_pct=float(ticker["price24hPcnt"]),
            volume_24h=float(ticker["volume24h"]),
            high_24h=float(ticker["highPrice24h"]),
            low_24h=float(ticker["lowPrice24h"]),
            bid_price=float(ticker["bid1Price"]),
            ask_price=float(ticker["ask1Price"]),
            last_update=datetime.utcnow(),
        )

    def get_tickers(self) -> List[MarketSummary]:
        """Get tickers for all symbols."""
        session = self._get_session()
        response = session.get_tickers(category="spot")

        tickers = []
        for t in response["result"]["list"]:
            tickers.append(MarketSummary(
                symbol=t["symbol"],
                exchange=self.exchange,
                price_24h=float(t["price24h"]),
                price_24h_change_pct=float(t["price24hPcnt"]),
                volume_24h=float(t["volume24h"]),
                high_24h=float(t["highPrice24h"]),
                low_24h=float(t["lowPrice24h"]),
                bid_price=float(t["bid1Price"]),
                ask_price=float(t["ask1Price"]),
                last_update=datetime.utcnow(),
            ))

        return tickers


class BinanceAdapter(DataAdapter):
    """Data adapter for Binance exchange (stub for future implementation)."""

    @property
    def exchange(self) -> Exchange:
        return Exchange.BINANCE

    def __init__(self, api_key: str = "", api_secret: str = "", testnet: bool = False):
        super().__init__(api_key, api_secret, testnet)
        # TODO: Implement Binance adapter
        logger.warning("Binance adapter not yet implemented")

    def get_klines(
        self,
        symbol: str,
        interval: Interval,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000,
    ) -> KlineData:
        raise NotImplementedError("Binance adapter not yet implemented")

    def get_symbols(self) -> List[SymbolInfo]:
        raise NotImplementedError("Binance adapter not yet implemented")

    def get_market_summary(self, symbol: str) -> MarketSummary:
        raise NotImplementedError("Binance adapter not yet implemented")

    def get_tickers(self) -> List[MarketSummary]:
        raise NotImplementedError("Binance adapter not yet implemented")


# =============================================================================
# Adapter Factory
# =============================================================================

class AdapterFactory:
    """Factory for creating data adapters."""

    _adapters: Dict[Exchange, type] = {
        Exchange.BYBIT: BybitAdapter,
        Exchange.BINANCE: BinanceAdapter,
    }

    @classmethod
    def create(
        cls,
        exchange: Exchange,
        api_key: str = "",
        api_secret: str = "",
        testnet: bool = False,
    ) -> DataAdapter:
        """Create an adapter for the specified exchange."""
        adapter_class = cls._adapters.get(exchange)
        if adapter_class is None:
            raise ValueError(f"Unsupported exchange: {exchange}")
        return adapter_class(api_key=api_key, api_secret=api_secret, testnet=testnet)

    @classmethod
    def register(cls, exchange: Exchange, adapter_class: type):
        """Register a new adapter for an exchange."""
        cls._adapters[exchange] = adapter_class

    @classmethod
    def supported_exchanges(cls) -> List[Exchange]:
        """List all supported exchanges."""
        return list(cls._adapters.keys())
