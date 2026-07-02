<p align="center">
  <h1 align="center">dgbit</h1>
  <p align="center">
    <strong>Professional Algorithmic Trading Framework for Bybit</strong>
  </p>
  <p align="center">
    Build, backtest, and deploy crypto trading strategies with confidence
  </p>
</p>

<p align="center">
  <a href="https://pypi.org/project/dgbit/"><img src="https://img.shields.io/pypi/v/dgbit?color=blue&label=PyPI" alt="PyPI version"></a>
  <a href="https://pypi.org/project/dgbit/"><img src="https://img.shields.io/pypi/pyversions/dgbit" alt="Python versions"></a>
  <a href="https://hub.docker.com/r/cryptuon/dgbit"><img src="https://img.shields.io/docker/v/cryptuon/dgbit?label=Docker" alt="Docker"></a>
  <a href="https://github.com/cryptuon/dgbit/actions"><img src="https://img.shields.io/github/actions/workflow/status/cryptuon/dgbit/test.yml?label=Tests" alt="Tests"></a>
  <a href="https://docs.cryptuon.com/dgbit"><img src="https://img.shields.io/badge/docs-mkdocs-blue" alt="Documentation"></a>
  <a href="https://github.com/cryptuon/dgbit/blob/main/LICENSE"><img src="https://img.shields.io/github/license/cryptuon/dgbit" alt="License"></a>
</p>

<p align="center">
  <a href="https://docs.cryptuon.com/dgbit">Documentation</a> |
  <a href="https://docs.cryptuon.com/dgbit/getting-started/quickstart/">Quick Start</a> |
  <a href="https://docs.cryptuon.com/dgbit/guides/strategies/">Strategy Guide</a> |
  <a href="https://github.com/cryptuon/dgbit/issues">Issues</a>
</p>

**[🌐 Site](https://dgbit.cryptuon.com/) · [📚 Docs](https://docs.cryptuon.com/dgbit/) · [📦 PyPI package](https://pypi.org/project/dgbit/) · [🔬 Cryptuon Research](https://github.com/cryptuon)**

---

## Why dgbit?

**dgbit** is a production-ready algorithmic trading framework designed for cryptocurrency traders who want to:

- **Backtest strategies** with historical data before risking real capital
- **Execute automated trades** on Bybit spot markets with confidence
- **Build custom strategies** using a pluggable, extensible architecture
- **Monitor positions** through a modern web dashboard
- **Deploy anywhere** with Docker support

Whether you're a quantitative trader developing new strategies or a developer building trading automation, dgbit provides the infrastructure you need.

## Key Features

| Feature | Description |
|---------|-------------|
| **Multi-Strategy Support** | Wavelet reversal, MA crossover, RSI, Bollinger Bands, and custom strategies |
| **Comprehensive Backtesting** | In-memory simulation with detailed metrics and interactive Plotly reports |
| **Real-time Execution** | Live trading on Bybit with position tracking and risk management |
| **Service Bus Architecture** | Scalable NNG-based messaging for high-frequency operations |
| **REST API** | Full-featured FastAPI backend with WebSocket support |
| **Web Dashboard** | Vue 3 frontend for monitoring and control |
| **Docker Ready** | One-command deployment with docker-compose |

## Quick Start

### Installation

```bash
# Install from PyPI
pip install dgbit

# Or with Docker
docker pull cryptuon/dgbit
```

### Run Your First Backtest

```python
from dgbit_core.backtesting import Backtester, BacktestConfig
from dgbit_core.trading.strategy import WaveletReversalStrategy
from dgbit_core.data.data_fetcher import BybitDataFetcher

# Fetch historical data
fetcher = BybitDataFetcher()
data = fetcher.get_kline_data("BTCUSDT", interval="15", limit=1000)

# Configure and run backtest
config = BacktestConfig(
    initial_capital=10000.0,
    transaction_fee=0.001,
)

backtester = Backtester(config=config)
backtester.strategy = WaveletReversalStrategy(min_signal_threshold=0.75)
result = backtester.run(data)

# View results
print(f"Total Return: {result.metrics['total_return']:.2%}")
print(f"Win Rate: {result.metrics['win_rate']:.2%}")
print(f"Max Drawdown: {result.metrics['max_drawdown']:.2%}")
```

### Start the API Server

```bash
# Using pip installation
dgbit-api

# Or with uvicorn directly
uvicorn dgbit_api.main:app --host 0.0.0.0 --port 8000
```

### Docker Deployment

```bash
# Clone the repository
git clone https://github.com/cryptuon/dgbit.git
cd dgbit

# Configure environment
cp dgbit-api/.env.example dgbit-api/.env
# Edit .env with your Bybit API credentials

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f api
```

## Architecture

```
                           dgbit Platform
    ┌─────────────────────────────────────────────────────────────┐
    │                                                              │
    │   ┌──────────────────────────────────────────────────────┐  │
    │   │                   Vue 3 Dashboard                     │  │
    │   │    Charts | Portfolio | Strategies | Monitoring       │  │
    │   └──────────────────────────────────────────────────────┘  │
    │                           │ HTTP / WebSocket                 │
    │                           ▼                                  │
    │   ┌──────────────────────────────────────────────────────┐  │
    │   │                 FastAPI REST API                      │  │
    │   │   /backtests  /jobs  /data  /strategies  /execution   │  │
    │   └──────────────────────────────────────────────────────┘  │
    │            │                │                │               │
    │            │ NNG IPC        │ NNG IPC        │ NNG IPC       │
    │            ▼                ▼                ▼               │
    │   ┌──────────────┐ ┌──────────────┐ ┌──────────────────┐   │
    │   │ Data Service │ │   Backtest   │ │ Strategy Service │   │
    │   │ (Market Data)│ │    Worker    │ │ (Signal Gen)     │   │
    │   └──────────────┘ └──────────────┘ └──────────────────┘   │
    │                                                              │
    │   ┌──────────────────────────────────────────────────────┐  │
    │   │               Shared Trading Core                     │  │
    │   │  Strategies | Backtesting | Position Tracking | Data  │  │
    │   └──────────────────────────────────────────────────────┘  │
    │                           │                                  │
    └───────────────────────────┼──────────────────────────────────┘
                                ▼
                         Bybit Exchange API
```

## Built-in Trading Strategies

| Strategy | Type | Description |
|----------|------|-------------|
| **Wavelet Reversal** | Mean Reversion | Daubechies wavelet decomposition for trend reversal detection |
| **MA Crossover** | Trend Following | Classic moving average crossover signals |
| **RSI** | Momentum | Relative Strength Index overbought/oversold signals |
| **Bollinger Bands** | Volatility | Breakout detection using Bollinger Band boundaries |

### Creating Custom Strategies

```python
from dgbit_core.trading.strategy import (
    BaseStrategy, 
    StrategyMetadata, 
    SignalType,
    strategy_registry
)

class MyMomentumStrategy(BaseStrategy):
    """Custom momentum-based trading strategy."""
    
    metadata = StrategyMetadata(
        name="my_momentum",
        description="Custom momentum strategy with volume confirmation",
        author="Your Name",
        version="1.0.0",
        signal_type=SignalType.MOMENTUM,
        parameters={
            "lookback_period": {"type": "int", "default": 14},
            "volume_threshold": {"type": "float", "default": 1.5},
        },
    )
    
    def generate_signal(self, data):
        # Your strategy logic here
        momentum = data['close'].pct_change(self.lookback_period).iloc[-1]
        volume_ratio = data['volume'].iloc[-1] / data['volume'].mean()
        
        if momentum > 0.02 and volume_ratio > self.volume_threshold:
            return 0.8  # Strong buy signal
        elif momentum < -0.02 and volume_ratio > self.volume_threshold:
            return 0.2  # Strong sell signal
        return 0.5  # Neutral

# Register your strategy
strategy_registry.register(MyMomentumStrategy)
```

## API Reference

### REST Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Service health and stats |
| `/api/backtests` | POST | Schedule a backtest job |
| `/api/jobs` | GET | List all jobs |
| `/api/jobs/{uuid}` | GET | Get job status and results |
| `/api/data/klines` | GET | Fetch OHLCV data |
| `/api/data/symbols` | GET | List available trading pairs |
| `/api/strategies` | GET | List available strategies |
| `/api/strategies/{name}/signal` | POST | Generate trading signal |
| `/api/execution/orders` | POST | Place an order |
| `/api/execution/positions` | GET | Get open positions |

### WebSocket Events

```javascript
// Connect to event stream
const ws = new WebSocket('ws://localhost:8000/api/ws/events');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Event:', data.type, data.payload);
};

// Event types: job.created, job.completed, job.failed, 
//              trade.entered, trade.exited, signal.generated
```

## Configuration

Create a `.env` file with your settings:

```env
# Bybit API (required for live trading)
BYBIT_API_KEY=your_api_key
BYBIT_API_SECRET=your_api_secret
BYBIT_TESTNET=true

# Application settings
ENVIRONMENT=development
LOG_LEVEL=INFO

# Default trading parameters
DEFAULT_SYMBOL=BTCUSDT
DEFAULT_INTERVAL=1

# Service bus addresses
NNG_COMMAND_ADDRESS=ipc:///tmp/dgbit_cmd.ipc
NNG_EVENT_ADDRESS=ipc:///tmp/dgbit_evt.ipc
```

## Documentation

Comprehensive documentation is available at **[docs.cryptuon.com/dgbit](https://docs.cryptuon.com/dgbit)**:

- [Installation Guide](https://docs.cryptuon.com/dgbit/getting-started/installation/)
- [Quick Start Tutorial](https://docs.cryptuon.com/dgbit/getting-started/quickstart/)
- [Strategy Development](https://docs.cryptuon.com/dgbit/guides/strategies/)
- [Backtesting Guide](https://docs.cryptuon.com/dgbit/guides/backtesting/)
- [API Reference](https://docs.cryptuon.com/dgbit/api/rest-api/)
- [Docker Deployment](https://docs.cryptuon.com/dgbit/deployment/docker/)

## Development

```bash
# Clone repository
git clone https://github.com/cryptuon/dgbit.git
cd dgbit

# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest dgbit-api/tests/

# Run linting
ruff check .

# Start development server
cd dgbit-api
uvicorn dgbit_api.main:app --reload
```

## Contributing

Contributions are welcome! Please read our [Contributing Guide](https://docs.cryptuon.com/dgbit/contributing/) for details on:

- Code style and standards
- Pull request process
- Development setup

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Disclaimer

**Trading cryptocurrencies involves significant risk.** This software is provided for educational and research purposes only. Past performance does not guarantee future results. Always test strategies thoroughly with paper trading before using real funds. The authors are not responsible for any financial losses incurred while using this software.

---

## Part of Cryptuon Research

`dgbit` is one of [20 open-source blockchain-infrastructure projects](https://www.cryptuon.com/projects) from **[Cryptuon Research](https://www.cryptuon.com)** — blockchain theory, shipped as protocols.

**Related projects:** [PolyBot](https://polybot.cryptuon.com/) · [Moby Market](https://mobymarket.cryptuon.com/) · [Mentat](https://mentat.cryptuon.com/)

Docs: [docs.cryptuon.com/dgbit](https://docs.cryptuon.com/dgbit/) · Contact: [contact@cryptuon.com](mailto:contact@cryptuon.com)

---

<p align="center">
  Made with care by <a href="https://github.com/cryptuon">Cryptuon</a>
</p>
