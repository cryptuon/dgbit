# Architecture Overview

High-level view of dgbit's system architecture.

## System Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              dgbit Platform                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                        Frontend (Vue 3)                           │   │
│  │  - Dashboard    - Charts & Trading    - Portfolio                 │   │
│  │  - Strategies   - System Monitoring                               │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                   │ HTTP / WebSocket                     │
│                                   ▼                                      │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                     API Service (FastAPI)                         │   │
│  │  - REST endpoints    - Request validation    - Job management     │   │
│  │  - WebSocket events  - Authentication        - Rate limiting      │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│           │                     │                     │                  │
│           │ NNG (IPC)           │ NNG (IPC)           │ NNG (IPC)        │
│           ▼                     ▼                     ▼                  │
│  ┌────────────────┐   ┌─────────────────┐   ┌─────────────────────┐    │
│  │  Data Service  │   │  Backtest Worker│   │  Strategy Service   │    │
│  │  (Market Data) │   │  (Backtesting)  │   │  (Signal Generation)│    │
│  └────────────────┘   └─────────────────┘   └─────────────────────┘    │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                     Shared Trading Core                           │   │
│  │  - Strategy Framework    - Backtesting Engine                     │   │
│  │  - Position Tracking     - Data Fetching                          │   │
│  │  - ML Models             - Risk Management                        │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                   │                                      │
└───────────────────────────────────┼──────────────────────────────────────┘
                                    ▼
                             Bybit Exchange API
```

## Components

### Frontend (dgbit-ui)

Vue 3 single-page application providing:

- **Dashboard**: Overview of system status and performance
- **Trading**: Real-time charts and order placement
- **Strategies**: Strategy selection and configuration
- **Portfolio**: Position tracking and P&L
- **System**: Settings and monitoring

**Technology Stack:**
- Vue 3 with Composition API
- Pinia for state management
- TailwindCSS for styling
- Vite for build tooling

### API Service (dgbit-api)

FastAPI-based REST API handling:

- **Request Routing**: HTTP endpoints for all operations
- **Job Management**: Async job creation and tracking
- **WebSocket**: Real-time event streaming
- **Database**: SQLite via TortoiseORM

**Key Endpoints:**
- `/api/health` - Health check
- `/api/backtests` - Backtest scheduling
- `/api/jobs` - Job management
- `/api/data` - Market data
- `/api/strategies` - Strategy operations
- `/api/execution` - Order execution

### Service Bus

NNG-based inter-process communication:

| Socket | Pattern | Purpose |
|--------|---------|---------|
| Command | REQ/REP | Synchronous API-to-worker |
| Event | PUB/SUB | Async event distribution |
| Queue | PUSH/PULL | Work distribution |

### Workers

Background job processors:

- **Backtest Worker**: Processes backtest jobs
- **Data Service**: Provides market data
- **Strategy Service**: Generates signals

### Shared Trading Core (dgbit_core)

Core trading logic used by all components:

- **Strategy Framework**: BaseStrategy, registry pattern
- **Backtesting Engine**: Historical simulation
- **Position Tracking**: Entry/exit management
- **Data Fetching**: Bybit API integration
- **ML Models**: Wavelet-based prediction

## Data Storage

### SQLite Database

Stores:
- Job records (status, payload, results)
- Execution history
- Configuration

### File System

- Backtest HTML reports
- Application logs
- IPC socket files

## External Dependencies

### Bybit Exchange

- Public API: Market data (no auth required)
- Private API: Trading (requires API keys)

Supports:
- Spot markets
- Testnet for development

## Deployment Models

### Development

```
                   ┌──────────────┐
                   │  Developer   │
                   └──────────────┘
                          │
              ┌───────────┼───────────┐
              ▼           ▼           ▼
         ┌────────┐  ┌────────┐  ┌────────┐
         │  API   │  │ Worker │  │   UI   │
         │ :8000  │  │        │  │ :3000  │
         └────────┘  └────────┘  └────────┘
              │           │
              └─────┬─────┘
                    ▼
              ┌──────────┐
              │  SQLite  │
              └──────────┘
```

### Production

```
                   ┌──────────────┐
                   │   Internet   │
                   └──────────────┘
                          │
                   ┌──────────────┐
                   │   nginx/LB   │
                   └──────────────┘
                          │
         ┌────────────────┼────────────────┐
         ▼                ▼                ▼
    ┌────────┐       ┌────────┐       ┌────────┐
    │  API   │       │  API   │       │   UI   │
    │   #1   │       │   #2   │       │  (CDN) │
    └────────┘       └────────┘       └────────┘
         │                │
         └────────┬───────┘
                  ▼
         ┌────────────────┐
         │    Workers     │
         │  (scaled out)  │
         └────────────────┘
                  │
                  ▼
         ┌────────────────┐
         │   PostgreSQL   │
         └────────────────┘
```

## Security Considerations

1. **API Keys**: Never in code, use secrets management
2. **Network**: Internal services not exposed
3. **Authentication**: Implement for production
4. **Rate Limiting**: Prevent abuse
5. **Input Validation**: Pydantic models

## Performance Characteristics

| Component | Latency | Throughput |
|-----------|---------|------------|
| API Response | < 50ms | 1000 req/s |
| Signal Generation | < 100ms | 100/s |
| Backtest (1000 candles) | ~2s | 30/min |
| WebSocket Events | < 10ms | 10,000/s |

## Next Steps

- [Service Bus](service-bus.md) - Deep dive into NNG messaging
- [Data Flow](data-flow.md) - How data moves through the system
