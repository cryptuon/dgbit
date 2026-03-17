# dgbit – Bybit Trading Bot Prototype

## Overview
dgbit is an experimental framework for researching and running short-term strategies on Bybit spot markets. The current codebase focuses on downloading high-frequency klines, extracting wavelet-based reversal signals, simulating trades through a lightweight backtester, and optionally streaming data for live execution. This repository is being refactored into a production-ready system; the documentation here captures the present state and the roadmap for the rewrite.

## Key Capabilities (Current Prototype)
- Fetch high-resolution kline data plus basic momentum features via `pybit` (`shared/python/dgbit_core/data/data_fetcher.py`).
- Generate trading signals using a Daubechies wavelet heuristic (`shared/python/dgbit_core/models/predictor.py`, `shared/python/dgbit_core/trading/strategy.py`).
- Perform single-position backtests with HTML reporting (`shared/python/dgbit_core/backtesting/backtester.py`).
- Stream live klines and trigger trades in real time (experimental, `shared/python/dgbit_core/trading/realtime_trader.py`).

## Architecture at a Glance
```
┌────────────┐    ┌────────────────┐    ┌─────────────────┐    ┌───────────────────┐
│ Bybit APIs │ -> │ Data Fetchers  │ -> │ Feature / Model  │ -> │ Strategy / Trading│
└────────────┘    │ (HTTP/WebSock) │    │ (Wavelet logic)  │    │ (Backtest/Live)   │
                  └────────────────┘    └─────────────────┘    └───────────────────┘
                                               │
                                               ▼
                                        Reports & Metrics
```
The refactor will formalize these layers into reusable services with shared configuration, logging, and tests. See `docs/ASSESSMENT.md` and `docs/ROADMAP.md` for details.

## Getting Started
### Prerequisites
- Python 3.11
- Poetry 1.6+
- Bybit API key/secret with market-data permissions (live or testnet)

### Installation
```bash
poetry install
```

### Environment Configuration
Create a `.env` file (not committed) with your credentials and runtime toggles:
```
BYBIT_API_KEY=...
BYBIT_API_SECRET=...
BYBIT_TESTNET=false
```
Additional configuration will migrate into a typed settings module during the refactor.

### Run a Sample Backtest
```bash
poetry run python -m dgbit_core.main
```
The script fetches volatile spot pairs, downloads historical klines, runs the `Backtester`, prints metrics, and writes Plotly HTML reports into `shared/python/dgbit_core/reports/`.

### Platform Apps
- **API service:** `cd apps/dgbit-api && poetry install && poetry run uvicorn dgbit_api.main:app --reload`
- **Background worker (prototype):** `poetry run python -m dgbit_api.workers.backtest_runner`
- **UI shell:** `cd apps/dgbit-ui && npm install && npm run dev` (Vite dev server proxied to the API)

### Experimental Real-Time Trading
`shared/python/dgbit_core/trading/realtime_trader.py` demonstrates how to stream minute-level klines and react to signals. It currently manages a single position in memory and lacks error handling or risk controls—use for exploration only.

## Project Structure
```
apps/
├── dgbit-api/           # FastAPI service + nng worker stubs
└── dgbit-ui/            # Vue 3 + Tailwind UI shell
shared/
└── python/
    └── dgbit_core/      # Trading logic (data, models, strategies, backtesting)
docs/
├── ASSESSMENT.md        # Technical assessment of the current codebase
├── ROADMAP.md           # Phased plan for the full refactor
├── ARCHITECTURE.md      # Current vs target architecture and data flows
├── DEVELOPMENT_GUIDE.md # Environment setup and contribution workflow
├── OPERATIONS.md        # Runbooks for research, paper, and production modes
└── PLATFORM_PLAN.md     # Structure for dgbit-api (FastAPI) and dgbit-ui (Vue)
```

## Refactor Roadmap Highlights
1. **Foundations:** Define layered architecture, centralized configuration, structured logging, and CI safety nets.
2. **Data & Features:** Encapsulate exchange adapters, caching, validation, and deterministic feature engineering reused across modes.
3. **Strategy & Modelling:** Support pluggable predictors with experiment harnesses and dependency injection.
4. **Simulation & Execution:** Build a shared order/portfolio engine for both backtests and live trading, including risk controls and reporting.
5. **Operations:** Containerize, monitor, and document operational processes before promoting to production.

Refer to `docs/ROADMAP.md` for the detailed sequencing plus success criteria, and to `docs/ASSESSMENT.md` for the gap analysis informing the plan.

## Contributing / Next Steps
- Follow the roadmap documents when planning tasks; open issues should reference the relevant phase and deliverable.
- Add unit tests and logging as you touch modules—quality gates are critical before shipping a live trading system.
- Track outstanding questions (e.g., supported exchanges, deployment targets) in `docs/ROADMAP.md` so execution risks stay visible.
