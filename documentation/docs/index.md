# dgbit Documentation

**Algorithmic Trading Framework for Bybit**

Backtest and execute crypto trading strategies against Bybit markets.

---

## What is dgbit?

dgbit is an algorithmic trading framework that bundles a strategy framework, an in-memory backtester, a FastAPI service, an NNG-based service bus, and a Vue 3 dashboard. The shipped data fetcher and live trader integrate with Bybit via the `pybit` SDK. Bybit's spot category is the default; the underlying `BybitAdapter` also accepts `linear` (USDT-M perpetuals) and `inverse` categories.

The `dgbit_data.adapters` package additionally contains scaffolding for Binance, Coinbase, and OKX (via `ccxt`), but the runtime data fetcher (`BybitDataFetcher`) and `RealtimeTrader` are Bybit-only today.

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

### Built-in Strategies

Four strategies register themselves with the global `strategy_registry` at import time:

- **`wavelet_reversal`** (`WaveletReversalStrategy`) - delegates to `PricePredictor`, which uses a Daubechies wavelet decomposition
- **`ma_crossover`** (`MACrossoverStrategy`) - SMA/EMA/WMA crossover, configurable via `ma_type`
- **`rsi`** (`RSIStrategy`) - RSI overbought/oversold thresholding
- **`bollinger_bands`** (`BollingerBandStrategy`) - position of the close within the bands, no separate breakout mode

All four inherit from `BaseStrategy` and emit a signal in the `[0.0, 1.0]` range.

### Backtesting

- In-memory simulation in `dgbit_core.backtesting.Backtester`
- Train/test split (`train_split`, default `0.7`)
- Metrics: `total_trades`, `win_rate`, `total_return`, `max_drawdown`, `profit_factor`, `avg_return`, `avg_duration`, `final_capital`, `wins`, `losses`
- Interactive Plotly HTML report via `Backtester.plot_results(...)`
- Configurable `transaction_fee` (applied on both entry and exit); slippage is not modelled

### Service Architecture

- FastAPI app exposing endpoints under `/api`
- NNG (`pynng`) command/event/data sockets, addresses configured via env vars
- Vue 3 dashboard in `dgbit-ui/`
- `docker-compose.yml` with `api`, `backtest-worker`, `ui`, and `data-service` services

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

# BybitDataFetcher requires Bybit API credentials (use testnet=True for read-only public data)
fetcher = BybitDataFetcher(api_key="", api_secret="", testnet=True)
data = fetcher.get_kline_data("BTCUSDT", interval="15", limit=1000)

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
