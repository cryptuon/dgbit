# Quick Start

Get dgbit running and execute your first backtest in under 5 minutes.

## Prerequisites

- dgbit installed ([Installation Guide](installation.md))
- Python 3.11+

## Step 1: Create a Project Directory

```bash
mkdir my-trading-project
cd my-trading-project
```

## Step 2: Fetch Historical Data

```python
from dgbit_core.data.data_fetcher import BybitDataFetcher

# Create a data fetcher (no API keys needed for public data)
fetcher = BybitDataFetcher()

# Fetch 1000 candles of 15-minute BTCUSDT data
data = fetcher.get_kline_data(
    symbol="BTCUSDT",
    interval="15",  # 15 minutes
    limit=1000
)

print(f"Fetched {len(data)} candles")
print(data.head())
```

## Step 3: Run a Backtest

```python
from dgbit_core.backtesting import Backtester, BacktestConfig
from dgbit_core.trading.strategy import WaveletReversalStrategy

# Configure the backtest
config = BacktestConfig(
    initial_capital=10000.0,  # Starting with $10,000
    transaction_fee=0.001,    # 0.1% fee per trade
    train_split=0.7,          # 70% train, 30% test
)

# Create backtester with Wavelet Reversal strategy
backtester = Backtester(config=config)
backtester.strategy = WaveletReversalStrategy(
    min_signal_threshold=0.75,
    take_profit_pct=0.02,    # 2% take profit
    stop_loss_pct=0.01,      # 1% stop loss
)

# Run the backtest
result = backtester.run(data)

# Print results
print("\n=== Backtest Results ===")
print(f"Total Trades: {result.metrics['total_trades']}")
print(f"Win Rate: {result.metrics['win_rate']:.2%}")
print(f"Total Return: {result.metrics['total_return']:.2%}")
print(f"Max Drawdown: {result.metrics['max_drawdown']:.2%}")
print(f"Profit Factor: {result.metrics['profit_factor']:.2f}")
```

## Step 4: Generate a Report

```python
# The backtester automatically generates an HTML report
# Check the 'reports' directory
import os
print(f"Report saved to: {os.path.abspath('reports/')}")
```

Open the generated HTML file in your browser to see interactive charts.

## Step 5: Start the API Server

For a full web experience, start the API server:

=== "Direct"

    ```bash
    uvicorn dgbit_api.main:app --host 0.0.0.0 --port 8000 --reload
    ```

=== "Docker"

    ```bash
    docker-compose up api
    ```

Visit `http://localhost:8000/api/health` to verify it's running.

## Step 6: Schedule a Backtest via API

```python
import httpx

response = httpx.post(
    "http://localhost:8000/api/backtests",
    json={
        "symbol": "ETHUSDT",
        "interval": "15",
        "limit": 500,
        "initial_capital": 5000.0,
    }
)

job = response.json()
print(f"Job scheduled: {job['job_id']}")
```

## Full Example Script

Here's a complete script combining all steps:

```python
#!/usr/bin/env python3
"""
dgbit Quick Start Example
Run a backtest on BTCUSDT with the Wavelet Reversal strategy.
"""

from dgbit_core.backtesting import Backtester, BacktestConfig
from dgbit_core.trading.strategy import WaveletReversalStrategy
from dgbit_core.data.data_fetcher import BybitDataFetcher


def main():
    # Fetch data
    print("Fetching historical data...")
    fetcher = BybitDataFetcher()
    data = fetcher.get_kline_data("BTCUSDT", interval="15", limit=1000)
    print(f"Fetched {len(data)} candles from {data['timestamp'].min()} to {data['timestamp'].max()}")
    
    # Configure backtest
    config = BacktestConfig(
        initial_capital=10000.0,
        transaction_fee=0.001,
    )
    
    # Create strategy
    strategy = WaveletReversalStrategy(
        min_signal_threshold=0.75,
        take_profit_pct=0.02,
        stop_loss_pct=0.01,
    )
    
    # Run backtest
    print("\nRunning backtest...")
    backtester = Backtester(config=config)
    backtester.strategy = strategy
    result = backtester.run(data)
    
    # Print results
    print("\n" + "=" * 50)
    print("BACKTEST RESULTS")
    print("=" * 50)
    print(f"Strategy: {strategy.metadata.name}")
    print(f"Symbol: BTCUSDT")
    print(f"Initial Capital: ${config.initial_capital:,.2f}")
    print("-" * 50)
    print(f"Total Trades: {result.metrics['total_trades']}")
    print(f"Winning Trades: {result.metrics.get('winning_trades', 'N/A')}")
    print(f"Win Rate: {result.metrics['win_rate']:.2%}")
    print(f"Avg Return per Trade: {result.metrics['avg_return']:.2%}")
    print("-" * 50)
    print(f"Final Capital: ${result.metrics['final_capital']:,.2f}")
    print(f"Total Return: {result.metrics['total_return']:.2%}")
    print(f"Max Drawdown: {result.metrics['max_drawdown']:.2%}")
    print(f"Profit Factor: {result.metrics['profit_factor']:.2f}")
    print("=" * 50)
    
    return result


if __name__ == "__main__":
    main()
```

Save this as `quickstart.py` and run:

```bash
python quickstart.py
```

## What's Next?

Now that you've run your first backtest:

1. **Try different strategies** - See [Trading Strategies](../guides/strategies.md)
2. **Create custom strategies** - See [Custom Strategies](../guides/custom-strategies.md)
3. **Configure for live trading** - See [Configuration](configuration.md)
4. **Deploy with Docker** - See [Docker Deployment](../deployment/docker.md)
