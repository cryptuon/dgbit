# Backtesting Guide

Learn how to backtest trading strategies with historical data using dgbit's backtesting engine.

## Overview

Backtesting simulates how a strategy would have performed on historical data. This helps you:

- Evaluate strategy performance before risking real capital
- Compare different strategies objectively
- Optimize strategy parameters
- Understand risk characteristics

## Basic Backtesting

### Step 1: Fetch Historical Data

```python
from dgbit_core.data.data_fetcher import BybitDataFetcher

fetcher = BybitDataFetcher()
data = fetcher.get_kline_data(
    symbol="BTCUSDT",
    interval="15",    # 15-minute candles
    limit=2000,       # Number of candles
)

print(f"Data range: {data['timestamp'].min()} to {data['timestamp'].max()}")
```

### Step 2: Configure the Backtest

```python
from dgbit_core.backtesting import BacktestConfig

config = BacktestConfig(
    initial_capital=10000.0,    # Starting capital in USDT
    transaction_fee=0.001,      # 0.1% trading fee
    train_split=0.7,            # Use 70% for training, 30% for testing
    report_dir="reports",       # Where to save reports
)
```

### Step 3: Select a Strategy

```python
from dgbit_core.trading.strategy import WaveletReversalStrategy

strategy = WaveletReversalStrategy(
    min_signal_threshold=0.75,
    take_profit_pct=0.02,
    stop_loss_pct=0.01,
)
```

### Step 4: Run the Backtest

```python
from dgbit_core.backtesting import Backtester

backtester = Backtester(config=config)
backtester.strategy = strategy
result = backtester.run(data)
```

### Step 5: Analyze Results

```python
# Performance metrics
print(f"Total Trades: {result.metrics['total_trades']}")
print(f"Win Rate: {result.metrics['win_rate']:.2%}")
print(f"Total Return: {result.metrics['total_return']:.2%}")
print(f"Max Drawdown: {result.metrics['max_drawdown']:.2%}")
print(f"Profit Factor: {result.metrics['profit_factor']:.2f}")
print(f"Avg Trade Duration: {result.metrics['avg_duration']:.1f} minutes")

# Trade details
for trade in result.trades[:5]:
    print(f"{trade.timestamp}: {trade.action} @ {trade.price:.2f}")
```

## Understanding Metrics

### Win Rate
Percentage of profitable trades.

$$\text{Win Rate} = \frac{\text{Winning Trades}}{\text{Total Trades}}$$

**Good values:** > 50% for trend following, > 55% for mean reversion

### Total Return
Overall percentage gain/loss on initial capital.

$$\text{Total Return} = \frac{\text{Final Capital} - \text{Initial Capital}}{\text{Initial Capital}}$$

### Maximum Drawdown
Largest peak-to-trough decline during the backtest.

$$\text{Max Drawdown} = \max\left(\frac{\text{Peak} - \text{Trough}}{\text{Peak}}\right)$$

**Good values:** < 20% for conservative, < 40% for aggressive strategies

### Profit Factor
Ratio of gross profits to gross losses.

$$\text{Profit Factor} = \frac{\text{Total Profits}}{\text{Total Losses}}$$

**Good values:** > 1.5 (profitable), > 2.0 (excellent)

### Sharpe Ratio
Risk-adjusted return measure.

$$\text{Sharpe} = \frac{\text{Mean Return} - \text{Risk Free Rate}}{\text{Std Dev of Returns}}$$

**Good values:** > 1.0 (acceptable), > 2.0 (excellent)

## Advanced Backtesting

### Parameter Optimization

Test different parameter combinations:

```python
from dgbit_core.backtesting import Backtester, BacktestConfig
from dgbit_core.trading.strategy import WaveletReversalStrategy

results = []

# Grid search over parameters
for threshold in [0.6, 0.7, 0.8, 0.9]:
    for tp in [0.015, 0.02, 0.025, 0.03]:
        for sl in [0.005, 0.01, 0.015]:
            strategy = WaveletReversalStrategy(
                min_signal_threshold=threshold,
                take_profit_pct=tp,
                stop_loss_pct=sl,
            )
            
            backtester = Backtester(config=config)
            backtester.strategy = strategy
            result = backtester.run(data)
            
            results.append({
                'threshold': threshold,
                'take_profit': tp,
                'stop_loss': sl,
                'return': result.metrics['total_return'],
                'win_rate': result.metrics['win_rate'],
                'max_drawdown': result.metrics['max_drawdown'],
            })

# Find best parameters
import pandas as pd
df = pd.DataFrame(results)
best = df.loc[df['return'].idxmax()]
print(f"Best parameters: {best}")
```

### Walk-Forward Analysis

Test strategy robustness with rolling windows:

```python
from datetime import timedelta

def walk_forward_backtest(data, strategy_class, window_size=500, step_size=100):
    """
    Walk-forward backtesting with rolling training/testing windows.
    """
    results = []
    
    for i in range(0, len(data) - window_size, step_size):
        window_data = data.iloc[i:i + window_size]
        
        backtester = Backtester(config=config)
        backtester.strategy = strategy_class()
        result = backtester.run(window_data)
        
        results.append({
            'start': window_data['timestamp'].iloc[0],
            'end': window_data['timestamp'].iloc[-1],
            'return': result.metrics['total_return'],
            'trades': result.metrics['total_trades'],
        })
    
    return pd.DataFrame(results)

# Run walk-forward analysis
wf_results = walk_forward_backtest(data, WaveletReversalStrategy)
print(f"Average return across windows: {wf_results['return'].mean():.2%}")
print(f"Consistency: {(wf_results['return'] > 0).mean():.2%} profitable windows")
```

### Multi-Asset Backtesting

Test across multiple trading pairs:

```python
symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"]
portfolio_results = {}

for symbol in symbols:
    data = fetcher.get_kline_data(symbol, interval="15", limit=1000)
    
    backtester = Backtester(config=config)
    backtester.strategy = WaveletReversalStrategy()
    result = backtester.run(data)
    
    portfolio_results[symbol] = result.metrics

# Compare performance
for symbol, metrics in portfolio_results.items():
    print(f"{symbol}: Return={metrics['total_return']:.2%}, "
          f"Win Rate={metrics['win_rate']:.2%}")
```

## Backtest Reports

dgbit generates interactive HTML reports with Plotly:

```python
# Reports are saved automatically
result = backtester.run(data)

# Report location
print(f"Report saved to: {config.report_dir}/backtest_report.html")
```

The report includes:

- **Price Chart**: Candlestick chart with entry/exit markers
- **Equity Curve**: Capital over time
- **Trade Table**: Detailed trade list
- **Metrics Summary**: Key performance statistics

## Via the API

Schedule backtests through the REST API:

```python
import httpx
import time

# Schedule backtest
response = httpx.post(
    "http://localhost:8000/api/backtests",
    json={
        "symbol": "BTCUSDT",
        "interval": "15",
        "limit": 1000,
        "initial_capital": 10000.0,
        "transaction_fee": 0.001,
    }
)
job = response.json()
job_id = job['job_id']

# Poll for completion
while True:
    status = httpx.get(f"http://localhost:8000/api/jobs/{job_id}").json()
    if status['status'] in ['completed', 'failed']:
        break
    time.sleep(1)

# Get results
if status['status'] == 'completed':
    print(f"Results: {status['result']}")
```

## Best Practices

### Avoid Overfitting

- Use out-of-sample testing (train/test split)
- Perform walk-forward analysis
- Don't optimize too many parameters
- Test on multiple market conditions

### Account for Realistic Costs

- Include transaction fees
- Account for slippage (especially for larger orders)
- Consider funding rates for perpetuals

### Validate Data Quality

```python
# Check for missing data
print(f"Missing values: {data.isnull().sum().sum()}")

# Check for gaps
data['time_diff'] = data['timestamp'].diff()
gaps = data[data['time_diff'] > pd.Timedelta(minutes=20)]
print(f"Data gaps: {len(gaps)}")
```

### Document Your Tests

Keep records of:

- Strategy parameters tested
- Data ranges used
- Performance metrics
- Observations and insights

## Next Steps

- [Custom Strategies](custom-strategies.md) - Build your own strategies
- [Live Trading](live-trading.md) - Move from backtest to live
- [Strategy Reference](../reference/strategies-ref.md) - All strategy parameters
