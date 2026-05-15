# Configuration Reference

Reference for configuration surfaced by the dgbit-api `Settings` class (`dgbit_api.core.config.Settings`). Environment variables not listed here are not consumed by `Settings`; some are consumed directly by `docker-compose.yml` interpolation or by service-specific code paths.

## Settings fields

| Env var | Field | Default |
|---------|-------|---------|
| `APP_NAME` | `app_name` | `dgbit-api` |
| `API_PREFIX` | `api_prefix` | `/api` |
| `ENVIRONMENT` | `environment` | `development` |
| `LOG_LEVEL` | `log_level` | `INFO` |
| `NNG_COMMAND_ADDRESS` | `nng_command_address` | `ipc:///tmp/dgbit_commands.ipc` |
| `NNG_EVENT_ADDRESS` | `nng_event_address` | `ipc:///tmp/dgbit_events.ipc` |
| `DEFAULT_SYMBOL` | `default_symbol` | `BTCUSDT` |
| `DEFAULT_INTERVAL` | `default_interval` | `1` |
| `BYBIT_API_KEY` | `bybit_api_key` | `""` |
| `BYBIT_API_SECRET` | `bybit_api_secret` | `""` |

## Compose-only or service-specific variables

These are referenced in `docker-compose.yml` or read ad-hoc from `os.getenv` but are **not** part of `Settings`:

- `BYBIT_TESTNET` (forwarded to API, worker, and data-service containers; defaults to `true` in compose)
- `NNG_DATA_ADDRESS` (used by the data-service container)

The HTTP bind host/port for the API server (`uvicorn`'s `--host` / `--port`) are command-line arguments — there are no `API_HOST` / `API_PORT` `Settings` fields.

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

### `BaseStrategy` common kwargs

Every strategy inherits these from `BaseStrategy.__init__`:

| Parameter | Default |
|-----------|---------|
| `min_signal_threshold` | `0.5` |
| `take_profit_pct` | `0.002` |
| `stop_loss_pct` | `0.005` |
| `position_size_pct` | `1.0` |

Subclasses override these defaults via their own `__init__` defaults (or their `metadata.parameters` schema).

### `WaveletReversalStrategy`

| Parameter | Default |
|-----------|---------|
| `min_signal_threshold` | `0.75` |
| `take_profit_pct` | `0.002` |
| `stop_loss_pct` | `0.005` |

The strategy currently exposes no `wavelet_level` or `lookback_period` constructor parameter; those values are fixed on the underlying `PricePredictor` (`level=3`, `window_size=60`).

### `MACrossoverStrategy`

| Parameter | Default | Notes |
|-----------|---------|-------|
| `fast_period` | `10` | `metadata.parameters` declares range `[2, 100]` |
| `slow_period` | `20` | range `[5, 200]` |
| `ma_type` | `"sma"` | one of `"sma"`, `"ema"`, `"wma"` |

### `RSIStrategy`

| Parameter | Default |
|-----------|---------|
| `period` | `14` |
| `oversold` | `30.0` |
| `overbought` | `70.0` |

### `BollingerBandStrategy`

| Parameter | Default |
|-----------|---------|
| `period` | `20` |
| `std_dev` | `2.0` |

The constructor keyword is `std_dev`, not `num_std`. There is no `mode` parameter; the strategy returns the close's relative position within the bands.

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

## Logging

Logging is configured by `dgbit_api.core.logging`. Set the `LOG_LEVEL` env var (default `INFO`) to control verbosity.

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
