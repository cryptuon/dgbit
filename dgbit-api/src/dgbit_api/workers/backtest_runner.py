import asyncio
import json
import logging
import sys
from pathlib import Path

# Add the shared python directory to the path
SHARED_DIR = Path(__file__).parent.parent.parent.parent / "shared" / "python"
sys.path.insert(0, str(SHARED_DIR))

from dgbit_core.backtesting.backtester import Backtester
from dgbit_core.data.data_fetcher import BybitDataFetcher
from dgbit_core.trading.strategy import TradingStrategy

# Add src to path for dgbit_api imports
SRC_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(SRC_DIR))

from dgbit_api.core.config import settings
from dgbit_api.core.logging import setup_logging
from dgbit_api.db.connection import init_db, close_db
from dgbit_api.infra.messaging import NNGWorker
from dgbit_api.services.job_service import JobService
from dgbit_api.db.models import JobType


# Configure logging
setup_logging(log_level=settings.log_level)
logger = logging.getLogger(__name__)


async def run_backtest_worker():
    """Run the backtest worker that processes jobs from the queue."""
    logger.info("Initializing backtest worker...")

    # Initialize database for job status updates
    await init_db()

    # Initialize components
    fetcher = BybitDataFetcher(
        api_key=settings.bybit_api_key,
        api_secret=settings.bybit_api_secret,
    )
    strategy = TradingStrategy()
    backtester = Backtester()

    # Create worker
    worker = NNGWorker(settings.nng_command_address)
    await worker.start()

    logger.info(f"Backtest worker listening on {settings.nng_command_address}")

    try:
        while True:
            try:
                message = await worker.recv()
                logger.info(f"Received message: {message}")

                job_uuid = message.get("job_uuid")
                payload = message.get("payload", {})

                if not job_uuid:
                    await worker.send({"error": "Missing job_uuid"})
                    continue

                # Check Bybit credentials
                if not settings.bybit_api_key or not settings.bybit_api_secret:
                    warning = "Missing Bybit credentials; cannot execute backtest"
                    logger.warning(warning)
                    await JobService.mark_failed(job_uuid, warning)
                    await worker.send({"error": warning})
                    continue

                # Mark job as running
                await JobService.mark_running(job_uuid)

                # Extract parameters
                symbol = payload.get("symbol", settings.default_symbol)
                limit = int(payload.get("limit", 500))

                logger.info(f"Running backtest for {symbol} with limit {limit}")

                # Fetch data
                data = fetcher.get_kline_data(symbol, limit=limit)

                # Run backtest
                backtester.strategy = strategy
                result = backtester.run(data)

                # Prepare response
                response = {
                    "job_uuid": job_uuid,
                    "symbol": symbol,
                    "metrics": result.metrics,
                    "trades": [
                        {
                            "timestamp": str(t.timestamp),
                            "action": t.action,
                            "symbol": t.symbol,
                            "price": t.price,
                            "quantity": t.quantity,
                            "capital": t.capital,
                            "pnl": t.pnl,
                            "pnl_pct": t.pnl_pct,
                        }
                        for t in result.trades
                    ],
                }

                # Mark job as complete
                await JobService.mark_complete(job_uuid, response)

                await worker.send(response)
                logger.info(f"Backtest {job_uuid} completed successfully")

            except Exception as e:
                logger.error(f"Error processing message: {e}", exc_info=True)
                if 'job_uuid' in locals():
                    await JobService.mark_failed(job_uuid, str(e))
                await worker.send({"error": str(e)})

    except asyncio.CancelledError:
        logger.info("Worker shutdown requested")
    finally:
        await worker.close()
        await close_db()


if __name__ == "__main__":
    try:
        asyncio.run(run_backtest_worker())
    except KeyboardInterrupt:
        logger.info("Worker interrupted by user")
