# REST API Reference

Complete reference for dgbit's REST API endpoints.

## Base URL

```
http://localhost:8000/api
```

## Endpoints

### System

#### Health Check

Check service health and get statistics.

```http
GET /api/health
```

**Response:**

```json
{
    "service": "dgbit",
    "environment": "development",
    "status": "ok",
    "version": "0.2.0",
    "stats": {
        "total_jobs": 42,
        "pending": 2,
        "running": 1,
        "completed": 35,
        "failed": 4
    }
}
```

---

### Backtests

#### Schedule Backtest

Create a new backtest job.

```http
POST /api/backtests
Content-Type: application/json
```

**Request Body:**

```json
{
    "symbol": "BTCUSDT",
    "interval": "15",
    "limit": 1000,
    "initial_capital": 10000.0,
    "transaction_fee": 0.001
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `symbol` | string | No | Trading pair (default: BTCUSDT) |
| `interval` | string | No | Candle interval in minutes (default: 1) |
| `limit` | integer | No | Number of candles (default: 1000) |
| `initial_capital` | number | No | Starting capital (default: 10000.0) |
| `transaction_fee` | number | No | Fee per trade (default: 0.001) |

**Response:**

```json
{
    "job_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "running",
    "message": "Backtest job dispatched"
}
```

---

### Jobs

#### List Jobs

Get all jobs with optional filtering.

```http
GET /api/jobs
GET /api/jobs?status=completed
GET /api/jobs?job_type=backtest
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `status` | string | Filter by status (pending, running, completed, failed) |
| `job_type` | string | Filter by type (backtest, data_sync, signal) |

**Response:**

```json
{
    "jobs": [
        {
            "id": 1,
            "uuid": "550e8400-e29b-41d4-a716-446655440000",
            "job_type": "backtest",
            "status": "completed",
            "payload": {"symbol": "BTCUSDT", "limit": 1000},
            "result": {"total_trades": 15, "win_rate": 0.6},
            "created_at": "2024-01-15T10:30:00Z",
            "completed_at": "2024-01-15T10:30:45Z"
        }
    ],
    "total": 1
}
```

#### Get Job

Get a specific job by UUID.

```http
GET /api/jobs/{uuid}
```

**Response:**

```json
{
    "id": 1,
    "uuid": "550e8400-e29b-41d4-a716-446655440000",
    "job_type": "backtest",
    "status": "completed",
    "payload": {
        "symbol": "BTCUSDT",
        "interval": "15",
        "limit": 1000
    },
    "result": {
        "total_trades": 15,
        "win_rate": 0.60,
        "total_return": 0.12,
        "max_drawdown": 0.05
    },
    "error": null,
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:30:45Z",
    "started_at": "2024-01-15T10:30:01Z",
    "completed_at": "2024-01-15T10:30:45Z"
}
```

#### Cancel Job

Cancel a pending or running job.

```http
POST /api/jobs/{uuid}/cancel
```

**Response:**

```json
{
    "job_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "cancelled",
    "message": "Job cancelled successfully"
}
```

---

### Data

#### Get Klines

Fetch OHLCV candlestick data.

```http
GET /api/data/klines?symbol=BTCUSDT&interval=15&limit=100
```

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `symbol` | string | Yes | Trading pair (e.g., BTCUSDT) |
| `interval` | string | No | Candle interval in minutes (default: 1) |
| `limit` | integer | No | Number of candles (default: 100, max: 1000) |

**Response:**

```json
{
    "symbol": "BTCUSDT",
    "interval": "15",
    "data": [
        {
            "timestamp": "2024-01-15T10:00:00Z",
            "open": 42150.50,
            "high": 42200.00,
            "low": 42100.00,
            "close": 42180.25,
            "volume": 125.5
        }
    ]
}
```

#### List Symbols

Get available trading pairs.

```http
GET /api/data/symbols
```

**Response:**

```json
{
    "symbols": [
        {"symbol": "BTCUSDT", "base": "BTC", "quote": "USDT"},
        {"symbol": "ETHUSDT", "base": "ETH", "quote": "USDT"},
        {"symbol": "SOLUSDT", "base": "SOL", "quote": "USDT"}
    ]
}
```

---

### Strategies

#### List Strategies

Get all available trading strategies.

```http
GET /api/strategies
```

**Response:**

```json
{
    "strategies": [
        {
            "name": "wavelet_reversal",
            "description": "Wavelet-based reversal detection strategy",
            "signal_type": "mean_reversion",
            "parameters": {
                "min_signal_threshold": {"type": "float", "default": 0.75},
                "take_profit_pct": {"type": "float", "default": 0.02},
                "stop_loss_pct": {"type": "float", "default": 0.01}
            }
        },
        {
            "name": "ma_crossover",
            "description": "Moving average crossover strategy",
            "signal_type": "trend_following",
            "parameters": {
                "fast_period": {"type": "int", "default": 12},
                "slow_period": {"type": "int", "default": 26}
            }
        }
    ]
}
```

#### Generate Signal

Generate a trading signal using a specific strategy.

```http
POST /api/strategies/{name}/signal
Content-Type: application/json
```

**Request Body:**

```json
{
    "symbol": "BTCUSDT",
    "interval": "15",
    "limit": 100,
    "parameters": {
        "min_signal_threshold": 0.8
    }
}
```

**Response:**

```json
{
    "strategy": "wavelet_reversal",
    "symbol": "BTCUSDT",
    "timestamp": "2024-01-15T10:30:00Z",
    "signal": {
        "value": 0.82,
        "direction": "long",
        "confidence": "high"
    },
    "recommended_action": {
        "action": "buy",
        "entry_price": 42150.00,
        "take_profit": 42993.00,
        "stop_loss": 41728.50
    }
}
```

---

### Execution

#### Place Order

Place a trading order.

```http
POST /api/execution/orders
Content-Type: application/json
```

**Request Body:**

```json
{
    "symbol": "BTCUSDT",
    "side": "buy",
    "order_type": "market",
    "quantity": 0.001,
    "stop_loss": 41000,
    "take_profit": 44000
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `symbol` | string | Yes | Trading pair |
| `side` | string | Yes | Order side (buy, sell) |
| `order_type` | string | Yes | Order type (market, limit) |
| `quantity` | number | Yes | Order quantity |
| `price` | number | No | Limit price (required for limit orders) |
| `stop_loss` | number | No | Stop loss price |
| `take_profit` | number | No | Take profit price |

**Response:**

```json
{
    "order_id": "12345678",
    "symbol": "BTCUSDT",
    "side": "buy",
    "order_type": "market",
    "quantity": 0.001,
    "status": "filled",
    "filled_price": 42150.00,
    "created_at": "2024-01-15T10:30:00Z"
}
```

#### Get Positions

Get open positions.

```http
GET /api/execution/positions
```

**Response:**

```json
{
    "positions": [
        {
            "symbol": "BTCUSDT",
            "side": "long",
            "quantity": 0.001,
            "entry_price": 42150.00,
            "current_price": 42300.00,
            "unrealized_pnl": 0.15,
            "unrealized_pnl_pct": 0.36,
            "take_profit": 44000,
            "stop_loss": 41000,
            "opened_at": "2024-01-15T10:30:00Z"
        }
    ]
}
```

---

## Error Handling

### Error Response Format

```json
{
    "detail": "Error description",
    "status_code": 400
}
```

### Common Error Codes

| Code | Description |
|------|-------------|
| 400 | Bad Request - Invalid parameters |
| 404 | Not Found - Resource doesn't exist |
| 422 | Validation Error - Invalid request body |
| 500 | Internal Server Error |

### Example Error

```http
POST /api/backtests
Content-Type: application/json

{"limit": -1}
```

```json
{
    "detail": [
        {
            "loc": ["body", "limit"],
            "msg": "ensure this value is greater than 0",
            "type": "value_error.number.not_gt"
        }
    ],
    "status_code": 422
}
```

## Rate Limiting

Currently, no rate limiting is implemented. For production, implement rate limiting via reverse proxy (nginx, traefik) or middleware.

## Pagination

Endpoints that return lists support pagination:

```http
GET /api/jobs?offset=0&limit=20
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `offset` | integer | 0 | Number of items to skip |
| `limit` | integer | 20 | Number of items to return |
