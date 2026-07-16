# dgbit Roadmap

> This is the **product roadmap** — vision, milestones, and the cheapest path to running dgbit in production.
> For the internal engineering refactor sequence (data contracts, module boundaries, execution-engine unification), see [`docs/ROADMAP.md`](docs/ROADMAP.md).

## Vision

dgbit is a **backtest-to-live algorithmic trading framework for Bybit** — a Python package plus a small multi-service stack (FastAPI, an NNG service bus, a Vue 3 dashboard) that takes a strategy from a historical simulation to a live position without a rewrite in between.

The market direction we are building toward is **agent-operated trading infrastructure**. In 2026, trading systems are increasingly driven not by a person clicking a dashboard but by schedulers, CI pipelines, and autonomous agents that read signals, place orders, and react to fills. dgbit is not an "AI trader" and makes **no financial-return claims**. It aims to be the honest, operable layer *underneath* one:

- **Parity, not promises.** A signal behaves identically in backtest and in live execution, because both consume the strategy through the same interface and the same single-exchange model. That is what makes an autonomous loop trustworthy — the thing it tested is the thing it runs.
- **Operable over an API.** Every action a human takes from the dashboard is available over REST plus a WebSocket event stream, so a cron job or an agent can drive the whole loop: schedule a backtest, request a signal, place an order, subscribe to `job.*` / `trade.*` / `signal.generated`.
- **Precise over broad.** dgbit binds to Bybit deliberately. Fees, kline boundaries, and order assumptions map one-to-one to the real venue instead of passing through a lowest-common-denominator multi-exchange abstraction.

## Milestones

| Milestone | Theme | Outcome |
| --- | --- | --- |
| **M1 — Framework baseline** *(current)* | Backtest, strategy plugin model, live execution, dashboard | `pip install dgbit`; four built-in strategies; in-memory backtester with Plotly reports; FastAPI + NNG + Vue 3 stack; docker-compose deploy. |
| **M2 — Production hardening** | Reliability & safety | Exchange reconnect/backoff, order reconciliation, hardened risk filters (max position, stop-outs), structured logs and metrics, secrets handling. See "Cheapest path to production" below. |
| **M3 — Backtest↔live parity guarantees** | Trust | Shared order/portfolio engine across simulation and live; replay tests that assert identical outcomes on the same data; documented fee/slippage models. |
| **M4 — Agent-operable surface** | 2026 direction | First-class API ergonomics for programmatic operators: stable job/signal/order contracts, idempotent order submission, richer event payloads, and reference examples for driving dgbit from a scheduler or an autonomous agent. |
| **M5 — Extensibility** | Reach | More built-in strategies and indicators, additional Bybit instruments (e.g. perpetuals), and a documented data-adapter seam — without abandoning single-exchange precision. |

Milestones describe direction and are not dated commitments.

## Cheapest path to production

**dgbit is software, not a chain.** There is no token, no gas, no on-chain deployment. "Production" here means two concrete things:

1. **A published, installable package** — the Python package on [PyPI](https://pypi.org/project/dgbit/) (`pip install dgbit`) and the Docker image at `cryptuon/dgbit`.
2. **A self-hosted running instance** — the API, workers, and (optionally) the dashboard executing your strategies against live Bybit.

**The cheapest path is: `pip install dgbit` (or `docker-compose up`) on a single small VPS.** No cluster, no managed database, no message broker to rent — the NNG bus is in-process IPC and the default persistence is SQLite via `aiosqlite`. A 1 vCPU / 1–2 GB instance is enough to run the API, the workers, and a handful of strategies; the dashboard is optional and can be served from the same box. Your recurring cost is that VPS plus a Bybit account.

That said, "cheapest to stand up" is not the same as "safe to leave running with real capital." Production-viability for a system that places live orders means:

- **Exchange API reliability.** Reconnect logic with exponential backoff, request throttling to respect rate limits, and websocket/keepalive handling so a dropped connection does not silently stop trading. (Roadmap M2.)
- **Order & position reconciliation.** On restart or reconnect, reconcile local state against Bybit's actual open orders and positions before acting again — never assume the in-memory view is authoritative.
- **Risk controls.** Enforce max position size, per-strategy exposure caps, and stop-outs *before* an order leaves the process. Start with `BYBIT_TESTNET=true` and only flip to live after the strategy you intend to run has been backtested.
- **Secrets management.** Keep `BYBIT_API_KEY` / `BYBIT_API_SECRET` out of the image and out of git — inject them at runtime (env file with locked-down permissions, or your host's secret store). Use API keys scoped to the minimum required permissions.
- **Monitoring.** Ship structured logs and basic metrics off the box (stdout to a log service, or Prometheus scraping) and alert on: disconnects, rejected orders, risk-limit trips, and worker crashes. A trading system that fails silently is worse than one that stops loudly.
- **Backtest→live parity.** Only run live what you have backtested, and treat any divergence between simulated and real fills as a bug to investigate, not noise to ignore.
- **Documentation.** Keep a runbook for the boring failure modes — key rotation, restart procedure, how to halt trading fast. Full docs live at [docs.cryptuon.com/dgbit](https://docs.cryptuon.com/dgbit/).

If you only want to *research* — backtest strategies, generate signals, build reports — none of the live-trading hardening applies, and the cost floor is lower still: `pip install dgbit` on your laptop, no exchange keys required.

## Non-goals

- **No return claims, ever.** dgbit is infrastructure. It does not promise, imply, or backtest-market any profit outcome.
- **Not multi-exchange.** Broad venue coverage is explicitly out of scope; precision on Bybit is the trade we chose. If you need many exchanges, that is an honest reason to look elsewhere (see the comparisons on [dgbit.cryptuon.com](https://dgbit.cryptuon.com/)).
- **Not a bundled agent.** dgbit provides the operable substrate — API, events, parity. Wiring an agent on top is your call and your code.

---

*Part of [Cryptuon Research](https://www.cryptuon.com). Docs: [docs.cryptuon.com/dgbit](https://docs.cryptuon.com/dgbit/) · Site: [dgbit.cryptuon.com](https://dgbit.cryptuon.com/)*
