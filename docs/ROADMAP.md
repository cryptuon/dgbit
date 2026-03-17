# Refactor Roadmap

## Guiding Principles
- **Parity first:** Align backtesting and live execution paths so a signal behaves identically regardless of environment.
- **Separation of concerns:** Decouple data access, feature engineering, modelling, strategy rules, and execution engines behind narrow interfaces.
- **Safety & observability:** Every module emits structured logs/metrics, validates inputs, and is covered by automated tests.
- **Composable delivery:** Prioritize incremental deliverables that can land independently while unlocking the broader rewrite.

## Phase Overview
| Phase | Goal | Primary Outcomes |
| --- | --- | --- |
| 0. Discovery & Stabilization | Capture requirements, freeze current behavior, and add guard rails for the refactor. | Repo audit, baseline diagrams, lint/test scaffolding, data samples stored locally. |
| 1. Foundations | Establish the new package layout, configuration system, logging, and development tooling. | Modular folder structure, config schema (Pydantic/dataclasses), logging helpers, Make/Poetry scripts, CI smoke tests. |
| 2. Data & Features Layer | Abstract Bybit and future exchanges from feature engineering so strategies consume a uniform data contract. | Data adapters, caching, validated schemas, deterministic feature pipeline reused by both sim/live contexts. |
| 3. Strategy & Modelling Engine | Support multiple predictors, feature stores, and rule definitions with dependency injection. | Signal interface, model registry, serialization, experiment harness, docs for extending strategies. |
| 4. Simulation & Execution | Build a shared order/portfolio engine and robust executor with risk checks, monitoring, and reporting. | Event-driven simulator, execution adapters, risk filters, reporting dashboards, integration tests. |
| 5. Release & Operations | Harden deployments, document SLOs, and automate monitoring/alerting. | Deployment scripts, prod runbooks, metric dashboards, rollback plan. |

## Phase Details
### Phase 0 – Discovery & Stabilization (Week 0–1)
- Capture baseline metrics by running the current backtester on a frozen dataset; store sample outputs in `data/snapshots`.
- Produce lightweight diagrams of the current flow (already started in `docs/ASSESSMENT.md`).
- Introduce formatting (`black`, `isort`) and lint checks plus a placeholder pytest suite with smoke tests to guard against regressions during refactor.

### Phase 1 – Foundations (Week 1–2)
- Move to a layered folder structure within `shared/python/dgbit_core` (e.g., `core`, `services`, `domain`) while bootstrapping deployable apps under `apps/`.
- Create a config module (Pydantic settings) that centralizes environment variables, network toggles, and strategy parameters.
- Add structured logging (loguru or stdlib) and tracing hooks for API calls.
- Write `Makefile`/Poetry scripts for `setup`, `test`, `lint`, `backtest`, and `trade`.

### Phase 2 – Data & Features Layer (Week 2–4)
- Wrap exchange calls inside provider classes with retry/backoff, throttling, and request/response schemas.
- Implement local caching (Parquet/SQLite) for historical data and a deterministic feature builder that outputs typed dataframes.
- Provide offline fixtures/mocks for unit tests and CLI utilities to sync new data.

### Phase 3 – Strategy & Modelling Engine (Week 4–6)
- Define a `Signal` or `Strategy` interface with lifecycle hooks (`prepare`, `generate_signals`, `post_trade`).
- Support multiple model types (wavelet heuristic, ML models) using a registry plus serialization so experiments can run offline.
- Build evaluation notebooks/scripts referencing the shared feature layer, and document how to plug in new strategies.

### Phase 4 – Simulation & Execution (Week 6–8)
- Implement a shared order book + portfolio engine used by both backtesting and live execution.
- Add transaction cost models, slippage, multi-position handling, and scenario runners.
- Build a real-time executor with risk checks (max position, stop-outs), exchange reconciliation, and failover logic.
- Emit structured metrics to a sink (stdout/Prometheus) and persist trade logs for auditability.

### Phase 5 – Release & Operations (Week 8–9)
- Containerize the application (Docker) and define deployment targets (research box, paper-trading, production).
- Add monitoring dashboards, alert rules, and runbooks for ops handoff.
- Conduct a final readiness review to ensure documentation, onboarding, and automated tests meet acceptance criteria.

## Dependencies & Enablers
- **Team decision on asset scope:** Determines data retention, capital allocation, and compliance needs.
- **Access to Bybit testnet / sandbox accounts:** Required to build integration tests and run execution rehearsals safely.
- **Infrastructure budget:** Needed for storage (feature cache) and compute (model training, backtesting clusters).

## Definition of Done
- All major modules conform to the new layered architecture and depend on shared interfaces.
- Backtesting and live engines share >80% of execution code paths and produce identical results on replayed data.
- CI pipeline runs linting, unit tests, integration smoke tests, and sample backtests automatically.
- Documentation (README, `docs/`) gives newcomers enough context to run, extend, and operate the system confidently.
