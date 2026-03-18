# dgbit Architecture with NNG Abstraction

## Current Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              dgbit Platform                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                        Frontend (Vue 3)                           │   │
│  │  - Dashboard                                                      │   │
│  │  - Backtest results                                               │   │
│  │  - Job management                                                 │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                   │ HTTP                                 │
│                                   ▼                                      │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                     API Service (FastAPI)                         │   │
│  │  - REST endpoints                                                 │   │
│  │  - Request validation                                             │   │
│  │  - Job creation                                                   │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│           │                     │                     │                  │
│           │ NNG (IPC)           │ NNG (IPC)           │ NNG (IPC)        │
│           ▼                     ▼                     ▼                  │
│  ┌────────────────┐   ┌─────────────────┐   ┌─────────────────────┐    │
│  │  Data Service  │   │  Backtest Woker │   │  Strategy Service   │    │
│  │  (Market Data) │   │  (Backtesting)  │   │  (Signal Generation)│    │
│  └────────────────┘   └─────────────────┘   └─────────────────────┘    │
│           │                     │                     │                  │
│           ▼                     ▼                     ▼                  │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                     External Services                             │   │
│  │  - Bybit API                    - Other Exchanges (future)        │   │
│  │  - Cache (Parquet)              - Database (SQLite)               │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## NNG Abstraction Points

### 1. Command Bus (Request/Reply)

```
┌─────────────────────────────────────────────────────────────────┐
│                        Command Bus Pattern                        │
│                                                                  │
│  ┌─────────────┐                                                 │
│  │   API       │──────┐                                           │
│  └─────────────┘      │     ┌─────────────────────────────┐      │
│                       ├────▶│                             │      │
│  ┌─────────────┐      │     │     NNG Router/Socket      │      │
│  │   Worker    │◀─────┤     │                             │      │
│  └─────────────┘      │     │  - PUB/SUB for events      │      │
│                       ├────▶│  - REQ/REP for commands    │      │
│  ┌─────────────┐      │     │  - PUSH/PULL for queues    │      │
│  │   Client    │◀─────┘     │                             │      │
│  └─────────────┘            └─────────────────────────────┘      │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 2. Service Abstraction Matrix

| Service | Interface | NNG Pattern | Status |
|---------|-----------|-------------|--------|
| **Data Service** | `get_klines(symbol, interval)` | REQ/REP | ✅ Done |
| **Backtest Worker** | `run_backtest(config)` | REQ/REP | ✅ Done |
| **Job Service** | `create_job()`, `get_status()` | REQ/REP | ✅ Done |
| **Strategy Service** | `generate_signal(data)` | REQ/REP | ✅ Done |
| **Execution Service** | `execute_trade(signal)` | REQ/REP | ✅ Done |
| **Event Bus** | `publish()`, `subscribe()` | PUB/SUB | ✅ Done |

### 3. Event Bus (Pub/Sub)

```
┌─────────────────────────────────────────────────────────────────┐
│                        Event Bus Pattern                          │
│                                                                  │
│  ┌─────────────┐     ┌─────────────────────────────────────┐    │
│  │   Source    │────▶│           NNG PUB Socket            │    │
│  └─────────────┘     └─────────────────────────────────────┘    │
│                           │                                     │
│         ┌─────────────────┼─────────────────┐                   │
│         │                 │                 │                   │
│         ▼                 ▼                 ▼                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐    │
│  │  Dashboard  │  │   Logging   │  │   Metrics/Audit     │    │
│  │  (WebSocket)│  │  (Consumer) │  │   (Consumer)        │    │
│  └─────────────┘  └─────────────┘  └─────────────────────┘    │
│                                                                  │
│  Event Types:                                                    │
│  - job.created                                                  │
│  - job.started                                                  │
│  - job.completed                                                │
│  - job.failed                                                   │
│  - trade.executed                                               │
│  - signal.generated                                             │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 4. Proposed NNG Socket Layout

```
IPC Address              Pattern    Purpose
─────────────────────────────────────────────────────────────────
ipc:///tmp/dgbit_cmd.ipc    REQ/REP   Command bus (sync operations)
ipc:///tmp/dgbit_evt.ipc    PUB/SUB   Event bus (async events)
ipc:///tmp/dgbit_queue.ipc  PUSH/PULL Job queue (worker distribution)
ipc:///tmp/dgbit_data.ipc   REQ/REP   Data service (market data)
```

### 5. Service Protocol Definition

```python
# Common message format for all NNG services
class ServiceMessage(BaseModel):
    command: str          # Command name
    payload: dict         # Command arguments
    request_id: str       # For request/response correlation
    timestamp: datetime   # Message timestamp
    source: str           # Sending service name
    priority: int = 0     # Priority (0=normal, 1=high)

class EventMessage(BaseModel):
    event_type: str       # Event type (e.g., "job.completed")
    data: dict            # Event payload
    timestamp: datetime   # Event timestamp
    source: str           # Event source
```

### 6. Service Registry Pattern

```
┌─────────────────────────────────────────────────────────────────┐
│                     Service Registry                             │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Services register themselves on startup:                │   │
│  │                                                          │   │
│  │  {                                                         │   │
│  │    "name": "backtest_worker",                             │   │
│  │    "address": "ipc:///tmp/dgbit_cmd.ipc",                 │   │
│  │    "capabilities": ["backtest", "simulation"],            │   │
│  │    "status": "ready"                                      │   │
│  │  }                                                         │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  Router dispatches based on "command" field:                    │
│  - "backtest.*"  → Backtest Worker                              │   │
│  - "data.*"      → Data Service                                 │   │
│  - "strategy.*"  → Strategy Service                             │   │
│  - "trade.*"     → Execution Service                            │   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 7. Implementation Priority

| Priority | Service | Status |
|----------|---------|--------|
| 1 | Data Service | ✅ Done |
| 2 | Job Service | ✅ Done |
| 3 | Event Bus | ✅ Done |
| 4 | Strategy Service | ✅ Done |
| 5 | Execution Service | ✅ Done |
| 6 | Orchestrator | ✅ Done |

### 8. Example: Unified Service Client

```python
from dgbit_services import ServiceClient, create_client

# Create client with auto-discovery
client = create_client(
    name="api",
    commands=["data", "backtest", "job"],
)

# Use any service transparently
klines = await client.data.get_klines("BTCUSDT", "1")
job = await client.backtest.run(config=config)
status = await client.job.get_status("job-123")

# Publish events
client.emit("trade.executed", {"symbol": "BTCUSDT", "side": "buy"})
```

### 9. Cross-Market Arbitrage Support

```
┌─────────────────────────────────────────────────────────────────┐
│                  Multi-Exchange Data Flow                        │
│                                                                  │
│  ┌─────────────┐                                                 │
│  │  Strategy   │                                                 │
│  │  (Signal)   │                                                 │
│  └──────┬──────┘                                                 │
│         │                                                        │
│         ▼                                                        │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                   Arbitrage Service                      │    │
│  │                                                          │    │
│  │  ┌───────────┐  ┌───────────┐  ┌───────────────┐        │    │
│  │  │ Bybit     │  │ Binance   │  │ Coinbase      │        │    │
│  │  │ Adapter   │  │ Adapter   │  │ Adapter       │        │    │
│  │  └─────┬─────┘  └─────┬─────┘  └───────┬───────┘        │    │
│  │        │              │                │                 │    │
│  │        └──────────────┼────────────────┘                 │    │
│  │                       ▼                                  │    │
│  │              ┌─────────────────┐                         │    │
│  │              │  Price Comparator│                         │    │
│  │              │  (NNG PULL)     │                         │    │
│  │              └────────┬────────┘                         │    │
│  │                       │                                  │    │
│  │                       ▼                                  │    │
│  │              ┌─────────────────┐                         │    │
│  │              │ Arbitrage Signal│                         │    │
│  │              │ Generator       │                         │    │
│  │              └─────────────────┘                         │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 10. Running the Service Bus

The service bus is started via the orchestrator:

```bash
cd dgbit-api

# Start all services with the orchestrator
poetry run python -m dgbit_services.orchestrator

# Or run individual services
poetry run python -m dgbit_services.events
poetry run python -m dgbit_services.data
poetry run python -m dgbit_services.jobs
poetry run python -m dgbit_services.strategy
poetry run python -m dgbit_services.execution
```

### 11. Service Dependencies

```
                    ┌─────────────────┐
                    │  Service Bus    │
                    │  Orchestrator   │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
              ▼              ▼              ▼
    ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
    │ Event Bus   │  │ Data Service│  │ Job Queue   │
    │ (PUB/SUB)   │  │ (REQ/REP)   │  │ (PUSH/PULL) │
    └──────┬──────┘  └──────┬──────┘  └──────┬──────┘
           │                │                │
           │                ▼                │
           │       ┌──────────────┐          │
           │       │ Strategy Svc │◀─────────┤
           │       │ (REQ/REP)    │          │
           │       └──────┬───────┘          │
           │              │                  │
           │              ▼                  │
           │       ┌──────────────┐          │
           └──────▶│ Execution    │◀─────────┘
                   │ Service      │
                   │ (REQ/REP)    │
                   └──────────────┘
```

### 12. Complete Service Matrix

| Service | Pattern | Address | Dependencies |
|---------|---------|---------|--------------|
| Event Bus | PUB/SUB | `ipc:///tmp/dgbit_evt.ipc` | None |
| Data Service | REQ/REP | `ipc:///tmp/dgbit_data.ipc` | Event Bus |
| Job Queue | REQ/REP | `ipc:///tmp/dgbit_jobs.ipc` | Event Bus |
| Strategy Service | REQ/REP | `ipc:///tmp/dgbit_strategy.ipc` | Event Bus, Data Service |
| Execution Service | REQ/REP | `ipc:///tmp/dgbit_execution.ipc` | Event Bus |

### 13. API Integration

All services are accessible via the FastAPI endpoints:

```python
# Data Service
GET /data/klines?symbol=BTCUSDT&interval=1h
GET /data/symbols

# Strategy Service
GET /strategies
POST /strategies/wavelet_reversal/signal

# Execution Service
POST /execution/orders
GET /execution/positions
GET /execution/balance

# Job Queue
POST /backtests
GET /jobs
```

What aspect would you like to dive deeper into?
