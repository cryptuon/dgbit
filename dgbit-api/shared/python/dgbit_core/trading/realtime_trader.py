import time
from typing import Optional
from dgbit_core.data.data_fetcher import BybitDataFetcher
from dgbit_core.trading.strategy import TradingStrategy
from dgbit_core.trading.position import Position
import pandas as pd
class RealtimeTrader:
    def __init__(self, api_key: str, api_secret: str):
        self.data_fetcher = BybitDataFetcher(api_key, api_secret)
        self.strategy = TradingStrategy()
        self.current_position: Optional[Position] = None
        self.historical_data = pd.DataFrame()
        
    def update_model(self, symbol: str):
        """Update the model with recent data"""
        new_data = self.data_fetcher.get_kline_data(symbol)
        self.historical_data = pd.concat([self.historical_data, new_data]).drop_duplicates()
        self.strategy.train(self.historical_data)
    
    def handle_new_data(self, kline_df: pd.DataFrame):
        """Handle incoming real-time data"""
        self.historical_data = pd.concat([self.historical_data, kline_df]).tail(1000)
        
        if self.current_position:
            current_price = float(kline_df['close'].iloc[-1])
            if (current_price >= self.current_position.take_profit_price or 
                current_price <= self.current_position.stop_loss_price):
                # Exit position
                self.exit_position(current_price, kline_df['timestamp'].iloc[-1])
        else:
            # Check for new entry
            should_enter, predicted_return = self.strategy.should_enter_trade(self.historical_data)
            if should_enter:
                self.enter_position(kline_df)
    
    def run(self, symbol: str):
        """Run the real-time trading loop"""
        print(f"Starting real-time trading for {symbol}")
        
        # Initial data load and model training
        self.update_model(symbol)
        
        # Start streaming
        self.data_fetcher.stream_klines(symbol, self.handle_new_data)
        
        # Update model periodically
        while True:
            time.sleep(600)  # Update model every 10 minutes
            self.update_model(symbol) 
