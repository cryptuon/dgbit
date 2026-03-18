from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from enum import Enum


class PositionSide(str, Enum):
    LONG = "long"
    SHORT = "short"


class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"


class OrderStatus(str, Enum):
    PENDING = "pending"
    FILLED = "filled"
    CANCELLED = "cancelled"


@dataclass
class Order:
    """Order representation for backtesting and live trading."""
    symbol: str
    side: PositionSide
    order_type: OrderType
    quantity: float
    price: Optional[float] = None
    status: OrderStatus = OrderStatus.PENDING
    filled_at: Optional[datetime] = None
    filled_price: Optional[float] = None
    filled_quantity: float = 0.0
    created_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()


@dataclass
class Position:
    """Position representation with entry/exit tracking."""
    symbol: str
    side: PositionSide
    entry_price: float
    entry_time: datetime
    quantity: float
    take_profit_price: float
    stop_loss_price: float
    exit_price: Optional[float] = None
    exit_time: Optional[datetime] = None

    def __post_init__(self):
        self._is_open = True

    @property
    def is_open(self) -> bool:
        return self._is_open

    def return_pct(self) -> float:
        """Calculate return percentage."""
        if self.side == PositionSide.LONG:
            return (self.exit_price - self.entry_price) / self.entry_price
        else:
            return (self.entry_price - self.exit_price) / self.entry_price

    @property
    def duration(self):
        """Position duration in minutes."""
        if self.exit_time and self.entry_time:
            return (self.exit_time - self.entry_time).total_seconds() / 60
        return 0.0

    def close(self, exit_price: float, exit_time: datetime) -> None:
        """Close the position."""
        self.exit_price = exit_price
        self.exit_time = exit_time
        self._is_open = False

    def calculate_pnl(self, current_price: float) -> float:
        """Calculate unrealized PnL."""
        if self.side == PositionSide.LONG:
            return (current_price - self.entry_price) / self.entry_price
        else:
            return (self.entry_price - current_price) / self.entry_price
