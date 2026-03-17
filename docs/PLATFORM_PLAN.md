# Platform Plan – dgbit-api & dgbit-ui

This document captures the up-front structure for splitting the project into an API service with background workers and a dedicated UI. The intent is to keep everything in a single repository (monorepo) while allowing each app to evolve independently.

## Target Repository Layout
```
apps/
├── dgbit-api/          # FastAPI service + background worker package
│   ├── pyproject.toml
│   └── dgbit_api/
│       ├── api/        # Routers, DTOs, dependency wiring
│       ├── workers/    # nng-based background jobs
│       ├── services/   # Trading/backtesting/application logic
│       ├── domain/     # Entities/value objects shared with workers
│       ├── infra/      # Data providers, exchanges, persistence
│       └── main.py     # ASGI entrypoint
├── dgbit-ui/           # Vue 3 + Vite + Tailwind SPA
│   ├── package.json
│   └── src/
│       ├── pages/
│       ├── components/
│       ├── composables/
│       ├── stores/     # Pinia stores for state
│       └── styles/
└── shared/
    ├── python/         # Reusable Python libraries (core models, utils)
    └── web/            # Shared TypeScript types or generated clients
docs/
└── ...                 # Architecture, roadmap, etc.
```
- `apps/` keeps deployable units separated.
- `shared/python` exposes packages (e.g., `dgbit-core`, `dgbit-signals`) consumed by both API service and workers.
- `shared/web` hosts generated OpenAPI clients or shared constants for the UI.

## dgbit-api (FastAPI + nng Workers)

### Core Responsibilities
1. **REST + WebSocket API:** Manage authentication, strategy configuration, job orchestration, portfolio/query endpoints.
2. **Background Processing:** Run CPU-heavy tasks (data ingestion, model training, backtests, signal generation) using nng sockets for command/control.
3. **Realtime Streams:** Push live market/trade events to the UI through WebSockets or Server-Sent Events, backed by worker data feeds.
4. **Persistence:** Store configurations, runs, and metrics (initially SQLite/PostgreSQL; extend later).

### Architectural Components
| Component | Purpose | Notes |
| --- | --- | --- |
| `api/routers` | FastAPI routers grouped by domain (`/strategies`, `/backtests`, `/jobs`, `/metrics`). | Use Pydantic models for request/response schemas. |
| `services/` | Application services orchestrating data fetchers, strategies, and persistence. | Thin wrappers around domain logic hosted in `shared/python`. |
| `workers/` | NNG-based worker processes for tasks: `data_sync`, `backtest_runner`, `signal_engine`, `trading_executor`. | Each worker subscribes to command sockets and publishes status/events. |
| `infra/` | Exchange adapters, data stores, message bus abstractions. | Implement `nng` transport wrappers, database repositories, caching, logging. |
| `core/config` | Settings module (Pydantic) unifying environment variables, CLI args, `.env`. | Shared between API and workers via `shared/python`. |

### NNG Messaging Plan
- **Command Socket (req/rep):** API sends job requests (start backtest, sync data) to a router service that dispatches to workers.
- **Event Bus (pub/sub):** Workers emit progress, logs, and telemetry. API subscribes to relay updates to clients via WebSockets.
- **Heartbeat Channel:** Workers send periodic heartbeats; API monitors liveness and triggers restart alerts.

### Task Lifecycle
1. Client hits `/backtests` POST.
2. API validates payload, writes job metadata to DB, sends command to `backtest_runner`.
3. Worker fetches dataset (via shared libraries), executes simulation, streams intermediate metrics over event bus.
4. API receives events, stores them, pushes to WebSocket subscribers, finally marks job complete.

### Dev/Build Considerations
- Use `uvicorn` for local dev, `gunicorn` + `uvicorn.workers.UvicornWorker` in prod.
- Package CLI entrypoints (`python -m dgbit_api.workers.backtest_runner`) to run workers.
- Provide Dockerfiles per app and a docker-compose stack for local integration (API, workers, Postgres, Redis).

## dgbit-ui (Vue 3 + Tailwind)

### Core Responsibilities
1. Visualize account metrics (equity curve, open positions, job status).
2. Configure strategies and run backtests through the API.
3. Stream live updates via WebSocket/SSE.
4. Provide developer-friendly UX for exploring datasets and logs.

### Structure
| Folder | Purpose |
| --- | --- |
| `src/pages/` | Route-level views (Dashboard, Backtests, Strategies, Operations). |
| `src/components/` | Reusable UI primitives (charts, cards, forms). |
| `src/composables/` | Vue Composition API hooks for API clients, sockets, formatting. |
| `src/stores/` | Pinia stores for app/global state, job queues, user prefs. |
| `src/services/api.ts` | Auto-generated OpenAPI client + wrappers. |
| `src/styles/` | Tailwind config + global styles. |

### Data Flow
1. UI calls REST endpoints using generated client.
2. UI subscribes to `/ws/jobs/:id` for progress updates.
3. UI dispatches actions to Pinia stores, which orchestrate API calls and state transitions.
4. Components render charts (e.g., using ECharts or Plotly.js) fed by store state.

### Build/Tooling
- Vite build with env-based configuration (`VITE_API_BASE_URL`).
- Tailwind + Headless UI for rapid layout.
- ESLint + Prettier enforced via npm scripts/CI.
- Dockerfile for production static hosting (Nginx) or deploy via Netlify/Vercel.

## Delivery Plan Snapshot
| Step | Outcome |
| --- | --- |
| 1. **Monorepo bootstrap** | Create `apps/dgbit-api` and `apps/dgbit-ui` skeletons; move existing Python logic under `shared/python` (`dgbit-core`). |
| 2. **Core libraries extraction** | Refactor `shared/python/dgbit_core` modules into reusable packages (`data`, `strategies`, `backtesting`) consumed by the API service. |
| 3. **FastAPI scaffolding** | Implement health endpoints, config, dependency injection, `nng` transport wrapper, sample worker. |
| 4. **Worker prototypes** | Build `backtest_runner` worker invoking shared libraries; integrate command/event sockets. |
| 5. **UI scaffolding** | Initialize Vue/Tailwind app, add auth shell, connect to API health endpoint. |
| 6. **Backtest workflow** | End-to-end: UI triggers backtest -> API -> worker -> event stream -> UI renders progress/results. |
| 7. **Realtime trading workflow** | Extend API routes/workers for live trading, WebSocket streaming, and dashboards. |
| 8. **Hardening & ops** | Logging, metrics, CI pipelines, deployment manifests (Docker Compose + cloud). |

## Coordination Notes
- Maintain compatibility between `shared/python` packages and API workers via semantic versioning (even within monorepo).
- Generate OpenAPI schema from FastAPI, feed into `dgbit-ui` for type-safe clients.
- Upfront decisions needed: database choice, authentication (JWT? API keys?), deployment target (Kubernetes, bare VM).
- Document runbooks in `docs/OPERATIONS.md` as the new components land.

This plan should guide the immediate structuring work so coding can begin with clear boundaries and integration points.
