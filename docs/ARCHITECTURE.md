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
| `shared/python/dgbit_core/data/data_fetcher.py` | HTTP + websocket adapters for Bybit plus inline feature engineering. | Tight coupling of transport, schema parsing, and feature creation. |
| `shared/python/dgbit_core/models/predictor.py` | Wavelet-based probability estimate of a reversal. | Stateless, no serialization. |
| `shared/python/dgbit_core/trading/strategy.py` | Couples predictor with thresholds and exit logic. | Instantiates predictor internally, limiting experimentation. |
| `shared/python/dgbit_core/backtesting/backtester.py` | Performs in-memory sequential simulation and produces Plotly reports. | Portfolio, execution, and reporting logic intertwined. |
| `shared/python/dgbit_core/trading/realtime_trader.py` | Streams live klines and mirrors the strategy logic. | Minimal error handling or risk management. |
| `shared/python/dgbit_core/main.py` | CLI entry that orchestrates data fetch + backtesting for volatile pairs. | Performs both discovery of symbols and simulation. |

## Runtime Flows
### Backtesting
```
.env -> main.py -> BybitDataFetcher.get_volatile_pairs()
      -> loop(pair):
           get_kline_data(pair)
           Backtester.run(data)
              └─ TradingStrategy -> PricePredictor
           Backtester.plot_results(...)
```
- Uses 70/30 train/test split inside `Backtester`.
- Executes one position at a time with full capital allocation.
- Reports stored as HTML under `shared/python/dgbit_core/reports/`.

### Real-Time Trading (experimental)
```
RealtimeTrader.run(symbol)
 ├─ update_model(symbol) -> fetcher.get_kline_data()
 └─ stream_klines(symbol, handle_new_data)
        ├─ strategy.should_enter_trade(...)
        └─ enter_position / exit_position (inline, no exchange orders yet)
```
- Keeps a rolling dataframe of recent klines and re-trains the predictor in memory.
- No persistence, state checkpointing, or reconnection handling.

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
apps/ (cli, services)
└── services/
    ├── data_providers/   (HTTP/WebSocket clients, caching, schemas)
    ├── feature_pipelines/
    ├── models/           (predictors, registries, serialization)
    ├── strategies/       (signal generators, rule engines)
    ├── execution/        (order router, portfolio engine shared by sim/live)
    └── reporting/        (metrics, dashboards, export)
core/
└── config, logging, events, shared types
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
- `apps/dgbit-api` now hosts the FastAPI service and worker orchestration stubs. `apps/dgbit-ui` houses the Vue/Tailwind SPA that will consume API routes and event streams. Both apps depend on `shared/python/dgbit_core` for domain logic and will eventually rely on generated OpenAPI clients.
