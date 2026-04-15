# dgbit - Algorithmic Trading Framework for Bybit
# Multi-stage Dockerfile for production deployment

# ============================================
# Stage 1: Python dependencies
# ============================================
FROM python:3.11-slim as python-deps

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install pip and upgrade
RUN pip install --no-cache-dir --upgrade pip

# Copy dependency files
COPY pyproject.toml ./
COPY dgbit-api/pyproject.toml ./dgbit-api/
COPY dgbit-api/shared/python/pyproject.toml ./dgbit-api/shared/python/

# Install dependencies
RUN pip install --no-cache-dir . || pip install --no-cache-dir \
    fastapi>=0.115.0 \
    "uvicorn[standard]>=0.34.0" \
    pynng>=0.8.1 \
    pydantic>=2.5.0 \
    pydantic-settings>=2.5.0 \
    tortoise-orm>=0.21.0 \
    aiosqlite>=0.19.0 \
    pandas>=2.1.0 \
    numpy>=1.26.0 \
    pybit>=5.0.0 \
    pywavelets>=1.5.0 \
    plotly>=5.18.0 \
    ccxt>=4.0.0 \
    loguru>=0.7.2 \
    click>=8.1.0 \
    python-json-logger>=2.0.7 \
    pyarrow>=15.0.0

# ============================================
# Stage 2: Production image
# ============================================
FROM python:3.11-slim as production

LABEL maintainer="Dipankar Sarkar <me@dipankar.name>"
LABEL description="dgbit - Algorithmic Trading Framework for Bybit"
LABEL version="0.1.0"

# Create non-root user for security
RUN groupadd -r dgbit && useradd -r -g dgbit dgbit

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=python-deps /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=python-deps /usr/local/bin /usr/local/bin

# Copy application code
COPY dgbit-api/src ./src
COPY dgbit-api/shared ./shared

# Set Python path
ENV PYTHONPATH="/app/src:/app/shared/python:${PYTHONPATH}"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Create necessary directories
RUN mkdir -p /app/db /app/reports /app/logs && \
    chown -R dgbit:dgbit /app

# Switch to non-root user
USER dgbit

# Expose API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Default command: run the API server
CMD ["uvicorn", "dgbit_api.main:app", "--host", "0.0.0.0", "--port", "8000"]

# ============================================
# Stage 3: Development image (optional)
# ============================================
FROM production as development

USER root

# Install dev dependencies
RUN pip install --no-cache-dir \
    pytest>=8.0.0 \
    pytest-asyncio>=0.24.0 \
    httpx>=0.27.0 \
    ruff>=0.4.0

USER dgbit

# Override for development with hot reload
CMD ["uvicorn", "dgbit_api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
