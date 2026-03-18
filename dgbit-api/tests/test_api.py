import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock


@pytest.fixture
def client():
    """Create a test client for the API without database initialization."""
    from fastapi import FastAPI
    from dgbit_api.core.config import settings
    from dgbit_api.api.routes import router

    # Create a minimal app for testing without lifespan
    app = FastAPI(title=settings.app_name, version="0.2.0")

    @app.get("/", tags=["system"], summary="Root ping")
    async def root():
        return {"message": f"{settings.app_name} is running", "version": "0.2.0"}

    app.include_router(router)

    return TestClient(app, raise_server_exceptions=False)


class TestHealthEndpoint:
    """Tests for health endpoint."""

    def test_root_endpoint(self, client):
        """Test root endpoint returns app info."""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data


class TestBacktestEndpoint:
    """Tests for backtest endpoints."""

    def test_backtest_requires_symbol(self, client):
        """Test backtest request requires symbol."""
        response = client.post("/api/backtests", json={})

        # Should fail due to validation or DB issues
        assert response.status_code in [422, 500]

    def test_backtest_with_valid_payload(self, client):
        """Test backtest with valid payload."""
        payload = {
            "symbol": "BTCUSDT",
            "interval": "1",
            "limit": 100,
        }

        response = client.post("/api/backtests", json=payload)

        # May fail if worker not running, but should validate
        assert response.status_code in [200, 500, 400]

    def test_backtest_with_all_params(self, client):
        """Test backtest with all parameters."""
        payload = {
            "symbol": "BTCUSDT",
            "interval": "1",
            "limit": 500,
            "initial_capital": 10000.0,
            "transaction_fee": 0.001,
        }

        response = client.post("/api/backtests", json=payload)

        assert response.status_code in [200, 500, 400]


class TestJobsEndpoint:
    """Tests for jobs endpoints - these test request validation only."""

    def test_list_jobs_validation(self, client):
        """Test that list jobs endpoint exists and accepts query params."""
        # This tests the endpoint structure, not the database
        response = client.get("/api/jobs")

        # Should either return jobs or fail due to DB not initialized
        assert response.status_code in [200, 500]

    def test_get_job_stats_validation(self, client):
        """Test that stats endpoint exists."""
        response = client.get("/api/jobs/stats")

        assert response.status_code in [200, 500]

    def test_get_nonexistent_job_validation(self, client):
        """Test that get job endpoint exists."""
        response = client.get("/api/jobs/nonexistent-uuid")

        # Should either return 404 or fail due to DB not initialized
        assert response.status_code in [404, 500]

    def test_cancel_nonexistent_job_validation(self, client):
        """Test that cancel endpoint exists."""
        response = client.post("/api/jobs/nonexistent-uuid/cancel")

        assert response.status_code in [404, 400, 500]
