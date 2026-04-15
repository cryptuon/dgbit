# Installation

This guide covers all the ways to install dgbit.

## Requirements

- Python 3.11 or later
- pip 21.0 or later
- (Optional) Docker 20.10+ for containerized deployment

## Installation Methods

### PyPI (Recommended)

The simplest way to install dgbit is from PyPI:

```bash
pip install dgbit
```

To install with development dependencies:

```bash
pip install dgbit[dev]
```

To install with documentation dependencies:

```bash
pip install dgbit[docs]
```

### Docker

Pull the official Docker image:

```bash
docker pull cryptuon/dgbit:latest
```

Or use a specific version:

```bash
docker pull cryptuon/dgbit:0.1.0
```

### From Source

For development or to get the latest changes:

```bash
# Clone the repository
git clone https://github.com/cryptuon/dgbit.git
cd dgbit

# Install in editable mode
pip install -e ".[dev]"
```

### Poetry (Backend Development)

If you're working on the FastAPI backend:

```bash
cd dgbit-api
poetry install
```

### npm (Frontend Development)

For the Vue 3 dashboard:

```bash
cd dgbit-ui
npm install
```

## Verifying Installation

### Python Package

```python
import dgbit_core
print(dgbit_core.__version__)
```

### CLI

```bash
dgbit --version
```

### API Server

```bash
dgbit-api
# Visit http://localhost:8000/api/health
```

## Dependencies

dgbit depends on several key packages:

| Package | Purpose |
|---------|---------|
| `fastapi` | REST API framework |
| `uvicorn` | ASGI server |
| `pandas` | Data manipulation |
| `numpy` | Numerical computing |
| `pybit` | Bybit API client |
| `pywavelets` | Wavelet transforms |
| `plotly` | Interactive charts |
| `pynng` | Service bus messaging |
| `tortoise-orm` | Database ORM |

## Platform Notes

### Linux

All features are fully supported on Linux.

### macOS

All features are fully supported on macOS. Apple Silicon (M1/M2) is supported.

### Windows

dgbit works on Windows with some caveats:

- NNG IPC sockets use a different path format
- Docker Desktop required for containerized deployment

## Troubleshooting

### ImportError: No module named 'dgbit_core'

Ensure you've installed the package correctly:

```bash
pip install --upgrade dgbit
```

### NNG Socket Errors

If you see NNG-related errors, ensure the IPC directories exist:

```bash
# Linux/macOS
mkdir -p /tmp

# Windows (use named pipes)
# Modify NNG_COMMAND_ADDRESS in .env
```

### Bybit API Errors

Verify your API keys and network connectivity:

```python
from pybit.unified_trading import HTTP

session = HTTP(
    testnet=True,
    api_key="your_key",
    api_secret="your_secret",
)
print(session.get_wallet_balance(accountType="SPOT"))
```

## Next Steps

- [Quick Start Guide](quickstart.md) - Run your first backtest
- [Configuration](configuration.md) - Set up your environment
