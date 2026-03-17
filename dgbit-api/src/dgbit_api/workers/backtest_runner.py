import json
import logging

from dgbit_core.backtesting.backtester import Backtester
from dgbit_core.data.data_fetcher import BybitDataFetcher
from dgbit_core.trading.strategy import TradingStrategy

from dgbit_api.core.config import settings
from dgbit_api.infra.messaging import worker_command_socket

logger = logging.getLogger(__name__)


def run() -> None:
    """Blocking loop waiting for backtest commands."""

    logger.info("Backtest worker listening on %s", settings.nng_command_address)

    fetcher = BybitDataFetcher(
        api_key=settings.bybit_api_key,
        api_secret=settings.bybit_api_secret,
    )
    strategy = TradingStrategy()
    backtester = Backtester()

    with worker_command_socket(settings.nng_command_address) as socket:
        while True:
            message = socket.recv()
            payload = json.loads(message.decode("utf-8"))
            logger.info("Received backtest command: %s", payload)

            if not settings.bybit_api_key or not settings.bybit_api_secret:
                warning = "Missing Bybit credentials; cannot execute backtest"
                logger.warning(warning)
                socket.send(json.dumps({"error": warning}).encode("utf-8"))
                continue

            symbol = payload.get("symbol", settings.default_symbol)
            limit = int(payload.get("limit", 500))
            data = fetcher.get_kline_data(symbol, limit=limit)

            backtester.strategy = strategy
            results = backtester.run(data)
            metrics = backtester.get_performance_metrics()

            response = {
                "symbol": symbol,
                "metrics": metrics,
                "results": results.to_dict(orient="records"),
            }
            socket.send(json.dumps(response).encode("utf-8"))


if __name__ == "__main__":
    logging.basicConfig(level=settings.log_level)
    run()
