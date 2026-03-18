"""
Data Service Client - Client for the Data Service

Provides a convenient interface for the API to communicate
with the Data Service via NNG.
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add parent to path
SRC_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(SRC_DIR))

import pynng
from loguru import logger

from dgbit_services import Message


class DataServiceClient:
    """Client for the Data Service."""

    DEFAULT_ADDRESS = "ipc:///tmp/dgbit_data.ipc"

    def __init__(self, address: str = None):
        self.address = address or self.DEFAULT_ADDRESS
        self._socket = None

    def _get_socket(self):
        """Get or create socket."""
        if self._socket is None:
            self._socket = pynng.Req0(dial=self.address, block=False)
            logger.info(f"Data service client connected to {self.address}")
        return self._socket

    def _send(self, command: str, payload: Dict = None) -> Dict:
        """Send a command and get response."""
        socket = self._get_socket()

        message = Message(
            command=command,
            payload=payload or {},
            source="data_client",
        )

        def _sync():
            socket.send(message.to_bytes())
            return socket.recv()

        loop = asyncio.new_event_loop()
        try:
            response = loop.run_in_executor(None, _sync)
            return json.loads(response.decode("utf-8"))
        finally:
            loop.close()

    async def get_klines(
        self,
        symbol: str = "BTCUSDT",
        exchange: str = "bybit",
        interval: str = "1",
        start_time: int = None,
        end_time: int = None,
        limit: int = 1000,
        use_cache: bool = True,
        force_refresh: bool = False,
    ) -> Dict:
        """Fetch kline data."""
        return self._send("GET_KLINES", {
            "symbol": symbol,
            "exchange": exchange,
            "interval": interval,
            "start_time": start_time,
            "end_time": end_time,
            "limit": limit,
            "use_cache": use_cache,
            "force_refresh": force_refresh,
        })

    def get_klines_sync(
        self,
        symbol: str = "BTCUSDT",
        exchange: str = "bybit",
        interval: str = "1",
        start_time: int = None,
        end_time: int = None,
        limit: int = 1000,
        use_cache: bool = True,
        force_refresh: bool = False,
    ) -> Dict:
        """Fetch kline data (synchronous wrapper)."""
        import asyncio
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(self.get_klines(
                symbol, exchange, interval, start_time, end_time,
                limit, use_cache, force_refresh
            ))
        finally:
            loop.close()

    async def get_symbols(self, exchange: str = "bybit") -> Dict:
        """Get available symbols."""
        return self._send("GET_SYMBOLS", {"exchange": exchange})

    async def get_tickers(self, exchange: str = "bybit") -> Dict:
        """Get market tickers."""
        return self._send("GET_TICKERS", {"exchange": exchange})

    async def backfill(
        self,
        symbol: str,
        exchange: str = "bybit",
        interval: str = "1",
        start_time: int = None,
        end_time: int = None,
        replace_existing: bool = False,
    ) -> Dict:
        """Trigger data backfill."""
        return self._send("BACKFILL", {
            "symbol": symbol,
            "exchange": exchange,
            "interval": interval,
            "start_time": start_time,
            "end_time": end_time,
            "replace_existing": replace_existing,
        })

    async def get_cache_status(self) -> Dict:
        """Get cache status."""
        return self._send("GET_CACHE_STATUS", {})

    async def clear_cache(self) -> Dict:
        """Clear the cache."""
        return self._send("CLEAR_CACHE", {})

    async def ping(self) -> Dict:
        """Ping the data service."""
        return self._send("ping", {})

    def close(self):
        """Close the client."""
        if self._socket:
            self._socket.close()
            self._socket = None


# =============================================================================
# Data API Routes Helper
# =============================================================================

class DataAPIHelper:
    """Helper class for data-related API routes."""

    def __init__(self, client: DataServiceClient = None):
        self._client = client

    @property
    def client(self) -> DataServiceClient:
        if self._client is None:
            self._client = DataServiceClient()
        return self._client

    async def get_market_data(
        self,
        symbol: str,
        interval: str = "1h",
        limit: int = 100,
    ) -> Dict:
        """
        Get market data for a symbol.

        Returns standardized market data suitable for strategies.
        """
        response = await self.client.get_klines(
            symbol=symbol,
            interval=interval,
            limit=limit,
            use_cache=True,
        )

        if response.get("success"):
            records = response.get("data", {}).get("records", [])
            # Convert to pandas-friendly format
            return {
                "symbol": symbol,
                "interval": interval,
                "data": [
                    {
                        "timestamp": r.get("start_time"),
                        "open": r.get("open"),
                        "high": r.get("high"),
                        "low": r.get("low"),
                        "close": r.get("close"),
                        "volume": r.get("volume"),
                        "turnover": r.get("turnover"),
                    }
                    for r in records
                ],
                "count": len(records),
            }

        return {"error": response.get("error", "Failed to fetch data")}

    async def get_available_symbols(self) -> List[str]:
        """Get list of available trading symbols."""
        response = await self.client.get_symbols()
        if response.get("success"):
            symbols = response.get("data", {}).get("symbols", [])
            return [s.get("symbol") for s in symbols if s.get("status") == "Trading"]
        return []

    async def get_cache_info(self) -> Dict:
        """Get cache statistics."""
        response = await self.client.get_cache_status()
        if response.get("success"):
            return response.get("data", {})
        return {}


# Global helper instance
_data_api_helper: Optional[DataAPIHelper] = None


def get_data_api_helper() -> DataAPIHelper:
    """Get the global data API helper."""
    global _data_api_helper
    if _data_api_helper is None:
        _data_api_helper = DataAPIHelper()
    return _data_api_helper
