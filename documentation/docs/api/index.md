# API Reference

dgbit provides multiple interfaces for interacting with the platform.

## Available APIs

<div class="grid cards" markdown>

-   :material-api:{ .lg .middle } **REST API**

    ---

    HTTP endpoints for backtesting, data, and execution

    [:octicons-arrow-right-24: REST API Reference](rest-api.md)

-   :material-websocket:{ .lg .middle } **WebSocket**

    ---

    Real-time event streaming and updates

    [:octicons-arrow-right-24: WebSocket Reference](websocket.md)

-   :material-language-python:{ .lg .middle } **Python SDK**

    ---

    Direct Python interface to dgbit components

    [:octicons-arrow-right-24: Python SDK](python-sdk.md)

</div>

## Quick Reference

### Base URL

```
http://localhost:8000/api
```

### Authentication

Currently, dgbit doesn't require authentication for local deployment. For production, implement authentication via reverse proxy or custom middleware.

### Response Format

All API responses are JSON:

```json
{
    "status": "ok",
    "data": { ... }
}
```

Error responses:

```json
{
    "detail": "Error message",
    "status_code": 400
}
```

## Common Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Service health check |
| `/api/backtests` | POST | Schedule backtest job |
| `/api/jobs` | GET | List all jobs |
| `/api/strategies` | GET | List available strategies |
| `/api/data/klines` | GET | Fetch OHLCV data |
