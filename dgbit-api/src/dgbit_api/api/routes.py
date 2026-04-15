from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from dgbit_api.core.config import settings
from dgbit_api.core.logging import get_logger
from dgbit_api.db.models import JobStatus, JobType
from dgbit_api.services.job_service import JobService
from dgbit_api.infra.messaging import get_api_client

# Import service bus clients
from dgbit_services import DataServiceClient
from dgbit_services.data import get_data_api_helper
from dgbit_services.strategy import StrategyClient
from dgbit_services.execution import ExecutionClient

logger = get_logger(__name__)
router = APIRouter(prefix=settings.api_prefix)

# Service bus clients (lazy initialization)
_data_client: Optional[DataServiceClient] = None
_strategy_client: Optional[StrategyClient] = None
_execution_client: Optional[ExecutionClient] = None


def get_data_client() -> DataServiceClient:
    """Get or create data service client."""
    global _data_client
    if _data_client is None:
        _data_client = DataServiceClient()
    return _data_client


def get_strategy_client() -> StrategyClient:
    """Get or create strategy service client."""
    global _strategy_client
    if _strategy_client is None:
        _strategy_client = StrategyClient()
    return _strategy_client


def get_execution_client() -> ExecutionClient:
    """Get or create execution service client."""
    global _execution_client
    if _execution_client is None:
        _execution_client = ExecutionClient()
    return _execution_client


class JobCreateRequest(BaseModel):
    job_type: JobType
    payload: dict


class JobResponse(BaseModel):
    id: int
    uuid: str
    job_type: str
    status: str
    payload: dict
    result: Optional[dict] = None
    error: Optional[str] = None
    created_at: str
    updated_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


class BacktestRequest(BaseModel):
    symbol: str = "BTCUSDT"
    interval: str = "1"
    limit: int = 1000
    initial_capital: float = 10000.0
    transaction_fee: float = 0.001


def job_to_response(job) -> dict:
    """Convert Job model to response dict."""
    import json
    return {
        "id": job.id,
        "uuid": job.uuid,
        "job_type": job.job_type,
        "status": job.status,
        "payload": json.loads(job.payload),
        "result": json.loads(job.result) if job.result else None,
        "error": job.error,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "updated_at": job.updated_at.isoformat() if job.updated_at else None,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
    }


@router.get("/health", tags=["system"], summary="Service health")
async def health() -> dict:
    """Basic health and metadata endpoint."""
    stats = await JobService.get_stats()
    return {
        "service": settings.app_name,
        "environment": settings.environment,
        "status": "ok",
        "version": "0.2.0",
        "stats": stats,
    }


@router.post("/backtests", tags=["backtests"], summary="Schedule a backtest")
async def schedule_backtest(request: BacktestRequest) -> dict:
    """
    Schedule a backtest job to be processed by a worker.
    The job is dispatched via NNG to the backtest worker.
    """
    payload = request.model_dump()
    job = await JobService.create(JobType.BACKTEST, payload)

    # Dispatch to worker via NNG
    try:
        client = get_api_client()
        await client.connect()

        message = {
            "job_uuid": job.uuid,
            "payload": payload,
        }

        logger.info(f"Dispatching backtest job {job.uuid} to worker")
        response = await client.send(message)

        # Mark job as running
        await JobService.mark_running(job.uuid)

        return {
            "job_id": job.uuid,
            "status": JobStatus.RUNNING.value,
            "message": "Backtest job dispatched",
        }
    except Exception as e:
        logger.error(f"Failed to dispatch backtest job: {e}")
        # Job is created but worker dispatch failed
        return {
            "job_id": job.uuid,
            "status": job.status,
            "warning": "Job created but worker dispatch failed",
        }


@router.get("/jobs", tags=["jobs"], summary="List jobs")
async def list_jobs(
    status: Optional[JobStatus] = Query(None, description="Filter by status"),
    job_type: Optional[JobType] = Query(None, description="Filter by type"),
    limit: int = Query(50, ge=1, le=100),
) -> List[dict]:
    """Return all jobs with optional filters."""
    jobs = await JobService.list_jobs(status=status, job_type=job_type, limit=limit)
    return [job_to_response(job) for job in jobs]


@router.get("/jobs/stats", tags=["jobs"], summary="Get job statistics")
async def get_job_stats() -> dict:
    """Return job statistics."""
    return await JobService.get_stats()


@router.get("/jobs/{job_uuid}", tags=["jobs"], summary="Get job by UUID")
async def get_job(job_uuid: str) -> dict:
    """Return a specific job by UUID."""
    job = await JobService.get_by_uuid(job_uuid)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job_to_response(job)


@router.post("/jobs/{job_uuid}/cancel", tags=["jobs"], summary="Cancel a job")
async def cancel_job(job_uuid: str) -> dict:
    """Cancel a pending or running job."""
    job = await JobService.get_by_uuid(job_uuid)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status not in [JobStatus.PENDING.value, JobStatus.RUNNING.value]:
        raise HTTPException(status_code=400, detail=f"Cannot cancel job in {job.status} status")

    # Update job status - in a real app, you'd also signal the worker to stop
    from dgbit_api.db.models import Job
    job.status = JobStatus.CANCELLED.value
    await job.save()

    return {"job_id": job_uuid, "status": JobStatus.CANCELLED.value}


# =============================================================================
# Data Service Endpoints
# =============================================================================

class MarketDataRequest(BaseModel):
    symbol: str = "BTCUSDT"
    interval: str = "1h"
    limit: int = 100
    use_cache: bool = True


@router.get("/data/symbols", tags=["data"], summary="List available symbols")
async def list_symbols(exchange: str = Query("bybit", description="Exchange name")) -> dict:
    """Get list of available trading symbols."""
    helper = get_data_api_helper()
    symbols = await helper.get_available_symbols()
    return {"exchange": exchange, "symbols": symbols, "count": len(symbols)}


@router.get("/data/klines", tags=["data"], summary="Get kline data")
async def get_klines(
    symbol: str = Query("BTCUSDT", description="Trading symbol"),
    interval: str = Query("1h", description="Time interval"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records"),
    use_cache: bool = Query(True, description="Use cached data if available"),
) -> dict:
    """Fetch kline/candlestick data."""
    client = get_data_client()
    response = await client.get_klines(
        symbol=symbol,
        interval=interval,
        limit=limit,
        use_cache=use_cache,
    )
    return response


@router.get("/data/cache", tags=["data"], summary="Get cache status")
async def get_cache_status() -> dict:
    """Get data cache status."""
    client = get_data_client()
    return await client.get_cache_status()


@router.delete("/data/cache", tags=["data"], summary="Clear data cache")
async def clear_cache() -> dict:
    """Clear the data cache."""
    client = get_data_client()
    return await client.clear_cache()


# =============================================================================
# Strategy Service Endpoints
# =============================================================================

@router.get("/strategies", tags=["strategies"], summary="List available strategies")
async def list_strategies() -> dict:
    """Get list of available trading strategies."""
    client = get_strategy_client()
    response = client.list_strategies()
    return response


@router.post("/strategies/{strategy_name}/signal", tags=["strategies"], summary="Generate signal")
async def generate_signal(
    strategy_name: str,
    symbol: str = Query("BTCUSDT", description="Trading symbol"),
) -> dict:
    """Generate a trading signal from a strategy."""
    client = get_strategy_client()
    response = client.generate_signal(strategy_name, symbol)
    return response


# =============================================================================
# Execution Service Endpoints
# =============================================================================

class OrderRequest(BaseModel):
    symbol: str
    side: str  # "buy" or "sell"
    quantity: float
    order_type: str = "market"
    price: Optional[float] = None


class ClosePositionRequest(BaseModel):
    symbol: str
    side: str = "both"


@router.get("/execution/orders", tags=["execution"], summary="List orders")
async def list_orders(symbol: Optional[str] = None, status: Optional[str] = None) -> dict:
    """Get all orders."""
    client = get_execution_client()
    return client.get_orders(symbol=symbol, status=status)


@router.get("/execution/orders/{order_id}", tags=["execution"], summary="Get order")
async def get_order(order_id: str) -> dict:
    """Get order status."""
    client = get_execution_client()
    return client.get_order(order_id)


@router.post("/execution/orders", tags=["execution"], summary="Create order")
async def create_order(request: OrderRequest) -> dict:
    """Create a new order."""
    client = get_execution_client()
    return client.create_order(
        symbol=request.symbol,
        side=request.side,
        quantity=request.quantity,
        order_type=request.order_type,
        price=request.price,
    )


@router.delete("/execution/orders/{order_id}", tags=["execution"], summary="Cancel order")
async def cancel_order(order_id: str, symbol: str) -> dict:
    """Cancel an order."""
    client = get_execution_client()
    return client.cancel_order(order_id, symbol)


@router.get("/execution/positions", tags=["execution"], summary="List positions")
async def list_positions(symbol: str = None) -> dict:
    """Get all positions."""
    client = get_execution_client()
    return client.get_positions(symbol=symbol)


@router.get("/execution/balance", tags=["execution"], summary="Get balance")
async def get_balance() -> dict:
    """Get account balance."""
    client = get_execution_client()
    return client.get_balance()


@router.post("/execution/positions/close", tags=["execution"], summary="Close position")
async def close_position(request: ClosePositionRequest) -> dict:
    """Close a position."""
    client = get_execution_client()
    return client.close_position(request.symbol, request.side)


@router.get("/execution/ping", tags=["execution"], summary="Ping execution service")
async def ping_execution() -> dict:
    """Check if execution service is available."""
    client = get_execution_client()
    return client._send("ping", {})


# =============================================================================
# WebSocket Endpoints for Real-time Updates
# =============================================================================

class ConnectionManager:
    """Manage WebSocket connections."""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def send_message(self, message: dict, websocket: WebSocket = None):
        """Send message to specific client or all clients."""
        if websocket:
            if websocket in self.active_connections:
                await websocket.send_json(message)
        else:
            for connection in self.active_connections:
                await connection.send_json(message)


manager = ConnectionManager()


@router.websocket("/ws/events")
async def websocket_events(websocket: WebSocket):
    """
    WebSocket endpoint for real-time event streaming.

    Subscribe to receive events:
    - job.created
    - job.started
    - job.completed
    - job.failed
    - trade.executed
    """
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive, receive any client messages
            data = await websocket.receive_text()
            # Echo back for ping/pong or handle subscriptions
            await websocket.send_json({"type": "ping", "received": data})
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@router.websocket("/ws/jobs/{job_uuid}")
async def websocket_job_updates(websocket: WebSocket, job_uuid: str):
    """
    WebSocket endpoint for job-specific updates.

    Subscribe to receive updates for a specific job.
    """
    await manager.connect(websocket)
    try:
        # Send initial confirmation
        await websocket.send_json({
            "type": "subscribed",
            "job_uuid": job_uuid,
            "message": "Subscribed to job updates"
        })

        while True:
            data = await websocket.receive_text()
            # Handle client messages (ping, unsubscribe, etc.)
            await websocket.send_json({"type": "ack", "job_uuid": job_uuid})
    except WebSocketDisconnect:
        manager.disconnect(websocket)

