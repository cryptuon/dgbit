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
    "service": "dgbit-api",
    "environment": "development",
    "status": "ok",
    "version": "0.2.0",
    "stats": { /* output of JobService.get_stats() */ }
}
```

`service` is the value of `Settings.app_name` (`dgbit-api` by default) and `environment` reflects `Settings.environment`.

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

**Response (worker dispatch succeeded):**

```json
{
    "job_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "running",
    "message": "Backtest job dispatched"
}
```

If the NNG dispatch fails, the API still returns 200 with the job's current status and a `warning` field instead of `message`. Inspect the response to determine whether the worker actually picked the job up.

---

### Jobs

#### List Jobs

Get all jobs with optional filtering.

```http
GET /api/jobs
GET /api/jobs?status=completed
GET /api/jobs?job_type=backtest
GET /api/jobs?limit=20
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `status` | `JobStatus` | Filter by status (`pending`, `running`, `completed`, `failed`, `cancelled`) |
| `job_type` | `JobType` | Filter by type (see `dgbit_api.db.models.JobType`) |
| `limit` | int | Max rows (1-100, default 50) |

**Response:** a JSON array of job objects (the endpoint does not wrap them in a `{jobs, total}` envelope):

```json
[
    {
        "id": 1,
        "uuid": "550e8400-e29b-41d4-a716-446655440000",
        "job_type": "backtest",
        "status": "completed",
        "payload": {"symbol": "BTCUSDT", "limit": 1000},
        "result": {"total_trades": 15, "win_rate": 0.6},
        "error": null,
        "created_at": "2024-01-15T10:30:00",
        "updated_at": "2024-01-15T10:30:45",
        "started_at": "2024-01-15T10:30:01",
        "completed_at": "2024-01-15T10:30:45"
    }
]
```

There is also a `GET /api/jobs/stats` endpoint that returns the same `stats` block as `/api/health`.

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

Cancel a pending or running job. Returns `400` if the job is not in `pending` or `running` status.

```http
POST /api/jobs/{job_uuid}/cancel
```

**Response:**

```json
{
    "job_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "cancelled"
}
```

Note: the route only marks the job row as cancelled in the database; it does not signal the worker.

---

### Data

#### Get Klines

Fetch OHLCV candlestick data via the data service.

```http
GET /api/data/klines?symbol=BTCUSDT&interval=1h&limit=100
```

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `symbol` | string | No | Trading pair (default `BTCUSDT`) |
| `interval` | string | No | Candle interval string (default `1h`) |
| `limit` | integer | No | Number of candles (1-1000, default 100) |
| `use_cache` | bool | No | Use cached data when available (default `true`) |

The response is whatever `DataServiceClient.get_klines(...)` returns from the data service over NNG; consult `dgbit_services.data` for the exact schema.

There are two helper endpoints for cache management:

- `GET /api/data/cache` returns the cache status.
- `DELETE /api/data/cache` clears the cache.

#### List Symbols

```http
GET /api/data/symbols?exchange=bybit
```

**Response:**

```json
{
    "exchange": "bybit",
    "symbols": ["BTCUSDT", "ETHUSDT", "..."],
    "count": 123
}
```

---

### Strategies

#### List Strategies

```http
GET /api/strategies
```

Proxies `StrategyClient.list_strategies()` over NNG; the response is the strategy service's payload (typically the strategy registry serialised by name). Built-in registered strategies are `wavelet_reversal`, `ma_crossover`, `rsi`, and `bollinger_bands`.

#### Generate Signal

```http
POST /api/strategies/{strategy_name}/signal?symbol=BTCUSDT
```

The endpoint accepts only the `symbol` query parameter; per-request parameter overrides are not supported through this route in the current build. The response is `StrategyClient.generate_signal(strategy_name, symbol)`'s output.

---

### Execution

All execution endpoints forward to `ExecutionClient` over NNG; their response shapes are whatever the execution service returns. The accepted request bodies and query parameters defined in FastAPI are:

#### Place Order

```http
POST /api/execution/orders
```

**Request body fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `symbol` | string | Yes | Trading pair |
| `side` | string | Yes | `"buy"` or `"sell"` |
| `quantity` | number | Yes | Order quantity |
| `order_type` | string | No | Defaults to `"market"` |
| `price` | number | No | Limit price |

There is no `stop_loss` / `take_profit` field at this layer.

#### Other endpoints

| Endpoint | Method | Notes |
|----------|--------|-------|
| `/api/execution/orders` | GET | Optional `symbol`, `status` query params |
| `/api/execution/orders/{order_id}` | GET | Fetch a single order |
| `/api/execution/orders/{order_id}` | DELETE | Cancel an order; requires `symbol` query param |
| `/api/execution/positions` | GET | Optional `symbol` filter |
| `/api/execution/balance` | GET | Account balance |
| `/api/execution/positions/close` | POST | Body: `{symbol, side}` (`side` defaults to `"both"`) |
| `/api/execution/ping` | GET | Health-checks the execution service |

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

There is no built-in rate limiting. Apply it at a reverse proxy (nginx, traefik) or in custom middleware.

## Pagination

`GET /api/jobs` accepts a `limit` query parameter (1-100, default 50). There is no `offset` parameter in the current build.
