from dgbit_core.data.data_fetcher import BybitDataFetcher
from dgbit_core.backtesting.backtester import Backtester
import os
from dotenv import load_dotenv

def main():
    load_dotenv()
    
    # Initialize data fetcher
    fetcher = BybitDataFetcher(
        api_key=os.getenv('BYBIT_API_KEY'),
        api_secret=os.getenv('BYBIT_API_SECRET')
    )
    
    # Get volatile pairs
    pairs = fetcher.get_volatile_pairs()
    
    # Run backtest for each pair
    for pair in pairs[:5]:  # Test first 5 pairs
        print(f"Backtesting {pair}")
        
        # Get historical data
        data = fetcher.get_kline_data(pair, limit=500)
        
        # Run backtest
        backtester = Backtester()
        results = backtester.run(data)
        print(results)
        metrics = backtester.get_performance_metrics()
        
        print("Performance metrics:")
        for metric, value in metrics.items():
            print(f"{metric}: {value}")
        print("\n")

if __name__ == "__main__":
    main() 
