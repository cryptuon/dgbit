from typing import List, Dict
import pandas as pd
from pybit.unified_trading import HTTP
from datetime import datetime, timedelta

class BybitDataFetcher:
    def __init__(self, api_key: str, api_secret: str, testnet: bool = False):
        self.session = HTTP(
            testnet=testnet,
            api_key=api_key,
            api_secret=api_secret
        )
        
    def get_kline_data(
        self,
        symbol: str,
        interval: str = "1",    # 1 minute
        lookback_hours: int = 24,  # Get 24 hours of minute data
        limit: int = 1000
    ) -> pd.DataFrame:
        """
        Fetch granular kline data from Bybit
        """
        limit = min(1000, lookback_hours * 60)  # Bybit max limit is 1000
        
        response = self.session.get_kline(
            category="spot",
            symbol=symbol,
            interval=interval,
            limit=limit
        )
        
        df = pd.DataFrame(response["result"]["list"])
        print(df.columns)
        df.columns = ["timestamp", "open", "high", "low", "close", "volume", "turnover"]
        df = df.astype(float)
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        
        # Add momentum indicators
        df['price_change'] = df['close'].pct_change()
        df['volume_change'] = df['volume'].pct_change()
        
        # Add rolling statistics for last 10 minutes
        df['rolling_volatility'] = df['price_change'].rolling(10).std()
        df['rolling_volume'] = df['volume'].rolling(10).mean()
        
        return df.sort_values("timestamp")

    def stream_klines(self, symbol: str, callback):
        """
        Stream real-time kline data
        """
        from pybit.unified_trading import WebSocket
        
        ws = WebSocket(
            testnet=False,
            channel_type="spot"
        )
        
        def handle_kline(message):
            data = message['data']
            kline_df = pd.DataFrame([{
                'timestamp': pd.to_datetime(data['timestamp'], unit='ms'),
                'open': float(data['open']),
                'high': float(data['high']),
                'low': float(data['low']),
                'close': float(data['close']),
                'volume': float(data['volume']),
                'turnover': float(data['turnover'])
            }])
            callback(kline_df)

        ws.kline_stream(
            symbol=symbol,
            interval="1",
            callback=handle_kline
        )

    def get_volatile_pairs(self, min_volume: float = 1000000) -> List[str]:
        """
        Find volatile pairs with sufficient volume
        """
        tickers = self.session.get_tickers(category="spot")
        pairs = []
        
        for ticker in tickers["result"]["list"]:
            volume_24h = float(ticker["volume24h"])
            low_price_24h = float(ticker["lowPrice24h"])
            high_price_24h = float(ticker["highPrice24h"])
            turnover_24h = float(ticker["turnover24h"])

            price_change = abs(float(ticker["price24hPcnt"]))
            
            # Lets look at the low and high price 24h and the turnover 24h
            if turnover_24h > min_volume and (high_price_24h - low_price_24h)/low_price_24h > 0.05:
                pairs.append(ticker["symbol"])
        print(pairs)

        return pairs 