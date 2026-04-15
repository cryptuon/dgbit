# Configuration

This guide covers all configuration options for dgbit.

## Environment Variables

dgbit uses environment variables for configuration. Create a `.env` file in the `dgbit-api` directory:

```bash
cp dgbit-api/.env.example dgbit-api/.env
```

### Core Settings

| Variable | Description | Default |
|----------|-------------|---------|
| `ENVIRONMENT` | Runtime environment (`development`, `production`) | `development` |
| `LOG_LEVEL` | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) | `INFO` |
| `APP_NAME` | Application name | `dgbit` |

### Bybit API Settings

| Variable | Description | Default |
|----------|-------------|---------|
| `BYBIT_API_KEY` | Your Bybit API key | (required for trading) |
| `BYBIT_API_SECRET` | Your Bybit API secret | (required for trading) |
| `BYBIT_TESTNET` | Use Bybit testnet | `true` |

### Trading Defaults

| Variable | Description | Default |
|----------|-------------|---------|
| `DEFAULT_SYMBOL` | Default trading pair | `BTCUSDT` |
| `DEFAULT_INTERVAL` | Default candle interval (minutes) | `1` |

### Service Bus (NNG)

| Variable | Description | Default |
|----------|-------------|---------|
| `NNG_COMMAND_ADDRESS` | Command bus address | `ipc:///tmp/dgbit_cmd.ipc` |
| `NNG_EVENT_ADDRESS` | Event bus address | `ipc:///tmp/dgbit_evt.ipc` |
| `NNG_JOB_QUEUE_ADDRESS` | Job queue address | `ipc:///tmp/dgbit_queue.ipc` |

## Example .env File

```env
# Environment
ENVIRONMENT=development
LOG_LEVEL=INFO

# Bybit API (get from https://www.bybit.com/app/user/api-management)
BYBIT_API_KEY=your_api_key_here
BYBIT_API_SECRET=your_api_secret_here
BYBIT_TESTNET=true

# Trading defaults
DEFAULT_SYMBOL=BTCUSDT
DEFAULT_INTERVAL=15

# Service bus
NNG_COMMAND_ADDRESS=ipc:///tmp/dgbit_cmd.ipc
NNG_EVENT_ADDRESS=ipc:///tmp/dgbit_evt.ipc
```

## Getting Bybit API Keys

1. Log in to [Bybit](https://www.bybit.com/)
2. Go to **Account** > **API Management**
3. Click **Create New Key**
4. Enable permissions:
    - **Read** - Required for data fetching
    - **Trade** - Required for order execution (optional)
5. Copy the API key and secret
6. Add to your `.env` file

!!! warning "API Key Security"
    - Never commit API keys to version control
    - Use testnet keys for development
    - Restrict API key permissions to what's needed
    - Set IP restrictions when possible

## Testnet vs Mainnet

For development and testing, use Bybit's testnet:

```env
BYBIT_TESTNET=true
```

Get testnet API keys from [testnet.bybit.com](https://testnet.bybit.com/).

For production with real funds:

```env
BYBIT_TESTNET=false
```

## Backtest Configuration

Configure backtests programmatically:

```python
from dgbit_core.backtesting import BacktestConfig

config = BacktestConfig(
    initial_capital=10000.0,    # Starting capital
    transaction_fee=0.001,      # 0.1% per trade
    train_split=0.7,            # 70% train, 30% test
    report_dir="reports",       # Where to save reports
)
```

## Strategy Configuration

Each strategy has its own parameters:

```python
from dgbit_core.trading.strategy import WaveletReversalStrategy

strategy = WaveletReversalStrategy(
    min_signal_threshold=0.75,  # Minimum signal to enter
    take_profit_pct=0.02,       # 2% take profit
    stop_loss_pct=0.01,         # 1% stop loss
    lookback_period=20,         # Candles to analyze
)
```

See [Built-in Strategies](../reference/strategies-ref.md) for all strategy parameters.

## Docker Configuration

When running with Docker, pass environment variables:

```bash
docker run -e BYBIT_API_KEY=xxx -e BYBIT_API_SECRET=xxx cryptuon/dgbit
```

Or use docker-compose with an env file:

```yaml
# docker-compose.yml
services:
  api:
    env_file:
      - .env
```

## Logging Configuration

dgbit uses loguru for structured logging. Configure via environment:

```env
LOG_LEVEL=DEBUG  # See all logs
LOG_LEVEL=INFO   # Standard logging
LOG_LEVEL=ERROR  # Errors only
```

### JSON Logging

For production, enable JSON logging:

```python
# In your code
from dgbit_api.core.logging import setup_logging
setup_logging(log_level="INFO", json_format=True)
```

## Database Configuration

dgbit uses SQLite by default for job tracking:

```python
# Default location
DATABASE_URL=sqlite://db/dgbit.db
```

The database is created automatically on first run.

## Next Steps

- [Trading Strategies](../guides/strategies.md) - Configure and use strategies
- [Docker Deployment](../deployment/docker.md) - Production configuration
- [Configuration Reference](../reference/configuration.md) - Complete reference
