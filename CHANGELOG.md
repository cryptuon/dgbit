# Changelog

All notable changes to dgbit will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- PyPI package publishing support with `pyproject.toml` at root level
- Docker and docker-compose configuration for easy deployment
- Comprehensive MkDocs documentation at `documentation/`
- GitHub Actions CI/CD workflows for testing, docs, PyPI, and Docker
- LICENSE file (MIT)
- MANIFEST.in for package distribution
- .dockerignore for efficient Docker builds
- Frontend Dockerfile and nginx configuration

### Fixed
- Missing import for `get_api_client` in `dgbit-api/src/dgbit_api/api/routes.py`
- Incorrect method call `get_performance_metrics()` in `dgbit-api/src/dgbit_api/workers/backtest_runner.py` - now correctly uses `result.metrics`
- JSON serialization using `json.dumps()` instead of `str()` in `dgbit-api/src/dgbit_api/db/models.py`

### Changed
- Updated README.md with badges, SEO-optimized content for traders, and professional structure

## [0.1.0] - 2026-01-05

### Added
- Initial release of dgbit trading framework
- FastAPI REST API with comprehensive endpoints
- Trading strategies: Wavelet Reversal, MA Crossover, RSI, Bollinger Bands
- Backtesting engine with interactive Plotly reports
- Service bus architecture using NNG
- Vue 3 frontend dashboard
- Bybit API integration
- SQLite persistence for jobs
- WebSocket support for real-time events
