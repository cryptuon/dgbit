"""
Data fetcher for dgbit backtesting and live trading.

This module provides a unified interface for fetching market data
from either Bybit directly or through the Data Service.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, List, Protocol, Dict, Any
import pandas as pd
from loguru import logger


class DataSource(Protocol):
    """Protocol for data sources."""

    def fetch_klines(
        self,
        symbol: str,
        interval: str = "1",
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000,
    ) -> pd.DataFrame:
        """Fetch kline data."""
        ...

    def fetch_symbols(self) -> List[Dict[str, str]]:
        """Fetch available symbols."""
        ...

    def stream_klines(self, symbol: str, interval: str, callback):
        """Stream real-time klines."""
        ...


class BybitDataSource:
    """Direct Bybit data source using pybit."""

    def __init__(
        self,
        api_key: str = "",
        api_secret: str = "",
        testnet: bool = False,
    ):
        from pybit.unified_trading import HTTP
        self.session = HTTP(
            testnet=testnet,
            api_key=api_key,
            api_secret=api_secret,
        )

    def fetch_klines(
        self,
        symbol: str,
        interval: str = "1",
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000,
    ) -> pd.DataFrame:
        """Fetch kline data from Bybit."""
        params = {
            "category": "spot",
            "symbol": symbol,
            "interval": interval,
            "limit": min(limit, 1000),
        }

        if start_time:
            params["start"] = int(start_time.timestamp() * 1000)
        if end_time:
            params["end"] = int(end_time.timestamp() * 1000)

        response = self.session.get_kline(**params)

        if "result" not in response or "list" not in response["result"]:
            raise ValueError(f"Invalid Bybit response: {response}")

        df = pd.DataFrame(response["result"]["list"])
        df.columns = ["timestamp", "open", "high", "low", "close", "volume", "turnover"]
        df = df.astype(float)
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df = df.sort_values("timestamp").reset_index(drop=True)

        # Add features
        df['price_change'] = df['close'].pct_change()
        df['volume_change'] = df['volume'].pct_change()
        df['rolling_volatility'] = df['price_change'].rolling(10).std()
        df['rolling_volume'] = df['volume'].rolling(10).mean()

        return df

    def fetch_symbols(self) -> List[Dict[str, str]]:
        """Fetch available symbols from Bybit."""
        response = self.session.get_symbols(category="spot")
        return [
            {
                "symbol": s["symbol"],
                "base": s["baseCoin"],
                "quote": s["quoteCoin"],
            }
            for s in response.get("result", {}).get("list", [])
        ]

    def stream_klines(self, symbol: str, interval: str, callback):
        """Stream real-time klines."""
        from pybit.unified_trading import WebSocket

        ws = WebSocket(testnet=False, channel_type="spot")

        def handle_kline(message):
            data = message['data']
            kline_df = pd.DataFrame([{
                'timestamp': pd.to_datetime(data['timestamp'], unit='ms'),
                'open': float(data['open']),
                'high': float(data['high']),
                'low': float(data['low']),
                'close': float(data['close']),
                'volume': float(data['volume']),
                'turnover': float(data['turnover'])
            }])
            callback(kline_df)

        ws.kline_stream(symbol=symbol, interval=interval, callback=handle_kline)


class DataServiceDataSource:
    """Data source using the dgbit Data Service via NNG."""

    def __init__(
        self,
        address: str = "ipc:///tmp/dgbit_data.ipc",
        timeout_ms: int = 30000,
    ):
        """Initialize data service client."""
        self.address = address
        self.timeout_ms = timeout_ms
        self._socket = None

    def _get_socket(self):
        """Get or create NNG socket."""
        if self._socket is None:
            import pynng
            self._socket = pynng.Req0(dial=self.address, block=False)
        return self._socket

    def _send_request(self, command: str, payload: Dict[str, Any] = None) -> Dict[str, Any]:
        """Send request to data service."""
        import json
        socket = self._get_socket()

        request = {
            "command": command,
            "payload": payload or {},
            "request_id": __import__("uuid").uuid4().hex,
            "timestamp": datetime.utcnow().isoformat(),
        }

        def _send_recv():
            socket.send(json.dumps(request).encode("utf-8"))
            return socket.recv()

        loop = __import__("asyncio").new_event_loop()
        try:
            response = json.loads(loop.run_in_executor(None, _send_recv).decode("utf-8"))
            return response
        finally:
            loop.close()

    def fetch_klines(
        self,
        symbol: str,
        interval: str = "1",
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000,
    ) -> pd.DataFrame:
        """Fetch klines from data service."""
        payload = {
            "symbol": symbol,
            "interval": interval,
            "limit": limit,
            "use_cache": True,
            "force_refresh": False,
        }

        if start_time:
            payload["start_time"] = start_time.isoformat()
        if end_time:
            payload["end_time"] = end_time.isoformat()

        response = self._send_request("GET_KLINES", payload)

        if not response.get("success"):
            raise ValueError(f"Data service error: {response.get('error')}")

        data = response["data"]
        records = data["records"]

        if not records:
            return pd.DataFrame(columns=[
                "timestamp", "open", "high", "low", "close", "volume", "turnover"
            ])

        # Convert to DataFrame
        df = pd.DataFrame(records)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values("timestamp").reset_index(drop=True)

        # Add features
        df['price_change'] = df['close'].pct_change()
        df['volume_change'] = df['volume'].pct_change()
        df['rolling_volatility'] = df['price_change'].rolling(10).std()
        df['rolling_volume'] = df['volume'].rolling(10).mean()

        logger.debug(f"Fetched {len(df)} klines from data service")
        return df

    def fetch_symbols(self) -> List[Dict[str, str]]:
        """Fetch symbols from data service."""
        response = self._send_request("GET_SYMBOLS", {"exchange": "bybit"})
        if not response.get("success"):
            raise ValueError(f"Data service error: {response.get('error')}")
        return response["data"]["symbols"]

    def stream_klines(self, symbol: str, interval: str, callback):
        """Stream is not supported via NNG. Use BybitDataSource instead."""
        raise NotImplementedError("Streaming not supported via Data Service. Use BybitDataSource.")


@dataclass
class DataFetcherConfig:
    """Configuration for data fetching."""
    source_type: str = "bybit"  # "bybit" or "service"
    service_address: str = "ipc:///tmp/dgbit_data.ipc"
    api_key: str = ""
    api_secret: str = ""
    testnet: bool = False
    default_symbol: str = "BTCUSDT"
    default_interval: str = "1"


class DataFetcher:
    """
    Unified data fetcher that can use either direct Bybit or Data Service.

    Example:
        # Use direct Bybit
        fetcher = DataFetcher(source_type="bybit", api_key="...", api_secret="...")

        # Use data service
        fetcher = DataFetcher(source_type="service")

        df = fetcher.get_klines("BTCUSDT", limit=500)
    """

    def __init__(self, config: Optional[DataFetcherConfig] = None):
        """Initialize data fetcher."""
        self.config = config or DataFetcherConfig()

        if self.config.source_type == "service":
            self.source = DataServiceDataSource(
                address=self.config.service_address,
            )
        else:
            self.source = BybitDataSource(
                api_key=self.config.api_key,
                api_secret=self.config.api_secret,
                testnet=self.config.testnet,
            )

    def get_klines(
        self,
        symbol: Optional[str] = None,
        interval: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000,
    ) -> pd.DataFrame:
        """
        Get kline data.

        Args:
            symbol: Trading pair (uses default if not specified)
            interval: Kline interval (uses default if not specified)
            start_time: Start time
            end_time: End time
            limit: Maximum records

        Returns:
            DataFrame with OHLCV data and features
        """
        symbol = symbol or self.config.default_symbol
        interval = interval or self.config.default_interval

        return self.source.fetch_klines(
            symbol=symbol,
            interval=interval,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
        )

    def get_volatile_pairs(
        self,
        min_volume: float = 1000000,
        min_change: float = 0.05,
    ) -> List[str]:
        """Find volatile pairs meeting criteria."""
        tickers = self.source.fetch_symbols()

        volatile = []
        for ticker in tickers:
            # This is a simplified version - full implementation would
            # use market summary data
            if float(ticker.get("volume24h", 0)) > min_volume:
                volatile.append(ticker["symbol"])

        return volatile

    def stream_klines(self, symbol: str, interval: str, callback):
        """Stream real-time klines."""
        self.source.stream_klines(symbol, interval, callback)


# Backward compatibility
class BybitDataFetcher(BybitDataSource):
    """Backward-compatible wrapper for BybitDataFetcher."""

    def __init__(self, api_key: str = "", api_secret: str = "", testnet: bool = False):
        super().__init__(api_key=api_key, api_secret=api_secret, testnet=testnet)

    def get_kline_data(
        self,
        symbol: str,
        interval: str = "1",
        lookback_hours: int = 24,
        limit: int = 1000,
    ) -> pd.DataFrame:
        """Get kline data (backward-compatible method)."""
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=lookback_hours)

        return self.fetch_klines(
            symbol=symbol,
            interval=interval,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
        )
