"""
NNG Data Service for dgbit.

This service provides a high-performance interface for market data
via NNG (nanomsg Next Gen) IPC messaging.

Commands:
- GET_KLINES: Fetch kline data (uses cache + live fetch)
- GET_SYMBOLS: List available symbols
- GET_TICKERS: Get market tickers
- BACKFILL: Trigger data backfill
- GET_CACHE_STATUS: Get cache status
- CLEAR_CACHE: Clear cache
"""

import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

# Add parent directories to path for imports
SRC_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(SRC_DIR))

import pynng
from loguru import logger

from dgbit_data.models import (
    KlineData, GetKlinesRequest, GetSymbolsRequest, BackfillRequest,
    ServiceRequest, ServiceResponse, Exchange, Interval,
)
from dgbit_data.cache import CacheManager
from dgbit_data.adapters import AdapterFactory


class DataService:
    """
    Market data service with caching and live fetching.

    Architecture:
    ┌─────────────────────────────────────────────────────────────┐
    │                    NNG Server                                │
    │  - Request/Reply pattern                                     │
    │  - IPC socket at configurable address                        │
    └─────────────────────────────────────────────────────────────┘
                            │
                            ▼
    ┌─────────────────────────────────────────────────────────────┐
    │                    Data Service                              │
    │  ┌─────────────────┐  ┌─────────────────────────────────┐   │
    │  │ Cache Manager   │  │  Adapter Factory               │   │
    │  │ (Parquet)       │  │  - Bybit                        │   │
    │  │                 │  │  - Binance (future)             │   │
    │  └─────────────────┘  └─────────────────────────────────┘   │
    └─────────────────────────────────────────────────────────────┘
    """

    def __init__(
        self,
        cache_dir: str = "data/cache",
        nng_address: str = "ipc:///tmp/dgbit_data.ipc",
        api_key: str = "",
        api_secret: str = "",
        testnet: bool = False,
    ):
        """
        Initialize data service.

        Args:
            cache_dir: Directory for cache files
            nng_address: NNG IPC address
            api_key: Bybit API key
            api_secret: Bybit API secret
            testnet: Use Bybit testnet
        """
        self.cache_dir = cache_dir
        self.nng_address = nng_address
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet

        self.cache_manager = CacheManager(cache_dir)
        self.adapters: Dict[Exchange, Any] = {}
        self._socket: Optional[pynng.Rep0] = None

    def _get_adapter(self, exchange: Exchange):
        """Get or create adapter for exchange."""
        if exchange not in self.adapters:
            self.adapters[exchange] = AdapterFactory.create(
                exchange,
                api_key=self.api_key,
                api_secret=self.api_secret,
                testnet=self.testnet,
            )
        return self.adapters[exchange]

    def handle_get_klines(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle GET_KLINES command."""
        try:
            request = GetKlinesRequest(**payload)

            # Check cache first if allowed
            if request.use_cache and not request.force_refresh:
                cached = self.cache_manager.get(
                    symbol=request.symbol,
                    exchange=request.exchange,
                    interval=request.interval,
                    start_time=request.start_time,
                    end_time=request.end_time,
                    limit=request.limit,
                )
                if cached and cached.count >= min(request.limit, 100):
                    logger.info(f"Cache hit for {request.symbol}")
                    return {
                        "success": True,
                        "data": {
                            "symbol": cached.symbol,
                            "exchange": cached.exchange.value,
                            "interval": cached.interval.value,
                            "start_time": cached.start_time.isoformat(),
                            "end_time": cached.end_time.isoformat(),
                            "count": cached.count,
                            "source": cached.source.value,
                            "records": [k.model_dump() for k in cached.data],
                        }
                    }

            # Fetch from exchange
            adapter = self._get_adapter(request.exchange)
            kline_data = adapter.get_klines(
                symbol=request.symbol,
                interval=request.interval,
                start_time=request.start_time,
                end_time=request.end_time,
                limit=request.limit,
            )

            # Cache the result
            if request.use_cache:
                self.cache_manager.save(kline_data)

            return {
                "success": True,
                "data": {
                    "symbol": kline_data.symbol,
                    "exchange": kline_data.exchange.value,
                    "interval": kline_data.interval.value,
                    "start_time": kline_data.start_time.isoformat(),
                    "end_time": kline_data.end_time.isoformat(),
                    "count": kline_data.count,
                    "source": kline_data.source.value,
                    "records": [k.model_dump() for k in kline_data.data],
                }
            }

        except Exception as e:
            logger.error(f"Error fetching klines: {e}")
            return {"success": False, "error": str(e)}

    def handle_get_symbols(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle GET_SYMBOLS command."""
        try:
            request = GetSymbolsRequest(**payload)
            adapter = self._get_adapter(request.exchange)
            symbols = adapter.get_symbols()

            return {
                "success": True,
                "data": {
                    "exchange": request.exchange.value,
                    "count": len(symbols),
                    "symbols": [s.model_dump() for s in symbols],
                }
            }
        except Exception as e:
            logger.error(f"Error fetching symbols: {e}")
            return {"success": False, "error": str(e)}

    def handle_get_tickers(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle GET_TICKERS command."""
        try:
            exchange = Exchange(payload.get("exchange", "bybit"))
            adapter = self._get_adapter(exchange)
            tickers = adapter.get_tickers()

            return {
                "success": True,
                "data": {
                    "exchange": exchange.value,
                    "count": len(tickers),
                    "tickers": [t.model_dump() for t in tickers],
                }
            }
        except Exception as e:
            logger.error(f"Error fetching tickers: {e}")
            return {"success": False, "error": str(e)}

    def handle_backfill(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle BACKFILL command."""
        try:
            request = BackfillRequest(**payload)
            adapter = self._get_adapter(request.exchange)

            # Calculate number of batches needed
            interval_seconds = {
                Interval.M1: 60,
                Interval.M5: 300,
                Interval.M15: 900,
                Interval.M30: 1800,
                Interval.H1: 3600,
                Interval.H4: 14400,
                Interval.D1: 86400,
            }.get(request.interval, 60)

            total_seconds = (request.end_time - request.start_time).total_seconds()
            batches = int(total_seconds / (interval_seconds * 1000)) + 1

            total_records = 0
            current_start = request.start_time

            for i in range(batches):
                batch_end = min(
                    current_start + timedelta(seconds=interval_seconds * 1000),
                    request.end_time
                )

                kline_data = adapter.get_klines(
                    symbol=request.symbol,
                    interval=request.interval,
                    start_time=current_start,
                    end_time=batch_end,
                    limit=1000,
                )

                if request.replace_existing:
                    self.cache_manager.delete(
                        symbol=request.symbol,
                        exchange=request.exchange,
                        interval=request.interval,
                    )

                self.cache_manager.save(kline_data)
                total_records += kline_data.count

                current_start = batch_end
                logger.info(f"Backfill progress: {i+1}/{batches} batches")

            return {
                "success": True,
                "data": {
                    "symbol": request.symbol,
                    "exchange": request.exchange.value,
                    "interval": request.interval.value,
                    "total_records": total_records,
                    "batches": batches,
                }
            }

        except Exception as e:
            logger.error(f"Error during backfill: {e}")
            return {"success": False, "error": str(e)}

    def handle_get_cache_status(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle GET_CACHE_STATUS command."""
        try:
            status = self.cache_manager.get_status()

            return {
                "success": True,
                "data": {
                    "cache_dir": status.cache_dir,
                    "total_symbols": status.total_symbols,
                    "total_files": status.total_files,
                    "total_size_bytes": status.total_size_bytes,
                    "total_size_mb": round(status.total_size_bytes / 1024 / 1024, 2),
                    "oldest_data": status.oldest_data.isoformat() if status.oldest_data else None,
                    "newest_data": status.newest_data.isoformat() if status.newest_data else None,
                    "symbols": [
                        {
                            "symbol": s.symbol,
                            "exchange": s.exchange.value,
                            "interval": s.interval.value,
                            "start_time": s.start_time.isoformat() if s.start_time else None,
                            "end_time": s.end_time.isoformat() if s.end_time else None,
                            "records": s.record_count,
                            "size_mb": round(s.file_size_bytes / 1024 / 1024, 2),
                        }
                        for s in status.symbol_details
                    ],
                }
            }
        except Exception as e:
            logger.error(f"Error getting cache status: {e}")
            return {"success": False, "error": str(e)}

    def handle_clear_cache(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle CLEAR_CACHE command."""
        try:
            count = self.cache_manager.clear_all()
            return {
                "success": True,
                "data": {"files_deleted": count}
            }
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            return {"success": False, "error": str(e)}

    def handle_command(self, request: ServiceRequest) -> ServiceResponse:
        """Process a service command."""
        command_handlers = {
            "GET_KLINES": self.handle_get_klines,
            "GET_SYMBOLS": self.handle_get_symbols,
            "GET_TICKERS": self.handle_get_tickers,
            "BACKFILL": self.handle_backfill,
            "GET_CACHE_STATUS": self.handle_get_cache_status,
            "CLEAR_CACHE": self.handle_clear_cache,
        }

        handler = command_handlers.get(request.command)
        if not handler:
            return ServiceResponse.error(
                command=request.command,
                request_id=request.request_id,
                error=f"Unknown command: {request.command}",
            )

        try:
            result = handler(request.payload)
            if result["success"]:
                return ServiceResponse.ok(
                    command=request.command,
                    request_id=request.request_id,
                    data=result.get("data"),
                )
            else:
                return ServiceResponse.error(
                    command=request.command,
                    request_id=request.request_id,
                    error=result.get("error", "Unknown error"),
                )
        except Exception as e:
            logger.exception(f"Error handling {request.command}")
            return ServiceResponse.error(
                command=request.command,
                request_id=request.request_id,
                error=str(e),
            )

    async def run(self):
        """Run the data service."""
        import os

        # Create socket
        self._socket = pynng.Rep0(listen=self.nng_address)
        logger.info(f"Data service listening on {self.nng_address}")

        # Ensure cache directory exists
        os.makedirs(self.cache_dir, exist_ok=True)

        try:
            while True:
                # Receive request
                message = self._socket.recv()
                request_dict = json.loads(message.decode("utf-8"))

                # Parse request
                request = ServiceRequest(**request_dict)

                logger.debug(f"Received command: {request.command}")

                # Handle command
                response = self.handle_command(request)

                # Send response
                response_data = response.model_dump()
                self._socket.send(json.dumps(response_data).encode("utf-8"))

        except asyncio.CancelledError:
            logger.info("Data service shutdown requested")
        except KeyboardInterrupt:
            logger.info("Data service interrupted")
        finally:
            if self._socket:
                self._socket.close()
                self._socket = None


def run_service():
    """Entry point for running the data service."""
    import argparse

    parser = argparse.ArgumentParser(description="dgbit Data Service")
    parser.add_argument("--cache-dir", default="data/cache", help="Cache directory")
    parser.add_argument("--address", default="ipc:///tmp/dgbit_data.ipc", help="NNG address")
    parser.add_argument("--api-key", default="", help="API key")
    parser.add_argument("--api-secret", default="", help="API secret")
    parser.add_argument("--testnet", action="store_true", help="Use testnet")
    parser.add_argument("--log-level", default="INFO", help="Log level")

    args = parser.parse_args()

    # Setup logging
    logger.remove()
    logger.add(sys.stdout, level=args.log_level, format="{time} | {level} | {message}")

    # Create and run service
    service = DataService(
        cache_dir=args.cache_dir,
        nng_address=args.address,
        api_key=args.api_key,
        api_secret=args.api_secret,
        testnet=args.testnet,
    )

    asyncio.run(service.run())


if __name__ == "__main__":
    run_service()
