# dgbit Documentation

**Professional Algorithmic Trading Framework for Bybit**

Build, backtest, and deploy crypto trading strategies with confidence.

---

## What is dgbit?

dgbit is a production-ready algorithmic trading framework designed for cryptocurrency traders and developers. It provides everything you need to research, backtest, and execute trading strategies on Bybit spot markets.

<div class="grid cards" markdown>

-   :material-rocket-launch:{ .lg .middle } **Quick Start**

    ---

    Get up and running with dgbit in minutes

    [:octicons-arrow-right-24: Getting Started](getting-started/quickstart.md)

-   :material-chart-line:{ .lg .middle } **Trading Strategies**

    ---

    Learn how to use and create trading strategies

    [:octicons-arrow-right-24: Strategy Guide](guides/strategies.md)

-   :material-flask:{ .lg .middle } **Backtesting**

    ---

    Test your strategies with historical data

    [:octicons-arrow-right-24: Backtesting Guide](guides/backtesting.md)

-   :material-docker:{ .lg .middle } **Docker Deployment**

    ---

    Deploy dgbit with Docker in production

    [:octicons-arrow-right-24: Docker Guide](deployment/docker.md)

</div>

## Key Features

### Multi-Strategy Support
dgbit includes several built-in trading strategies and makes it easy to create your own:

- **Wavelet Reversal** - Daubechies wavelet decomposition for trend reversal detection
- **MA Crossover** - Classic moving average crossover signals
- **RSI** - Relative Strength Index momentum strategy
- **Bollinger Bands** - Volatility-based breakout detection

### Comprehensive Backtesting
Test your strategies against historical data before risking real capital:

- In-memory simulation engine
- Detailed performance metrics (win rate, drawdown, profit factor)
- Interactive Plotly HTML reports
- Configurable transaction fees and slippage

### Production-Ready Architecture
Built for real-world deployment:

- FastAPI REST API with WebSocket support
- NNG-based service bus for scalable execution
- Vue 3 web dashboard for monitoring
- Docker-ready with multi-container orchestration

## Installation

=== "pip"

    ```bash
    pip install dgbit
    ```

=== "Docker"

    ```bash
    docker pull cryptuon/dgbit
    ```

=== "From Source"

    ```bash
    git clone https://github.com/cryptuon/dgbit.git
    cd dgbit
    pip install -e ".[dev]"
    ```

## Quick Example

```python
from dgbit_core.backtesting import Backtester, BacktestConfig
from dgbit_core.trading.strategy import WaveletReversalStrategy
from dgbit_core.data.data_fetcher import BybitDataFetcher

# Fetch historical data
fetcher = BybitDataFetcher()
data = fetcher.get_kline_data("BTCUSDT", interval="15", limit=1000)

# Run backtest
backtester = Backtester(config=BacktestConfig(initial_capital=10000.0))
backtester.strategy = WaveletReversalStrategy()
result = backtester.run(data)

print(f"Total Return: {result.metrics['total_return']:.2%}")
print(f"Win Rate: {result.metrics['win_rate']:.2%}")
```

## Community

- **GitHub Issues**: [Report bugs or request features](https://github.com/cryptuon/dgbit/issues)
- **Discussions**: [Ask questions and share ideas](https://github.com/cryptuon/dgbit/discussions)

## License

dgbit is released under the [MIT License](https://github.com/cryptuon/dgbit/blob/main/LICENSE).

!!! warning "Disclaimer"
    Trading cryptocurrencies involves significant risk. This software is provided for educational and research purposes only. Past performance does not guarantee future results. Always test strategies thoroughly before using real funds.
