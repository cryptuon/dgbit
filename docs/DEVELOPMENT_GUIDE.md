# Development Guide

This guide keeps contributors aligned while the project transitions from prototype to production. Update it as tooling or workflows evolve.

## Tooling & Environment
- **Python:** 3.11 (match `pyproject.toml`).
- **Package manager:** Poetry. Run `poetry install` before hacking.
- **Linters/formatters:** `black`, `isort`. Add `ruff` or `mypy` during the refactor if desired.
- **Secrets:** Store Bybit credentials in `.env` (never commit). Consider using a secrets manager once deployed.

### Bootstrap Steps
```bash
poetry install
cp .env.example .env  # create if missing, set BYBIT_* vars
```

### Helpful Commands
| Action | Command |
| --- | --- |
| Format | `poetry run black shared/python/dgbit_core` |
| Import sort | `poetry run isort shared/python/dgbit_core` |
| Run tests (placeholder) | `poetry run pytest` |
| Backtest CLI | `poetry run python -m dgbit_core.main` |
| Explore REPL | `poetry run python` |

### Multi-app Workflow
- **API service:** `cd apps/dgbit-api && poetry install && poetry run uvicorn dgbit_api.main:app --reload`
- **Workers:** `poetry run python -m dgbit_api.workers.backtest_runner`
- **UI:** `cd apps/dgbit-ui && npm install && npm run dev`

Add `make` targets later (e.g., `make fmt`, `make test`, `make backtest`) for convenience.

## Branching & Workflow
1. Fork or branch from `main`.
2. Work in small, reviewable increments aligned with roadmap phases.
3. Include tests/docs updates alongside code changes.
4. Run formatters/tests locally; fix lint warnings before pushing.
5. Open pull requests referencing roadmap phases (e.g., `Phase 2 – Data Layer: caching`).

## Testing Strategy (Future State)
- **Unit tests:** Cover adapters (mocked HTTP/WebSocket), feature builders, predictors, and strategy decision logic.
- **Integration tests:** Replay canned datasets through the shared execution engine to assert parity between sim and live logic.
- **End-to-end smoke:** Run a short backtest against stored klines to validate packaging/build pipelines.
- **Static analysis:** `mypy` for typing, `ruff`/`flake8` for style, `bandit` for security as needed.

Currently the repo lacks tests—start by scaffolding fixtures in `tests/` with sample data frames (CSV/Parquet) to freeze behavior for the refactor.

## Coding Guidelines
- Prefer dependency injection over singletons; pass collaborators (data providers, predictors) to constructors.
- Keep modules focused (data acquisition, feature engineering, models, strategies, execution, reporting).
- Write docstrings for public classes/functions describing purpose, inputs, outputs, and side effects.
- Avoid hard-coded constants; place them in config objects or `.env` files processed via a settings module.
- Add lightweight logging (`logger.info/debug`) for key lifecycle events (data sync, signal generation, order submission).

## Documentation Standards
- Update `README.md` and relevant files in `docs/` when architecture or workflows change.
- Include ASCII diagrams or tables when they clarify flows.
- Keep documents concise; link to detailed references rather than duplicating content.

## Data Handling
- Store temporary or generated artifacts under `data/` or `reports/` outside the `shared/python/dgbit_core` package.
- Sanitize and compress large datasets before committing; prefer scripts to regenerate them.
- For third-party data, document provenance, licensing, and update cadence.

## Troubleshooting Tips
- **API failures:** Check rate limits, credential validity, and whether testnet vs live endpoints are selected.
- **Plotly reports missing:** Ensure `reports/` directory exists and that pandas inputs contain `timestamp` columns.
- **Streaming disconnects:** Add logging and reconnection loops; wrap callbacks with try/except to avoid silent failures.

Following this guide as the refactor proceeds will keep the team aligned and reduce churn as new contributors join.
