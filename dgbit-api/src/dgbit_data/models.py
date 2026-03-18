"""
Data models for the dgbit data service.

These models provide validated data contracts for all market data
exchanged between the data service and clients.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, validator
import pandas as pd


class Interval(str, Enum):
    """Kline intervals."""
    M1 = "1"
    M5 = "5"
    M15 = "15"
    M30 = "30"
    H1 = "60"
    H4 = "240"
    D1 = "D"
    W1 = "W"
    MN = "M"


class Exchange(str, Enum):
    """Supported exchanges."""
    BYBIT = "bybit"
    BINANCE = "binance"
    COINBASE = "coinbase"
    KRAKEN = "kraken"


class DataSource(str, Enum):
    """Data source types."""
    LIVE = "live"
    CACHE = "cache"
    BACKFILL = "backfill"
    SIMULATED = "simulated"


# =============================================================================
# Kline Data Models
# =============================================================================

class KlineBase(BaseModel):
    """Base Kline (OHLCV) data."""
    timestamp: datetime
    open: float = Field(gt=0, description="Open price")
    high: float = Field(gt=0, description="High price")
    low: float = Field(gt=0, description="Low price")
    close: float = Field(gt=0, description="Close price")
    volume: float = Field(ge=0, description="Trading volume")
    turnover: float = Field(ge=0, description="Trading turnover")

    @validator("high")
    def high_must_be_ge_open(cls, v, values):
        if "open" in values and v < values["open"]:
            raise ValueError("high must be >= open")
        return v

    @validator("low")
    def low_must_be_le_open(cls, v, values):
        if "open" in values and v > values["open"]:
            raise ValueError("low must be <= open")
        return v


class KlineData(BaseModel):
    """Validated Kline data with metadata."""
    symbol: str = Field(..., min_length=1, description="Trading pair symbol")
    exchange: Exchange = Field(default=Exchange.BYBIT, description="Exchange name")
    interval: Interval = Field(default=Interval.M1, description="Kline interval")
    start_time: datetime = Field(description="Data start time")
    end_time: datetime = Field(description="Data end time")
    count: int = Field(ge=0, description="Number of klines")
    data: List[KlineBase] = Field(description="Kline records")
    source: DataSource = Field(default=DataSource.LIVE, description="Data source")
    cached_at: Optional[datetime] = Field(None, description="When data was cached")

    @validator("end_time")
    def end_time_must_be_after_start(cls, v, values):
        if "start_time" in values and v <= values["start_time"]:
            raise ValueError("end_time must be after start_time")
        return v

    def to_dataframe(self) -> pd.DataFrame:
        """Convert to pandas DataFrame."""
        if not self.data:
            return pd.DataFrame(columns=[
                "timestamp", "open", "high", "low", "close", "volume", "turnover"
            ])

        return pd.DataFrame([k.model_dump() for k in self.data])

    @classmethod
    def from_dataframe(
        cls,
        df: pd.DataFrame,
        symbol: str,
        exchange: Exchange = Exchange.BYBIT,
        interval: Interval = Interval.M1,
        source: DataSource = DataSource.LIVE,
    ) -> "KlineData":
        """Create KlineData from DataFrame."""
        # Validate required columns
        required = ["timestamp", "open", "high", "low", "close", "volume", "turnover"]
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise ValueError(f"Missing columns: {missing}")

        # Parse timestamps
        timestamps = pd.to_datetime(df["timestamp"])

        # Create kline records
        klines = [
            KlineBase(
                timestamp=ts,
                open=row["open"],
                high=row["high"],
                low=row["low"],
                close=row["close"],
                volume=row["volume"],
                turnover=row.get("turnover", 0.0),
            )
            for ts, row in zip(timestamps, df.itertuples(index=False))
        ]

        return KlineData(
            symbol=symbol,
            exchange=exchange,
            interval=interval,
            start_time=timestamps.min(),
            end_time=timestamps.max(),
            count=len(klines),
            data=klines,
            source=source,
        )


# =============================================================================
# Symbol and Market Models
# =============================================================================

class SymbolStatus(str, Enum):
    """Symbol trading status."""
    TRADING = "trading"
    BREAK = "break"
    HALTED = "halted"
    DELISTED = "delisted"


class SymbolInfo(BaseModel):
    """Information about a trading symbol."""
    symbol: str = Field(..., description="Trading pair symbol")
    base_asset: str = Field(..., description="Base asset (e.g., BTC)")
    quote_asset: str = Field(..., description="Quote asset (e.g., USDT)")
    exchange: Exchange = Field(..., description="Exchange name")
    status: SymbolStatus = Field(default=SymbolStatus.TRADING, description="Trading status")
    min_price: float = Field(gt=0, description="Minimum price precision")
    max_price: float = Field(gt=0, description="Maximum price")
    min_quantity: float = Field(gt=0, description="Minimum order quantity")
    max_quantity: float = Field(gt=0, description="Maximum order quantity")
    tick_size: float = Field(gt=0, description="Price tick size")
    step_size: float = Field(gt=0, description="Quantity step size")
    created_at: Optional[datetime] = Field(None, description="When symbol was added")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional data")


class MarketSummary(BaseModel):
    """Summary of market conditions for a symbol."""
    symbol: str = Field(..., description="Trading pair")
    exchange: Exchange = Field(..., description="Exchange name")
    price_24h: float = Field(..., description="24h price")
    price_24h_change_pct: float = Field(description="24h price change %")
    volume_24h: float = Field(..., description="24h volume")
    high_24h: float = Field(..., description="24h high")
    low_24h: float = Field(..., description="24h low")
    bid_price: float = Field(description="Current bid")
    ask_price: float = Field(description="Current ask")
    last_update: datetime = Field(description="Last update time")


# =============================================================================
# Cache Models
# =============================================================================

class CacheInfo(BaseModel):
    """Information about cached data."""
    symbol: str = Field(..., description="Trading pair")
    exchange: Exchange = Field(..., description="Exchange name")
    interval: Interval = Field(..., description="Kline interval")
    start_time: Optional[datetime] = Field(None, description="Earliest cached data")
    end_time: Optional[datetime] = Field(None, description="Latest cached data")
    record_count: int = Field(default=0, description="Number of records")
    file_path: str = Field(..., description="Cache file path")
    file_size_bytes: int = Field(default=0, description="File size in bytes")
    last_updated: datetime = Field(..., description="Last cache update")
    is_complete: bool = Field(default=False, description="Whether cache is complete")


class CacheStatus(BaseModel):
    """Overall cache status."""
    cache_dir: str = Field(..., description="Cache directory path")
    total_symbols: int = Field(default=0, description="Total cached symbols")
    total_files: int = Field(default=0, description="Total cache files")
    total_size_bytes: int = Field(default=0, description="Total cache size")
    oldest_data: Optional[datetime] = Field(None, description="Oldest cached data")
    newest_data: Optional[datetime] = Field(None, description="Newest cached data")
    symbol_details: List[CacheInfo] = Field(default_factory=list, description="Per-symbol info")


# =============================================================================
# Request/Response Models for NNG
# =============================================================================

class GetKlinesRequest(BaseModel):
    """Request for kline data."""
    symbol: str = Field(..., description="Trading pair symbol")
    exchange: Exchange = Field(default=Exchange.BYBIT, description="Exchange name")
    interval: Interval = Field(default=Interval.M1, description="Kline interval")
    start_time: Optional[datetime] = Field(None, description="Start time")
    end_time: Optional[datetime] = Field(None, description="End time")
    limit: int = Field(default=1000, ge=1, le=10000, description="Max records")
    use_cache: bool = Field(default=True, description="Use cached data if available")
    force_refresh: bool = Field(default=False, description="Force refresh from exchange")


class GetSymbolsRequest(BaseModel):
    """Request for symbol list."""
    exchange: Exchange = Field(default=Exchange.BYBIT, description="Exchange name")
    status: Optional[SymbolStatus] = Field(None, description="Filter by status")


class BackfillRequest(BaseModel):
    """Request to backfill data."""
    symbol: str = Field(..., description="Trading pair symbol")
    exchange: Exchange = Field(default=Exchange.BYBIT, description="Exchange name")
    interval: Interval = Field(default=Interval.M1, description="Kline interval")
    start_time: datetime = Field(..., description="Backfill start time")
    end_time: datetime = Field(..., description="Backfill end time")
    replace_existing: bool = Field(default=False, description="Replace existing cache")


class ServiceRequest(BaseModel):
    """Generic service request."""
    command: str = Field(..., description="Command name")
    payload: Dict[str, Any] = Field(default_factory=dict, command="Command payload")
    request_id: str = Field(default_factory=lambda: __import__("uuid").uuid4().hex)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ServiceResponse(BaseModel):
    """Generic service response."""
    success: bool = Field(..., description="Whether request succeeded")
    command: str = Field(..., description="Command name")
    request_id: str = Field(..., description="Request ID for correlation")
    data: Optional[Dict[str, Any]] = Field(None, description="Response data")
    error: Optional[str] = Field(None, description="Error message if failed")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    @classmethod
    def ok(cls, command: str, request_id: str, data: Dict[str, Any] = None) -> "ServiceResponse":
        return cls(success=True, command=command, request_id=request_id, data=data)

    @classmethod
    def error(cls, command: str, request_id: str, error: str) -> "ServiceResponse":
        return cls(success=False, command=command, request_id=request_id, error=error)
