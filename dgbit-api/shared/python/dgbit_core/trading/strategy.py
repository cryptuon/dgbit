from typing import Tuple
import pandas as pd
from dgbit_core.models.predictor import PricePredictor

class TradingStrategy:
    def __init__(self, 
                 min_buy_pressure: float = 0.75,  # Lower threshold for wavelet signals
                 take_profit: float = 0.002,      # 0.2% profit target
                 stop_loss: float = 0.005):       # 0.5% stop loss
        self.predictor = PricePredictor()
        self.min_buy_pressure = min_buy_pressure
        self.take_profit = take_profit
        self.stop_loss = stop_loss
        
    def train(self, historical_data: pd.DataFrame):
        """Train the prediction model"""
        self.predictor.train(historical_data)
        
    def should_enter_trade(self, data: pd.DataFrame) -> Tuple[bool, float]:
        """
        Determine if we should enter a trade based on buying pressure
        """
        buy_probability = self.predictor.predict(data)
        
        # Only enter if we have strong buying pressure signal
        should_enter = buy_probability > self.min_buy_pressure
        
        return should_enter, buy_probability
        
    def calculate_exit_prices(self, entry_price: float) -> Tuple[float, float]:
        """Calculate take profit and stop loss prices"""
        take_profit_price = entry_price * (1 + self.take_profit)
        stop_loss_price = entry_price * (1 - self.stop_loss)
        return take_profit_price, stop_loss_price 
