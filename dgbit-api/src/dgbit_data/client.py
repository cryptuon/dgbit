"""
NNG Client for the dgbit Data Service.

Provides a convenient interface for other services to fetch market data.
"""

import asyncio
import json
from datetime import datetime
from typing import Any, Dict, Optional, List
from pathlib import Path
import sys

# Add parent directories to path
SRC_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(SRC_DIR))

import pynng
from loguru import logger

from dgbit_data.models import (
    KlineData, ServiceRequest, ServiceResponse, Exchange, Interval
)


class DataServiceClient:
    """
    Client for communicating with the Data Service via NNG.

    Example:
        client = DataServiceClient()
        klines = client.get_klines("BTCUSDT", "1")
        symbols = client.get_symbols()
    """

    def __init__(
        self,
        address: str = "ipc:///tmp/dgbit_data.ipc",
        timeout_ms: int = 30000,
    ):
        """
        Initialize client.

        Args:
            address: NNG address of the data service
            timeout_ms: Request timeout in milliseconds
        """
        self.address = address
        self.timeout_ms = timeout_ms
        self._socket: Optional[pynng.Req0] = None

    def _get_socket(self) -> pynng.Req0:
        """Get or create socket."""
        if self._socket is None:
            self._socket = pynng.Req0(dial=self.address, block=False)
        return self._socket

    def _send_request(self, command: str, payload: Dict[str, Any] = None) -> Dict[str, Any]:
        """Send a request to the data service."""
        socket = self._get_socket()

        request = ServiceRequest(
            command=command,
            payload=payload or {},
        )

        data = json.dumps(request.model_dump()).encode("utf-8")

        def _send_recv():
            socket.send(data)
            return socket.recv()

        loop = asyncio.new_event_loop()
        try:
            response_bytes = loop.run_in_executor(None, _send_recv)
            response_dict = json.loads(response_bytes.decode("utf-8"))
            return response_dict
        finally:
            loop.close()

    def close(self):
        """Close the connection."""
        if self._socket:
            self._socket.close()
            self._socket = None

    def get_klines(
        self,
        symbol: str,
        interval: str = "1",
        exchange: str = "bybit",
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000,
        use_cache: bool = True,
        force_refresh: bool = False,
    ) -> KlineData:
        """
        Fetch kline data.

        Args:
            symbol: Trading pair symbol (e.g., BTCUSDT)
            interval: Kline interval (1, 5, 15, 60, etc.)
            exchange: Exchange name
            start_time: Start time
            end_time: End time
            limit: Maximum records
            use_cache: Use cached data if available
            force_refresh: Force refresh from exchange

        Returns:
            KlineData object
        """
        payload = {
            "symbol": symbol,
            "interval": interval,
            "exchange": exchange,
            "limit": limit,
            "use_cache": use_cache,
            "force_refresh": force_refresh,
        }

        if start_time:
            payload["start_time"] = start_time.isoformat()
        if end_time:
            payload["end_time"] = end_time.isoformat()

        response = self._send_request("GET_KLINES", payload)

        if not response.get("success"):
            raise ValueError(f"Failed to get klines: {response.get('error')}")

        data = response["data"]

        # Convert records back to KlineBase objects
        from dgbit_data.models import KlineBase

        klines = [
            KlineBase(
                timestamp=datetime.fromisoformat(r["timestamp"]),
                open=r["open"],
                high=r["high"],
                low=r["low"],
                close=r["close"],
                volume=r["volume"],
                turnover=r.get("turnover", 0.0),
            )
            for r in data["records"]
        ]

        return KlineData(
            symbol=data["symbol"],
            exchange=Exchange(data["exchange"]),
            interval=Interval(data["interval"]),
            start_time=datetime.fromisoformat(data["start_time"]),
            end_time=datetime.fromisoformat(data["end_time"]),
            count=data["count"],
            data=klines,
            source=__import__("dgbit_data.models", fromlist=["DataSource"]).DataSource(data["source"]),
        )

    def get_symbols(self, exchange: str = "bybit") -> List[Dict[str, Any]]:
        """Get list of available symbols."""
        response = self._send_request("GET_SYMBOLS", {"exchange": exchange})

        if not response.get("success"):
            raise ValueError(f"Failed to get symbols: {response.get('error')}")

        return response["data"]["symbols"]

    def get_tickers(self, exchange: str = "bybit") -> List[Dict[str, Any]]:
        """Get market tickers."""
        response = self._send_request("GET_TICKERS", {"exchange": exchange})

        if not response.get("success"):
            raise ValueError(f"Failed to get tickers: {response.get('error')}")

        return response["data"]["tickers"]

    def backfill(
        self,
        symbol: str,
        interval: str,
        start_time: datetime,
        end_time: datetime,
        exchange: str = "bybit",
        replace_existing: bool = False,
    ) -> Dict[str, Any]:
        """Trigger data backfill."""
        payload = {
            "symbol": symbol,
            "interval": interval,
            "exchange": exchange,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "replace_existing": replace_existing,
        }

        response = self._send_request("BACKFILL", payload)

        if not response.get("success"):
            raise ValueError(f"Failed to backfill: {response.get('error')}")

        return response["data"]

    def get_cache_status(self) -> Dict[str, Any]:
        """Get cache status."""
        response = self._send_request("GET_CACHE_STATUS", {})

        if not response.get("success"):
            raise ValueError(f"Failed to get cache status: {response.get('error')}")

        return response["data"]

    def clear_cache(self) -> int:
        """Clear all cached data."""
        response = self._send_request("CLEAR_CACHE", {})

        if not response.get("success"):
            raise ValueError(f"Failed to clear cache: {response.get('error')}")

        return response["data"]["files_deleted"]

    def health_check(self) -> bool:
        """Check if data service is healthy."""
        try:
            status = self.get_cache_status()
            return True
        except Exception:
            return False


# =============================================================================
# Convenience Functions
# =============================================================================

def get_klines(
    symbol: str,
    interval: str = "1",
    address: str = "ipc:///tmp/dgbit_data.ipc",
    **kwargs
) -> KlineData:
    """Quick function to get klines without creating a client."""
    client = DataServiceClient(address=address)
    try:
        return client.get_klines(symbol, interval, **kwargs)
    finally:
        client.close()


def get_symbols(
    exchange: str = "bybit",
    address: str = "ipc:///tmp/dgbit_data.ipc",
) -> List[Dict[str, Any]]:
    """Quick function to get symbols without creating a client."""
    client = DataServiceClient(address=address)
    try:
        return client.get_symbols(exchange)
    finally:
        client.close()
