# dgbit – Bybit Trading Bot Framework

## Overview

dgbit is an experimental framework for researching and running short-term strategies on Bybit spot markets. The system provides:

- High-frequency kline data fetching from Bybit
- Multiple trading strategies (Wavelet Reversal, MA Crossover, RSI, Bollinger Bands)
- Backtesting simulation with HTML reporting
- Service bus architecture for scalable execution
- Vue 3 web interface for monitoring and control

## Key Capabilities

- **Data Fetching**: Fetch high-resolution kline data via `pybit` and `ccxt`
- **Trading Strategies**: Pluggable strategy system with registry pattern
- **Backtesting**: In-memory simulation with Plotly HTML reports
- **Position Management**: Position tracking with entry/exit logic
- **Service Bus**: NNG-based messaging for inter-process communication

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              dgbit Platform                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                        Frontend (Vue 3)                           │   │
│  │  - Dashboard    - Charts & Trading    - Portfolio                 │   │
│  │  - Strategies   - System                                             │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                   │ HTTP / WebSocket                     │
│                                   ▼                                      │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                     API Service (FastAPI)                         │   │
│  │  - REST endpoints    - Request validation    - Job management     │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│           │                     │                     │                  │
│           │ NNG (IPC)           │ NNG (IPC)           │ NNG (IPC)        │
│           ▼                     ▼                     ▼                  │
│  ┌────────────────┐   ┌─────────────────┐   ┌─────────────────────┐    │
│  │  Data Service  │   │  Backtest Worker│   │  Strategy Service   │    │
│  │  (Market Data) │   │  (Backtesting)  │   │  (Signal Generation)│    │
│  └────────────────┘   └─────────────────┘   └─────────────────────┘    │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## Project Structure

```
dgbit/
├── dgbit-api/                         # FastAPI backend service
│   ├── src/dgbit_api/                # Main API application
│   │   ├── api/                      # API routes
│   │   ├── core/                     # Configuration, logging
│   │   ├── db/                       # Database models
│   │   ├── infra/                    # Infrastructure (messaging)
│   │   ├── services/                 # Business services
│   │   └── workers/                  # Background workers
│   ├── src/dgbit_services/           # Service bus (NNG)
│   ├── src/dgbit_data/               # Data layer (adapters)
│   ├── src/dgbit_cli/                # CLI tools
│   ├── shared/python/dgbit_core/     # Trading logic
│   │   ├── backtesting/              # Backtesting engine
│   │   ├── trading/                  # Strategy, position, execution
│   │   ├── data/                     # Data fetching
│   │   └── models/                   # Predictor models
│   └── tests/                        # API tests
│
├── dgbit-ui/                         # Vue 3 frontend
│   ├── src/
│   │   ├── views/                    # Page components
│   │   ├── stores/                   # Pinia stores
│   │   ├── services/                 # API client
│   │   └── router/                   # Vue Router
│   └── ...
│
└── docs/                             # Documentation
```

## Getting Started

### Prerequisites

- Python 3.11+
- Poetry 1.6+
- Node.js 18+ (for frontend)
- Bybit API key/secret (for live trading)

### Backend Setup

```bash
cd dgbit-api
poetry install
```

### Frontend Setup

```bash
cd dgbit-ui
npm install
```

### Environment Configuration

Create a `.env` file in `dgbit-api/` with your credentials:

```env
BYBIT_API_KEY=...
BYBIT_API_SECRET=...
BYBIT_TESTNET=false
```

### Running the Platform

**API Service:**

```bash
cd dgbit-api
poetry run uvicorn dgbit_api.main:app --reload
```

**Frontend Development:**

```bash
cd dgbit-ui
npm run dev
```

**Background Workers:**

```bash
cd dgbit-api
poetry run python -m dgbit_api.workers.backtest_runner
```

### Running Tests

```bash
cd dgbit-api
poetry run pytest
```

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Health check |
| `POST /backtests` | Create a backtest job |
| `GET /backtests/{id}` | Get backtest results |
| `GET /jobs` | List all jobs |
| `GET /data/klines` | Get kline data |
| `GET /data/symbols` | List trading pairs |
| `GET /strategies` | List available strategies |
| `POST /execution/orders` | Place an order |
| `GET /execution/positions` | Get open positions |

## Strategies

### Built-in Strategies

1. **Wavelet Reversal** - Daubechies wavelet-based reversal signals
2. **MA Crossover** - Moving average crossover strategy
3. **RSI** - Relative Strength Index strategy
4. **Bollinger Bands** - Bollinger Bands breakout strategy

### Creating Custom Strategies

```python
from dgbit_core.trading.strategy import BaseStrategy, StrategyMetadata, SignalType, strategy_registry

class MyStrategy(BaseStrategy):
    metadata = StrategyMetadata(
        name="my_strategy",
        description="My custom strategy",
        author="You",
        version="0.1.0",
        signal_type=SignalType.MOMENTUM,
        parameters={...},
    )

    def generate_signal(self, data):
        # Your logic here
        return signal_value

strategy_registry.register(MyStrategy)
```

## Backtesting

```python
from dgbit_core.backtesting import Backtester, BacktestConfig
from dgbit_core.trading import create_strategy

# Create strategy
strategy = create_strategy("wavelet_reversal", min_signal_threshold=0.75)

# Configure backtest
config = BacktestConfig(
    initial_capital=10000.0,
    transaction_fee=0.001,
)

# Run backtest
backtester = Backtester(config=config)
backtester.strategy = strategy
result = backtester.run(market_data)

# Results include metrics and HTML report
print(f"Win Rate: {result.metrics['win_rate']:.2%}")
```

## Service Bus

The platform uses NNG (nanomsg) for inter-process communication:

| Socket | Pattern | Purpose |
|--------|---------|---------|
| `ipc:///tmp/dgbit_cmd.ipc` | REQ/REP | Command bus |
| `ipc:///tmp/dgbit_evt.ipc` | PUB/SUB | Event bus |
| `ipc:///tmp/dgbit_queue.ipc` | PUSH/PULL | Job queue |

## Documentation

- [Architecture](docs/ARCHITECTURE.md) - System architecture overview
- [Strategy Architecture](docs/STRATEGY_ARCHITECTURE.md) - Extensible strategy system
- [NNG Architecture](docs/NNG_ARCHITECTURE.md) - Service bus design
- [Roadmap](docs/ROADMAP.md) - Development roadmap
- [Development Guide](docs/DEVELOPMENT_GUIDE.md) - Setup and contribution guide

## License

MIT
