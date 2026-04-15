# Configuration Reference

Complete reference of all configuration options.

## Environment Variables

### Application Settings

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `APP_NAME` | string | `dgbit` | Application name |
| `ENVIRONMENT` | string | `development` | Runtime environment |
| `LOG_LEVEL` | string | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |

### Bybit API

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `BYBIT_API_KEY` | string | `""` | Bybit API key |
| `BYBIT_API_SECRET` | string | `""` | Bybit API secret |
| `BYBIT_TESTNET` | boolean | `true` | Use Bybit testnet |

### Trading Defaults

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `DEFAULT_SYMBOL` | string | `BTCUSDT` | Default trading pair |
| `DEFAULT_INTERVAL` | string | `1` | Default candle interval (minutes) |

### Service Bus (NNG)

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `NNG_COMMAND_ADDRESS` | string | `ipc:///tmp/dgbit_cmd.ipc` | Command bus address |
| `NNG_EVENT_ADDRESS` | string | `ipc:///tmp/dgbit_evt.ipc` | Event bus address |
| `NNG_JOB_QUEUE_ADDRESS` | string | `ipc:///tmp/dgbit_queue.ipc` | Job queue address |
| `NNG_DATA_ADDRESS` | string | `ipc:///tmp/dgbit_data.ipc` | Data service address |

### API Server

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `API_HOST` | string | `0.0.0.0` | API bind host |
| `API_PORT` | integer | `8000` | API bind port |
| `API_PREFIX` | string | `/api` | API route prefix |

## BacktestConfig

Configuration for backtesting.

```python
from dgbit_core.backtesting import BacktestConfig

config = BacktestConfig(
    initial_capital=10000.0,
    transaction_fee=0.001,
    train_split=0.7,
    report_dir="reports",
)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `initial_capital` | float | `10000.0` | Starting capital in quote currency |
| `transaction_fee` | float | `0.001` | Fee per trade (0.001 = 0.1%) |
| `train_split` | float | `0.7` | Train/test split ratio |
| `report_dir` | string | `reports` | Directory for HTML reports |

## Strategy Parameters

### Common Parameters

All strategies support these parameters:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `take_profit_pct` | float | `0.02` | Take profit percentage |
| `stop_loss_pct` | float | `0.01` | Stop loss percentage |
| `min_signal_threshold` | float | `0.7` | Minimum signal to enter |

### WaveletReversalStrategy

| Parameter | Type | Default | Range | Description |
|-----------|------|---------|-------|-------------|
| `min_signal_threshold` | float | `0.75` | 0.0-1.0 | Signal threshold |
| `take_profit_pct` | float | `0.02` | 0.001-0.1 | Take profit % |
| `stop_loss_pct` | float | `0.01` | 0.001-0.1 | Stop loss % |
| `wavelet_level` | int | `3` | 1-5 | Decomposition level |

### MACrossoverStrategy

| Parameter | Type | Default | Range | Description |
|-----------|------|---------|-------|-------------|
| `fast_period` | int | `12` | 2-50 | Fast EMA period |
| `slow_period` | int | `26` | 10-200 | Slow EMA period |
| `take_profit_pct` | float | `0.03` | 0.001-0.1 | Take profit % |
| `stop_loss_pct` | float | `0.015` | 0.001-0.1 | Stop loss % |

### RSIStrategy

| Parameter | Type | Default | Range | Description |
|-----------|------|---------|-------|-------------|
| `period` | int | `14` | 2-50 | RSI period |
| `oversold` | int | `30` | 10-40 | Oversold threshold |
| `overbought` | int | `70` | 60-90 | Overbought threshold |
| `take_profit_pct` | float | `0.025` | 0.001-0.1 | Take profit % |
| `stop_loss_pct` | float | `0.012` | 0.001-0.1 | Stop loss % |

### BollingerBandStrategy

| Parameter | Type | Default | Range | Description |
|-----------|------|---------|-------|-------------|
| `period` | int | `20` | 5-50 | BB period |
| `num_std` | float | `2.0` | 1.0-3.0 | Standard deviations |
| `mode` | string | `mean_reversion` | - | `mean_reversion` or `breakout` |
| `take_profit_pct` | float | `0.02` | 0.001-0.1 | Take profit % |
| `stop_loss_pct` | float | `0.01` | 0.001-0.1 | Stop loss % |

## Bybit Intervals

Supported candle intervals:

| Interval | Minutes | Description |
|----------|---------|-------------|
| `1` | 1 | 1 minute |
| `3` | 3 | 3 minutes |
| `5` | 5 | 5 minutes |
| `15` | 15 | 15 minutes |
| `30` | 30 | 30 minutes |
| `60` | 60 | 1 hour |
| `120` | 120 | 2 hours |
| `240` | 240 | 4 hours |
| `360` | 360 | 6 hours |
| `720` | 720 | 12 hours |
| `D` | 1440 | 1 day |
| `W` | 10080 | 1 week |
| `M` | 43200 | 1 month |

## Logging Configuration

### Log Levels

| Level | Value | Description |
|-------|-------|-------------|
| `DEBUG` | 10 | Detailed debugging info |
| `INFO` | 20 | Normal operations |
| `WARNING` | 30 | Unexpected but handled |
| `ERROR` | 40 | Failures |
| `CRITICAL` | 50 | System failures |

### Log Format

```python
from dgbit_api.core.logging import setup_logging

# Standard format
setup_logging(log_level="INFO")

# JSON format (production)
setup_logging(log_level="INFO", json_format=True)
```

## Docker Configuration

### Resource Limits

```yaml
services:
  api:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G
```

### Health Check

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/api/health"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s
```
