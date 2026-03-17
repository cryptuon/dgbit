# dgbit-api

FastAPI-powered control plane for the dgbit platform. It exposes REST/WebSocket APIs, orchestrates background workers via nng sockets, and surfaces trading analytics to clients (dgbit-ui).

## Layout
```
src/dgbit_api/
├── api/          # Route definitions and DTOs
├── core/         # Configuration, logging, dependency wiring
├── domain/       # Shared domain entities/value objects
├── infra/        # Messaging, persistence, adapters
├── services/     # Application services orchestrating dgbit-core libraries
├── workers/      # Background worker entrypoints
└── main.py       # ASGI entrypoint
```

## Quickstart
```bash
cd apps/dgbit-api
poetry install
poetry run uvicorn dgbit_api.main:app --reload
```

Workers can be launched with:
```bash
poetry run python -m dgbit_api.workers.backtest_runner
```
