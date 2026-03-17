# Project Assessment

## Snapshot
- **Purpose:** Experimental Bybit spot trading bot that fetches klines, produces a wavelet-based reversal signal, backtests that logic, and can stream live data for execution.
- **Entry point:** `shared/python/dgbit_core/main.py` orchestrates fetching volatile pairs, running historical downloads via `BybitDataFetcher`, invoking the `Backtester`, and printing metrics.
- **Core stack:** Python 3.11, Poetry, `pybit` for Bybit APIs, `pandas`/`numpy` for analytics, `pywavelets` for the heuristic `PricePredictor`, Plotly for HTML reports.
- **Current maturity:** Prototype. Tight coupling between modules, no persistence beyond memory, no tests, and limited observability or configuration.

## Current Architecture
### Data Acquisition (`shared/python/dgbit_core/data/data_fetcher.py`)
- Provides synchronous HTTP access to Bybit and a websocket streamer, then enriches the dataframe with simple momentum features.
- Uses API keys loaded in `main.py` via `.env`, but does not validate inputs, throttle requests, or abstract multiple exchanges.

### Modelling & Strategy (`shared/python/dgbit_core/models/predictor.py`, `shared/python/dgbit_core/trading/strategy.py`)
- Wavelet-based `PricePredictor` performs inline feature engineering and prediction without persisting artifacts.
- `TradingStrategy` hard-codes thresholds for entry/exit and instantiates the predictor internally, which makes dependency injection for experiments difficult.

### Backtesting & Analytics (`shared/python/dgbit_core/backtesting/backtester.py`)
- Splits a dataframe into train/test partitions, simulates sequential decisions, and stores positions in memory.
- Calculates a minimal set of metrics and generates Plotly HTML dashboards inside `reports/`, but mixes portfolio accounting, trade execution logic, and reporting in one class.

### Live Execution (`shared/python/dgbit_core/trading/realtime_trader.py`)
- Extends `TradingStrategy` to streaming use, but lacks order management, account syncing, or risk controls.
- Model updates and streaming occur on the same thread without lifecycle management, retry logic, or monitoring hooks.

### Tooling & Support
- No tests, linting hooks, structured logging, or CI.
- `reports/` lives under the Python package tree, making it difficult to distribute artifacts separately from code.

## Observed Strengths
- Focused domain scope with distinct modules for data, strategy, backtesting, and live trading.
- Uses modern scientific Python stack (pandas, numpy, scikit-learn placeholder, Plotly) and Poetry for dependency management.
- Early inclusion of both historical analysis (backtester) and streaming pathways (realtime trader), which clarifies intent for future expansion.

## Technical Debt & Risks
| Area | Risk | Refactor Implication |
| --- | --- | --- |
| **Architecture** | Modules import each other directly, and responsibilities (data fetching, feature engineering, signal generation, portfolio accounting) are interleaved. | Introduce layered packages (`core`, `data`, `features`, `strategies`, `execution`, `simulators`) with explicit interfaces and dependency injection. |
| **Configuration & Secrets** | Credentials are read ad hoc from environment variables with no validation or config schema. | Implement a configuration layer (Pydantic or `dataclasses`) and centralized secrets handling. |
| **Data Management** | No caching, persistence, or schema contracts for market data; computations assume all columns exist. | Define typed data models, add adapters for data providers, and encapsulate feature engineering separately from fetching. |
| **Strategy/Model Lifecycle** | `PricePredictor` is stateless and intertwined with strategy thresholds; no experimentation framework. | Separate feature pipelines, modelling, and strategy rules; add serialization and evaluation harnesses. |
| **Backtesting Fidelity** | Execution assumes full-capital trades and ignores slippage, fees (beyond a flat number), and concurrency. | Build an extensible simulator that supports order types, multiple positions, performance attribution, and scenario analysis. |
| **Realtime Trading** | No error handling, reconnection logic, or safeguards when orders fail or data streams stop. | Wrap API interactions, add retry/backoff, event-driven architecture, and plug risk checks before sending orders. |
| **Testing & CI** | Zero automated tests; no static analysis or formatting enforcement. | Introduce pytest suites, fixture data, integration tests for adapters, and CI workflows (GitHub Actions). |
| **Observability** | No structured logging or metrics; debugging relies on `print`. | Add logging facade, metrics collection, and health checks to make production behavior auditable. |

## Refactor Priorities
1. **Foundation:** Define the future package layout, central configuration, logging, and better dependency management. Move generated artifacts (reports, data) outside the Python package tree.
2. **Data & Features:** Create ingestion adapters with schema validation, caching, and deterministic feature engineering modules for both backtesting and live modes.
3. **Strategy Layer:** Support pluggable predictors and rules. Expose interfaces for experimentation and allow asynchronous training or service-based models.
4. **Simulation & Execution:** Rebuild the backtester around an order/portfolio engine shared with the live trader to guarantee parity, and enhance execution to cover state syncing, risk controls, and exchange abstractions.
5. **Quality Gates:** Add comprehensive unit/integration tests, config validation, linting, and CI/CD so refactors remain safe.

## Suggested Supporting Work
- Document domain constraints (asset universe, trading hours, acceptable latency).
- Define KPIs for the bot (max drawdown, Sharpe, hit rate) to evaluate strategies consistently.
- Create developer onboarding materials (make targets, troubleshooting guide) once the refactor stabilizes.

Refer to `docs/ROADMAP.md` for a phased plan that sequences the above workstreams.
