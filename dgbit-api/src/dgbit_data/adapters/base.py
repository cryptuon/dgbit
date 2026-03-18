"""
Base Adapter Interfaces

Defines the abstract base classes for exchange adapters.
All concrete adapters must implement these interfaces.

Author: dgbit
Version: 1.0.0
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable
from decimal import Decimal


class Interval(Enum):
    """Kline interval values."""
    M1 = "1m"
    M5 = "5m"
    M15 = "15m"
    M30 = "30m"
    H1 = "1h"
    H4 = "4h"
    D1 = "1d"
    W1 = "1w"
    MN1 = "1M"


class Exchange(Enum):
    """Supported exchanges."""
    BYBIT = "bybit"
    BINANCE = "binance"
    COINBASE = "coinbase"
    OKX = "okx"
    KRAKEN = "kraken"
    KUCOIN = "kucoin"
    BITGET = "bitget"


class Side(Enum):
    """Order side."""
    BUY = "buy"
    SELL = "sell"


class OrderType(Enum):
    """Order type."""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderStatus(Enum):
    """Order status."""
    PENDING = "pending"
    OPEN = "open"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class PositionSide(Enum):
    """Position side."""
    LONG = "long"
    SHORT = "short"
    BOTH = "both"


@dataclass
class ExchangeConfig:
    """
    Configuration for exchange connection.

    Attributes:
        api_key: API key for authenticated requests
        api_secret: API secret for authentication
        passphrase: Additional passphrase (required by some exchanges)
        testnet: Whether to use testnet/sandbox
        timeout: Request timeout in seconds
        rate_limit: Whether to apply rate limiting
    """
    api_key: str = ""
    api_secret: str = ""
    passphrase: str = ""
    testnet: bool = True
    timeout: int = 30
    rate_limit: bool = True

    def validate(self) -> bool:
        """
        Validate configuration.

        Returns:
            True if configuration is valid
        """
        if self.testnet:
            return True  # Testnets don't require credentials
        return bool(self.api_key and self.api_secret)


@dataclass
class Kline:
    """
    Single kline/candlestick data point.

    Attributes:
        timestamp: Start time of the candle
        open: Opening price
        high: Highest price
        low: Lowest price
        close: Closing price
        volume: Trading volume
        turnover: Turnover value (if available)
    """
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    turnover: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
            "turnover": self.turnover,
        }


@dataclass
class KlineData:
    """
    Collection of klines for a symbol.

    Attributes:
        symbol: Trading pair symbol (e.g., "BTCUSDT")
        exchange: Exchange name
        interval: Time interval
        data: List of klines
        source: Data source (cache, live, etc.)
    """
    symbol: str
    exchange: Exchange
    interval: Interval
    data: List[Kline]
    source: str = "live"

    @property
    def count(self) -> int:
        """Return number of klines."""
        return len(self.data)

    @property
    def start_time(self) -> Optional[datetime]:
        """Return start time of data."""
        if not self.data:
            return None
        return self.data[0].timestamp

    @property
    def end_time(self) -> Optional[datetime]:
        """Return end time of data."""
        if not self.data:
            return None
        return self.data[-1].timestamp

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "symbol": self.symbol,
            "exchange": self.exchange.value,
            "interval": self.interval.value,
            "count": self.count,
            "data": [k.to_dict() for k in self.data],
        }


@dataclass
class Ticker:
    """
    Market ticker data.

    Attributes:
        symbol: Trading pair symbol
        price: Current price
        price_24h: 24h ago price
        volume_24h: 24h trading volume
        change_24h: 24h price change percentage
        high_24h: 24h high price
        low_24h: 24h low price
        timestamp: Update time
    """
    symbol: str
    price: float
    price_24h: float = 0.0
    volume_24h: float = 0.0
    change_24h: float = 0.0
    high_24h: float = 0.0
    low_24h: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "symbol": self.symbol,
            "price": self.price,
            "price_24h": self.price_24h,
            "volume_24h": self.volume_24h,
            "change_24h": self.change_24h,
            "high_24h": self.high_24h,
            "low_24h": self.low_24h,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class Symbol:
    """
    Trading pair information.

    Attributes:
        symbol: Trading pair (e.g., "BTC/USDT")
        base: Base asset (e.g., "BTC")
        quote: Quote asset (e.g., "USDT")
        precision: Price precision (decimal places)
        quantity_precision: Quantity precision
        min_quantity: Minimum order quantity
        min_value: Minimum order value
        status: Trading status (trading, break, etc.)
        maker_fee: Maker fee rate
        taker_fee: Taker fee rate
    """
    symbol: str
    base: str
    quote: str
    precision: int = 8
    quantity_precision: int = 4
    min_quantity: float = 0.0
    min_value: float = 0.0
    status: str = "trading"
    maker_fee: float = 0.001
    taker_fee: float = 0.001

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "symbol": self.symbol,
            "base": self.base,
            "quote": self.quote,
            "precision": self.precision,
            "quantity_precision": self.quantity_precision,
            "min_quantity": self.min_quantity,
            "min_value": self.min_value,
            "status": self.status,
            "maker_fee": self.maker_fee,
            "taker_fee": self.taker_fee,
        }


@dataclass
class OrderBook:
    """
    Order book data.

    Attributes:
        symbol: Trading pair
        bids: List of [price, quantity] pairs
        asks: List of [price, quantity] pairs
        timestamp: Update time
    """
    symbol: str
    bids: List[List[float]]
    asks: List[List[float]]
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "symbol": self.symbol,
            "bids": self.bids,
            "asks": self.asks,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class Order:
    """
    Order information.

    Attributes:
        order_id: Exchange order ID
        symbol: Trading pair
        side: Order side (buy/sell)
        order_type: Order type (market/limit/stop)
        quantity: Order quantity
        price: Limit price (if applicable)
        filled_qty: Filled quantity
        avg_price: Average fill price
        status: Order status
        created_at: Order creation time
        updated_at: Last update time
    """
    order_id: str
    symbol: str
    side: Side
    order_type: OrderType
    quantity: float
    price: Optional[float] = None
    filled_qty: float = 0.0
    avg_price: Optional[float] = None
    status: OrderStatus = OrderStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "order_id": self.order_id,
            "symbol": self.symbol,
            "side": self.side.value,
            "order_type": self.order_type.value,
            "quantity": self.quantity,
            "price": self.price,
            "filled_qty": self.filled_qty,
            "avg_price": self.avg_price,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass
class Position:
    """
    Trading position.

    Attributes:
        symbol: Trading pair
        side: Position side (long/short)
        quantity: Position size
        entry_price: Average entry price
        mark_price: Current mark price
        unrealized_pnl: Unrealized P&L
        leverage: Leverage multiplier
    """
    symbol: str
    side: PositionSide
    quantity: float
    entry_price: float
    mark_price: float = 0.0
    unrealized_pnl: float = 0.0
    leverage: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "symbol": self.symbol,
            "side": self.side.value,
            "quantity": self.quantity,
            "entry_price": self.entry_price,
            "mark_price": self.mark_price,
            "unrealized_pnl": self.unrealized_pnl,
            "leverage": self.leverage,
        }


@dataclass
class Trade:
    """
    Executed trade.

    Attributes:
        trade_id: Trade ID
        order_id: Related order ID
        symbol: Trading pair
        side: Trade side
        quantity: Trade quantity
        price: Execution price
        fee: Trading fee
        fee_currency: Fee currency
        timestamp: Trade time
    """
    trade_id: str
    order_id: str
    symbol: str
    side: Side
    quantity: float
    price: float
    fee: float = 0.0
    fee_currency: str = "USDT"
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "trade_id": self.trade_id,
            "order_id": self.order_id,
            "symbol": self.symbol,
            "side": self.side.value,
            "quantity": self.quantity,
            "price": self.price,
            "fee": self.fee,
            "fee_currency": self.fee_currency,
            "timestamp": self.timestamp.isoformat(),
        }


@runtime_checkable
class DataAdapter(Protocol):
    """
    Protocol for data-fetching adapters.

    All data adapters must implement this interface.

    Example:
        ```python
        class BinanceAdapter(DataAdapter):
            def get_klines(
                self,
                symbol: str,
                interval: Interval,
                start_time: Optional[int] = None,
                end_time: Optional[int] = None,
                limit: int = 100,
            ) -> KlineData:
                # Implementation
                pass
        ```
    """

    @property
    def name(self) -> str:
        """Return exchange name."""
        ...

    @property
    def exchange(self) -> Exchange:
        """Return exchange enum value."""
        ...

    def get_klines(
        self,
        symbol: str,
        interval: Interval,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        limit: int = 100,
    ) -> KlineData:
        """
        Fetch kline/candlestick data.

        Args:
            symbol: Trading pair (e.g., "BTCUSDT")
            interval: Time interval
            start_time: Start time in milliseconds
            end_time: End time in milliseconds
            limit: Maximum number of klines

        Returns:
            KlineData object with historical data
        """
        ...

    def get_symbols(self) -> List[Symbol]:
        """
        Fetch available trading pairs.

        Returns:
            List of Symbol objects
        """
        ...

    def get_tickers(self, symbol: Optional[str] = None) -> List[Ticker]:
        """
        Fetch market tickers.

        Args:
            symbol: Optional symbol filter

        Returns:
            List of Ticker objects
        """
        ...

    def get_order_book(
        self,
        symbol: str,
        depth: int = 100,
    ) -> OrderBook:
        """
        Fetch order book.

        Args:
            symbol: Trading pair
            depth: Order book depth

        Returns:
            OrderBook object
        """
        ...

    def get_balance(self) -> Dict[str, float]:
        """
        Fetch account balance.

        Returns:
            Dictionary of asset -> available balance
        """
        ...

    def health_check(self) -> bool:
        """
        Check if adapter is healthy.

        Returns:
            True if connection is healthy
        """
        ...


@runtime_checkable
class ExecutionAdapter(Protocol):
    """
    Protocol for execution adapters.

    All execution adapters must implement this interface.

    Example:
        ```python
        class BinanceExecutionAdapter(ExecutionAdapter):
            def create_order(
                self,
                symbol: str,
                side: Side,
                order_type: OrderType,
                quantity: float,
                price: Optional[float] = None,
            ) -> Order:
                # Implementation
                pass
        ```
    """

    @property
    def name(self) -> str:
        """Return exchange name."""
        ...

    @property
    def exchange(self) -> Exchange:
        """Return exchange enum value."""
        ...

    def create_order(
        self,
        symbol: str,
        side: Side,
        order_type: OrderType,
        quantity: float,
        price: Optional[float] = None,
        stop_price: Optional[float] = None,
        time_in_force: str = "GTC",
    ) -> Order:
        """
        Create a new order.

        Args:
            symbol: Trading pair
            side: Order side (buy/sell)
            order_type: Order type
            quantity: Order quantity
            price: Limit price (for limit orders)
            stop_price: Stop price (for stop orders)
            time_in_force: Time in force (GTC, IOC, FOK)

        Returns:
            Order object with order ID
        """
        ...

    def cancel_order(
        self,
        order_id: str,
        symbol: str,
    ) -> bool:
        """
        Cancel an order.

        Args:
            order_id: Order ID to cancel
            symbol: Trading pair

        Returns:
            True if cancellation was successful
        """
        ...

    def get_order(
        self,
        order_id: str,
        symbol: str,
    ) -> Optional[Order]:
        """
        Get order status.

        Args:
            order_id: Order ID
            symbol: Trading pair

        Returns:
            Order object or None if not found
        """
        ...

    def get_open_orders(
        self,
        symbol: Optional[str] = None,
    ) -> List[Order]:
        """
        Get all open orders.

        Args:
            symbol: Optional symbol filter

        Returns:
            List of open Order objects
        """
        ...

    def get_positions(self, symbol: Optional[str] = None) -> List[Position]:
        """
        Get current positions.

        Args:
            symbol: Optional symbol filter

        Returns:
            List of Position objects
        """
        ...

    def close_position(
        self,
        symbol: str,
        side: PositionSide,
        quantity: Optional[float] = None,
    ) -> List[Trade]:
        """
        Close a position.

        Args:
            symbol: Trading pair
            side: Position side to close
            quantity: Quantity to close (None = all)

        Returns:
            List of executed trades
        """
        ...

    def set_leverage(self, symbol: str, leverage: int) -> bool:
        """
        Set position leverage.

        Args:
            symbol: Trading pair
            leverage: Leverage multiplier

        Returns:
            True if successful
        """
        ...
