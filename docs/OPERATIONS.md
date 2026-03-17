# Operations Guide

This runbook outlines how the system should behave in different environments (research, paper trading, production) and what operational safeguards need to exist after the refactor.

## Environments
| Env | Purpose | Notes |
| --- | --- | --- |
| **Research** | Local experiments, offline backtests, feature development. | Uses cached historical data, mock exchange adapters, can run without credentials. |
| **Paper Trading** | Real-time dry runs against Bybit testnet. | Shares the live execution engine but routes orders to testnet endpoints; metrics reported to dashboards. |
| **Production** | Live trading with real capital. | Requires hardened secrets management, monitoring, alerting, and change control. |

## Deployment Targets (Future State)
- **CLI / Batch Jobs:** `python -m dgbit_core.main` for analysis runs, scheduled via cron or workflow engine.
- **Realtime Service:** `apps/dgbit-api` FastAPI deployment (systemd, Docker container, or Kubernetes pod) executing orchestration logic.
- **Data Sync Workers:** `dgbit_api.workers.*` background jobs refreshing caches (klines, reference data).

## Configuration Sources
- `.env` for local development.
- Centralized secrets store (Vault, AWS Secrets Manager, etc.) for shared environments.
- Typed settings (Pydantic) to merge environment variables, CLI args, and config files.

## Monitoring & Alerting
- **Logs:** Structured JSON logs with correlation IDs for each backtest or trading session.
- **Metrics:** Emit latency, throughput, PnL, order status, error counts to Prometheus/CloudWatch.
- **Alerts:** Trigger on missing data, order failures, excessive drawdown, or service restarts.
- **Dashboards:** Visualize account equity, position inventory, and signal statistics.

## Run Procedures
### Backtest Job
1. Prepare dataset (download/cached).
2. Run `poetry run python -m dgbit_core.main` (placeholder; will become dedicated CLI).
3. Review metrics/logs; archive Plotly reports.
4. Store inputs/outputs together for reproducibility.

### Live Trading Session
1. Validate credentials and risk parameters.
2. Launch service with monitored process manager.
3. Verify connectivity to market data and order endpoints.
4. Monitor logs/metrics for anomalies; be prepared to disable strategy quickly.
5. After session, export trade logs and reconcile with exchange account.

## Incident Response (Future State)
- **Detection:** Alerts from monitoring or manual observation.
- **Mitigation:** Pause trading (circuit breaker), revert to safe config, or failover to standby service.
- **Communication:** Notify stakeholders, capture timeline, open incident doc.
- **Postmortem:** Document root cause, remediation tasks, and tests to prevent recurrence.

## Compliance & Security Considerations
- Audit logs for trade decisions and configuration changes.
- Role-based access to credentials and deployment pipelines.
- Regular key rotation and secure storage (no plaintext credentials in repos or logs).
- Document risk limits and approvals required before deploying new strategies.

Use this guide as the foundation for detailed runbooks once the refactor delivers a production-ready system.
