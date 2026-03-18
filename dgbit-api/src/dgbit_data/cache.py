"""
Cache manager for storing and retrieving market data.

Uses Parquet format for efficient columnar storage and fast queries.
"""

import os
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
import pandas as pd
from loguru import logger

from dgbit_data.models import (
    KlineData, CacheInfo, CacheStatus, Exchange, Interval
)


class CacheManager:
    """Manages market data cache using Parquet files."""

    def __init__(self, cache_dir: str = "data/cache"):
        """
        Initialize cache manager.

        Args:
            cache_dir: Directory for cache files
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._metadata_file = self.cache_dir / "cache_metadata.json"

    def _get_cache_path(
        self,
        symbol: str,
        exchange: Exchange,
        interval: Interval,
    ) -> Path:
        """Get cache file path for a symbol."""
        # Normalize symbol (e.g., BTCUSDT -> BTC_USDT)
        normalized = symbol.upper().replace("-", "_")
        return self.cache_dir / f"{exchange.value}_{normalized}_{interval.value}.parquet"

    def _get_metadata_path(self, cache_path: Path) -> Path:
        """Get metadata file path for a cache file."""
        return cache_path.with_suffix(".meta.json")

    def save(self, kline_data: KlineData) -> CacheInfo:
        """
        Save kline data to cache.

        Args:
            kline_data: KlineData to cache

        Returns:
            CacheInfo about the saved data
        """
        cache_path = self._get_cache_path(
            kline_data.symbol,
            kline_data.exchange,
            kline_data.interval,
        )

        # Convert to DataFrame
        df = kline_data.to_dataframe()

        # Add metadata columns for efficient querying
        df = df.copy()
        df["_symbol"] = kline_data.symbol
        df["_exchange"] = kline_data.exchange.value
        df["_interval"] = kline_data.interval.value

        # Save to Parquet
        if cache_path.exists():
            # Append to existing file
            existing = pd.read_parquet(cache_path)
            # Combine and remove duplicates based on timestamp
            combined = pd.concat([existing, df], ignore_index=True)
            combined = combined.drop_duplicates(subset=["timestamp"], keep="last")
            combined = combined.sort_values("timestamp")
            combined.to_parquet(cache_path, index=False)
        else:
            df.to_parquet(cache_path, index=False)

        # Update metadata
        meta_path = self._get_metadata_path(cache_path)
        file_size = cache_path.stat().st_size
        metadata = {
            "symbol": kline_data.symbol,
            "exchange": kline_data.exchange.value,
            "interval": kline_data.interval.value,
            "start_time": kline_data.start_time.isoformat(),
            "end_time": kline_data.end_time.isoformat(),
            "record_count": len(df),
            "file_size": file_size,
            "last_updated": datetime.utcnow().isoformat(),
        }
        with open(meta_path, "w") as f:
            json.dump(metadata, f, indent=2)

        logger.info(f"Cached {len(df)} records for {kline_data.symbol} at {cache_path}")

        return CacheInfo(
            symbol=kline_data.symbol,
            exchange=kline_data.exchange,
            interval=kline_data.interval,
            start_time=kline_data.start_time,
            end_time=kline_data.end_time,
            record_count=len(df),
            file_path=str(cache_path),
            file_size_bytes=file_size,
            last_updated=datetime.utcnow(),
            is_complete=False,
        )

    def get(
        self,
        symbol: str,
        exchange: Exchange,
        interval: Interval,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 10000,
    ) -> Optional[KlineData]:
        """
        Retrieve kline data from cache.

        Args:
            symbol: Trading pair symbol
            exchange: Exchange name
            interval: Kline interval
            start_time: Start of time range (optional)
            end_time: End of time range (optional)
            limit: Maximum records to return

        Returns:
            KlineData if found, None otherwise
        """
        cache_path = self._get_cache_path(symbol, exchange, interval)

        if not cache_path.exists():
            logger.debug(f"Cache miss for {symbol} @ {exchange.value}/{interval.value}")
            return None

        try:
            df = pd.read_parquet(cache_path)

            # Filter by time range
            if start_time:
                df = df[df["timestamp"] >= start_time]
            if end_time:
                df = df[df["timestamp"] <= end_time]

            # Apply limit
            if len(df) > limit:
                df = df.tail(limit)

            if df.empty:
                return None

            # Remove metadata columns for output
            for col in ["_symbol", "_exchange", "_interval"]:
                if col in df.columns:
                    df = df.drop(columns=[col])

            kline_data = KlineData.from_dataframe(
                df,
                symbol=symbol,
                exchange=exchange,
                interval=interval,
                source=__import__("dgbit_data.models", fromlist=["DataSource"]).DataSource.CACHE,
            )

            logger.debug(f"Cache hit: {len(kline_data.data)} records for {symbol}")
            return kline_data

        except Exception as e:
            logger.error(f"Error reading cache: {e}")
            return None

    def get_info(
        self,
        symbol: str,
        exchange: Exchange,
        interval: Interval,
    ) -> Optional[CacheInfo]:
        """Get cache info for a symbol."""
        cache_path = self._get_cache_path(symbol, exchange, interval)
        meta_path = self._get_metadata_path(cache_path)

        if not meta_path.exists():
            return None

        try:
            with open(meta_path, "r") as f:
                meta = json.load(f)

            return CacheInfo(
                symbol=meta["symbol"],
                exchange=Exchange(meta["exchange"]),
                interval=Interval(meta["interval"]),
                start_time=datetime.fromisoformat(meta["start_time"]),
                end_time=datetime.fromisoformat(meta["end_time"]),
                record_count=meta["record_count"],
                file_path=meta["symbol"],
                file_size_bytes=meta["file_size"],
                last_updated=datetime.fromisoformat(meta["last_updated"]),
                is_complete=False,
            )
        except Exception as e:
            logger.error(f"Error reading cache info: {e}")
            return None

    def get_status(self) -> CacheStatus:
        """Get overall cache status."""
        symbols = {}
        total_size = 0
        total_files = 0
        oldest = None
        newest = None

        for meta_path in self.cache_dir.glob("*.meta.json"):
            try:
                with open(meta_path, "r") as f:
                    meta = json.load(f)

                file_path = meta_path.with_suffix(".parquet")
                file_size = file_path.stat().st_size if file_path.exists() else 0

                total_size += file_size
                total_files += 1

                start = datetime.fromisoformat(meta["start_time"])
                end = datetime.fromisoformat(meta["end_time"])

                if oldest is None or start < oldest:
                    oldest = start
                if newest is None or end > newest:
                    newest = end

                key = f"{meta['exchange']}_{meta['symbol']}_{meta['interval']}"
                symbols[key] = CacheInfo(
                    symbol=meta["symbol"],
                    exchange=Exchange(meta["exchange"]),
                    interval=Interval(meta["interval"]),
                    start_time=start,
                    end_time=end,
                    record_count=meta["record_count"],
                    file_path=str(file_path),
                    file_size_bytes=file_size,
                    last_updated=datetime.fromisoformat(meta["last_updated"]),
                    is_complete=False,
                )

            except Exception as e:
                logger.warning(f"Error reading {meta_path}: {e}")

        return CacheStatus(
            cache_dir=str(self.cache_dir),
            total_symbols=len(symbols),
            total_files=total_files,
            total_size_bytes=total_size,
            oldest_data=oldest,
            newest_data=newest,
            symbol_details=list(symbols.values()),
        )

    def delete(
        self,
        symbol: str,
        exchange: Exchange,
        interval: Interval,
    ) -> bool:
        """Delete cached data for a symbol."""
        cache_path = self._get_cache_path(symbol, exchange, interval)
        meta_path = self._get_metadata_path(cache_path)

        deleted = False
        if cache_path.exists():
            cache_path.unlink()
            deleted = True
        if meta_path.exists():
            meta_path.unlink()
            deleted = True

        if deleted:
            logger.info(f"Deleted cache for {symbol} @ {exchange.value}/{interval.value}")

        return deleted

    def clear_all(self) -> int:
        """Clear all cached data. Returns number of files deleted."""
        count = 0
        for path in self.cache_dir.glob("*.parquet"):
            path.unlink()
            count += 1
        for path in self.cache_dir.glob("*.meta.json"):
            path.unlink()
            count += 1

        logger.info(f"Cleared {count} cache files")
        return count
