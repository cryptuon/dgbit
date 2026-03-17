from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class Position:
    symbol: str
    entry_price: float
    entry_time: datetime
    take_profit_price: float
    stop_loss_price: float
    position_size: float
    exit_price: Optional[float] = None
    exit_time: Optional[datetime] = None
    
    @property
    def is_open(self) -> bool:
        return self.exit_price is None
    
    @property
    def duration(self) -> Optional[float]:
        if not self.exit_time:
            return None
        return (self.exit_time - self.entry_time).total_seconds() / 3600  # hours
    
    def return_pct(self) -> Optional[float]:
        if not self.exit_price:
            return None
        return (self.exit_price - self.entry_price) / self.entry_price