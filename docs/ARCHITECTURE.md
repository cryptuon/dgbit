# Architecture Overview

## Domain Scope
dgbit targets short-term discretionary strategies on Bybit spot markets. The system currently:
- Collects minute-level klines and enriches them with simple price/volume derivatives.
- Applies a wavelet-based heuristic to detect potential reversals.
- Routes those signals through either a historical simulator or an experimental live trader.

The refactor aims to preserve this workflow while hardening data contracts, modelling interfaces, execution safety, and operational excellence.

## Module Map (Current State)
| Module | Responsibility | Notes |
| --- | --- | --- |
| `dgbit-api/shared/python/dgbit_core/data/fetcher.py` | HTTP + websocket adapters for Bybit plus inline feature engineering. | Tight coupling of transport, schema parsing, and feature creation. |
| `dgbit-api/shared/python/dgbit_core/trading/strategy.py` | Pluggable strategy system with registry pattern. | Supports multiple strategies (Wavelet, MA, RSI, Bollinger). |
| `dgbit-api/shared/python/dgbit_core/trading/position.py` | Position tracking with entry/exit logic. | Used by backtester and execution engine. |
| `dgbit-api/shared/python/dgbit_core/backtesting/backtester.py` | Performs in-memory sequential simulation and produces Plotly reports. | Portfolio, execution, and reporting logic intertwined. |
| `dgbit-api/src/dgbit_api/api/routes.py` | REST API endpoints. | Health, backtests, jobs, data, strategies, execution. |
| `dgbit-api/src/dgbit_services/` | NNG service bus for inter-process communication. | Events, jobs, strategy, execution, data services. |

## Runtime Flows
### Backtesting
```
API/CLI -> Backtester.run(config, strategy, market_data)
       └─ Strategy.generate_signal() -> Position management
       └─ Metrics & HTML report
```
- Uses configurable train/test split.
- Executes one position at a time with configurable capital allocation.
- Reports stored as HTML under configured output directory.

### API Service
```
Client -> FastAPI (dgbit-api/src/dgbit_api/main.py)
      └─ Routes (/health, /backtests, /jobs, /data, /strategies, /execution)
      └─ NNG Services (dgbit-api/src/dgbit_services/)
```
- REST API handles synchronous requests.
- NNG service bus handles async operations and events.
- WebSocket for real-time updates (event bus subscription).

## Data Contracts
- `get_kline_data()` returns a pandas DataFrame with numeric columns: `timestamp`, `open`, `high`, `low`, `close`, `volume`, `turnover`, plus engineered features (`price_change`, `volume_change`, `rolling_volatility`, `rolling_volume`).
- Downstream modules assume all columns exist and use implicit dtype conversions. There is no schema validation or versioning yet.

## Pain Points
1. **Coupling:** Each module instantiates its dependencies, making it hard to swap predictors, strategies, or data sources.
2. **Parallel Execution Paths:** Backtester and live trader implement similar logic separately, risking divergence.
3. **Lack of Contracts:** No typed DTOs or validation for API inputs/outputs, which complicates caching, testing, and reuse.
4. **Observability Gaps:** Logging, tracing, and metrics are absent; debugging depends on `print`.

## Target Architecture (Refactor Goal)
```
dgbit-api/
├── src/dgbit_api/              # FastAPI REST API
│   ├── api/                    # Route handlers
│   ├── core/                   # Config, logging
│   ├── db/                     # Database models
│   ├── infra/                  # Infrastructure (messaging)
│   ├── services/               # Business services
│   └── workers/                # Background workers
├── src/dgbit_services/         # NNG Service Bus
│   ├── events.py               # Event bus (PUB/SUB)
│   ├── jobs.py                 # Job queue
│   ├── strategy.py             # Strategy service
│   ├── execution.py            # Execution service
│   ├── data.py                 # Data service
│   └── orchestrator.py         # Service orchestrator
├── src/dgbit_data/             # Data layer
│   ├── adapters/               # Exchange adapters
│   ├── client.py               # Data service client
│   └── service.py              # Data service
├── shared/python/dgbit_core/   # Shared trading logic
│   ├── backtesting/            # Backtesting engine
│   ├── trading/                # Strategies, positions
│   └── data/                   # Data fetching
└── tests/                      # API tests

dgbit-ui/                        # Vue 3 SPA
├── src/
│   ├── views/                  # Page components
│   ├── stores/                 # Pinia stores
│   └── services/               # API client
└── ...
```
- **Dependency Injection:** Constructor parameters or factories supply predictors, cost models, and risk limits to strategies and engines.
- **Shared Execution Engine:** Backtesting and live trading use the same order/portfolio services so that replaying live data yields identical outcomes.
- **Schema Enforcement:** Pydantic (or similar) models describe data at each boundary (API response, feature set, signal).
- **Observability:** Structured logging, metrics, and audit trails around trade lifecycle events.

## Refactor Considerations
- Move generated artifacts (`reports/`, cached data) outside the Python package to align with packaging best practices.
- Introduce asynchronous or event-driven components for data streaming and execution to avoid blocking loops.
- Provide integration points for advanced models (scikit-learn, LightGBM) already listed in dependencies but not yet used.
- Design the system so that new exchanges or instruments are just new adapters, not rewrites.

Refer to `docs/ROADMAP.md` for the sequence of workstreams required to reach the target state.
- `dgbit-api` hosts the FastAPI service, NNG service bus, and worker orchestration. `dgbit-ui` houses the Vue/Tailwind SPA that consumes API routes and event streams. Both apps depend on `shared/python/dgbit_core` for domain logic.
