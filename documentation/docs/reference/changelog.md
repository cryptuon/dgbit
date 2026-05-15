# Changelog

All notable changes to dgbit will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- PyPI package publishing support
- Docker and docker-compose configuration
- Comprehensive MkDocs documentation
- GitHub Actions CI/CD workflows

### Fixed
- Missing import for `get_api_client` in routes.py
- Incorrect method call `get_performance_metrics()` in backtest_runner.py
- JSON serialization using `json.dumps()` instead of `str()` in models.py

### Changed
- Updated README with badges and SEO-optimized content

## [0.1.0] - 2026-01-05

### Added
- Initial release of dgbit trading framework
- FastAPI REST API with endpoints for:
  - Backtesting (`/api/backtests`)
  - Job management (`/api/jobs`)
  - Market data (`/api/data`)
  - Strategies (`/api/strategies`)
  - Execution (`/api/execution`)
- Trading strategies:
  - Wavelet Reversal Strategy
  - MA Crossover Strategy
  - RSI Strategy
  - Bollinger Bands Strategy
- Backtesting engine with:
  - In-memory simulation
  - Train/test splitting
  - Performance metrics
  - Interactive Plotly reports
- Service bus architecture using NNG:
  - Command bus (REQ/REP)
  - Event bus (PUB/SUB)
  - Job queue (PUSH/PULL)
- Vue 3 frontend dashboard
- Position and order management
- Bybit API integration via pybit
- SQLite persistence for jobs
- WebSocket support for real-time events

### Dependencies
- Python 3.11+
- FastAPI 0.115+
- Pandas 2.1+
- PyWavelets 1.5+
- pynng 0.8+

---

## Version History

| Version | Date | Highlights |
|---------|------|------------|
| 0.1.0 | 2026-01-05 | Initial release |

## Upgrading

```bash
pip install --upgrade dgbit
```

Or with Docker:

```bash
docker pull cryptuon/dgbit:latest
docker-compose pull
docker-compose up -d
```

The canonical changelog is [`CHANGELOG.md`](https://github.com/cryptuon/dgbit/blob/main/CHANGELOG.md) at the repo root; the table above is a mirror.
