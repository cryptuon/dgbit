# Data Flow

How data moves through the dgbit system.

## Backtest Flow

```
┌──────────┐    POST /backtests    ┌─────────┐
│  Client  │ ───────────────────▶  │   API   │
└──────────┘                       └─────────┘
                                        │
                                        │ 1. Create Job record
                                        ▼
                                   ┌─────────┐
                                   │ SQLite  │
                                   └─────────┘
                                        │
                                        │ 2. Dispatch via NNG
                                        ▼
                                   ┌─────────┐
                                   │ Command │
                                   │   Bus   │
                                   └─────────┘
                                        │
                                        │ 3. Process job
                                        ▼
                                   ┌─────────┐
                                   │ Worker  │
                                   └─────────┘
                                        │
                    ┌───────────────────┼───────────────────┐
                    ▼                   │                   ▼
              ┌─────────┐               │             ┌─────────┐
              │  Bybit  │               │             │ Strategy│
              │   API   │               │             │  Core   │
              └─────────┘               │             └─────────┘
                    │                   │                   │
                    │ 4. Fetch data     │ 5. Run backtest   │
                    └───────────────────┼───────────────────┘
                                        │
                                        │ 6. Store results
                                        ▼
                                   ┌─────────┐
                                   │ SQLite  │
                                   └─────────┘
                                        │
                                        │ 7. Publish event
                                        ▼
                                   ┌─────────┐
                                   │  Event  │
                                   │   Bus   │
                                   └─────────┘
                                        │
                                        │ 8. Notify client
                                        ▼
                                   ┌─────────┐
                                   │WebSocket│
                                   └─────────┘
```

### Step-by-Step

1. **Client Request**: User submits backtest via API
2. **Job Creation**: API creates job record in SQLite
3. **Dispatch**: Job dispatched to worker via NNG command bus
4. **Data Fetch**: Worker fetches OHLCV data from Bybit
5. **Backtest**: Strategy processes data, generates signals
6. **Store**: Results stored in SQLite, HTML report generated
7. **Event**: job.completed event published
8. **Notify**: WebSocket delivers update to client

## Signal Generation Flow

```
┌──────────┐   POST /strategies/*/signal   ┌─────────┐
│  Client  │ ────────────────────────────▶ │   API   │
└──────────┘                               └─────────┘
                                                │
                                                │ 1. Request signal
                                                ▼
                                          ┌───────────┐
                                          │ Strategy  │
                                          │  Client   │
                                          └───────────┘
                                                │
                                                │ 2. Fetch data
                                                ▼
                                          ┌───────────┐
                                          │   Data    │
                                          │  Client   │
                                          └───────────┘
                                                │
                                                │ 3. Get OHLCV
                                                ▼
                                          ┌───────────┐
                                          │  Bybit    │
                                          │   API     │
                                          └───────────┘
                                                │
                                                │ 4. Generate signal
                                                ▼
                                          ┌───────────┐
                                          │ Strategy  │
                                          │   Core    │
                                          └───────────┘
                                                │
                                                │ 5. Return signal
                                                ▼
                                          ┌───────────┐
                                          │  Client   │
                                          └───────────┘
```

## Live Trading Flow

```
┌───────────────────────────────────────────────────────────┐
│                    Trading Loop                            │
│                                                            │
│  ┌──────────┐     ┌──────────┐     ┌──────────┐          │
│  │  Fetch   │ ──▶ │ Generate │ ──▶ │ Execute  │          │
│  │   Data   │     │  Signal  │     │  Trade   │          │
│  └──────────┘     └──────────┘     └──────────┘          │
│       │                │                │                  │
│       ▼                ▼                ▼                  │
│  ┌──────────┐     ┌──────────┐     ┌──────────┐          │
│  │   OHLCV  │     │  Signal  │     │  Order   │          │
│  │   Data   │     │  0.0-1.0 │     │ Executed │          │
│  └──────────┘     └──────────┘     └──────────┘          │
│                                         │                  │
│                                         ▼                  │
│                                    ┌──────────┐           │
│                                    │ Position │           │
│                                    │ Tracking │           │
│                                    └──────────┘           │
│                                         │                  │
│                    ┌────────────────────┼────────────────┐│
│                    ▼                    ▼                ▼│
│               ┌────────┐          ┌────────┐      ┌────────┐
│               │   TP   │          │   SL   │      │ Timeout│
│               │  Hit   │          │  Hit   │      │        │
│               └────────┘          └────────┘      └────────┘
│                    │                    │              │    │
│                    └────────────────────┼──────────────┘    │
│                                         ▼                   │
│                                    ┌──────────┐            │
│                                    │  Close   │            │
│                                    │ Position │            │
│                                    └──────────┘            │
│                                         │                   │
│                                         ▼                   │
│                                    ┌──────────┐            │
│                                    │  Record  │            │
│                                    │  P&L     │            │
│                                    └──────────┘            │
│                                                            │
└───────────────────────────────────────────────────────────┘
```

## Data Structures

### OHLCV DataFrame

```python
# Columns after fetch and feature engineering
{
    'timestamp': datetime,      # Candle time
    'open': float,             # Open price
    'high': float,             # High price
    'low': float,              # Low price
    'close': float,            # Close price
    'volume': float,           # Trading volume
    'price_change': float,     # Close-to-close change
    'rolling_volatility': float,  # 20-period volatility
    'rolling_volume': float,   # 20-period avg volume
    'symbol': str,             # Trading pair
}
```

### Signal

```python
{
    'value': float,           # 0.0 (sell) to 1.0 (buy)
    'direction': str,         # 'long' or 'short'
    'confidence': str,        # 'low', 'medium', 'high'
    'strategy': str,          # Strategy name
    'timestamp': datetime,    # Generation time
}
```

### Trade

```python
{
    'timestamp': datetime,    # Trade time
    'action': str,           # 'entry' or 'exit'
    'symbol': str,           # Trading pair
    'price': float,          # Execution price
    'quantity': float,       # Position size
    'side': str,             # 'long' or 'short'
    'pnl': float,            # Realized P&L (exit only)
    'pnl_pct': float,        # P&L percentage
    'duration_minutes': float,  # Time in position
    'exit_type': str,        # 'take_profit', 'stop_loss'
}
```

### Job

```python
{
    'id': int,               # Auto-increment ID
    'uuid': str,             # UUID for external reference
    'job_type': str,         # 'backtest', 'data_sync'
    'status': str,           # 'pending', 'running', 'completed'
    'payload': dict,         # Job parameters
    'result': dict,          # Job output
    'error': str,            # Error message if failed
    'created_at': datetime,
    'started_at': datetime,
    'completed_at': datetime,
}
```

## Caching Strategy

### Data Cache

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Request   │ ──▶ │   Check     │ ──▶ │   Bybit     │
│   Data      │     │   Cache     │     │   API       │
└─────────────┘     └─────────────┘     └─────────────┘
                          │                    │
                          │ Hit                │ Miss
                          ▼                    ▼
                    ┌─────────────┐     ┌─────────────┐
                    │   Return    │     │   Fetch &   │
                    │   Cached    │     │   Cache     │
                    └─────────────┘     └─────────────┘
```

Cache behaviour is configured in `dgbit_data.cache` and surfaced through the `use_cache` flag on `/api/data/klines`. TTLs and eviction policy are not currently exposed via configuration; consult the cache module for the active defaults.

## Error Propagation

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Error in  │ ──▶ │   Mark Job  │ ──▶ │   Publish   │
│   Worker    │     │   Failed    │     │   Event     │
└─────────────┘     └─────────────┘     └─────────────┘
                                              │
                    ┌─────────────────────────┼────────┐
                    ▼                         ▼        ▼
              ┌───────────┐           ┌───────────┐ ┌─────┐
              │  Log to   │           │  WebSocket│ │Alert│
              │  Loguru   │           │  Notify   │ │     │
              └───────────┘           └───────────┘ └─────┘
```
