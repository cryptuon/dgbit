"""
Strategy Service - Pluggable strategy execution via NNG

Provides:
- Strategy registry for dynamic loading
- Signal generation via REQ/REP
- Strategy backtesting interface
- Performance metrics
"""

import asyncio
import json
import logging
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

# Add parent to path
SRC_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(SRC_DIR))

import pynng
from loguru import logger

from dgbit_services import (
    Message, ServiceBase, ServiceType, ServiceRegistry,
    Event, EventType
)


@dataclass
class StrategyConfig:
    """Configuration for a strategy instance."""
    strategy_name: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    capital: float = 10000.0
    risk_per_trade: float = 0.02
    max_positions: int = 5


@dataclass
class Signal:
    """Trading signal from a strategy."""
    strategy_name: str
    symbol: str
    direction: str  # "long" or "short"
    confidence: float  # 0.0 to 1.0
    entry_price: Optional[float] = None
    take_profit: Optional[float] = None
    stop_loss: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StrategyMetrics:
    """Performance metrics for a strategy."""
    strategy_name: str
    total_signals: int = 0
    win_rate: float = 0.0
    avg_return: float = 0.0
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    profit_factor: float = 0.0
    last_updated: datetime = field(default_factory=datetime.utcnow)


class StrategyInterface:
    """Abstract interface for strategies."""

    @property
    def name(self) -> str:
        """Return strategy name."""
        raise NotImplementedError

    @property
    def version(self) -> str:
        """Return strategy version."""
        return "0.1.0"

    def generate_signal(self, data: Any) -> Signal:
        """Generate a trading signal from market data."""
        raise NotImplementedError

    def train(self, data: Any) -> None:
        """Train the strategy if needed."""
        pass

    def get_parameters(self) -> Dict[str, Any]:
        """Return strategy parameters."""
        return {}

    def validate_parameters(self, params: Dict[str, Any]) -> bool:
        """Validate strategy parameters."""
        return True


class StrategyRegistry:
    """
    Registry for strategies with dynamic loading.
    """

    def __init__(self):
        self._strategies: Dict[str, Type[StrategyInterface]] = {}
        self._instances: Dict[str, StrategyInterface] = {}

    def register(self, strategy_class: Type[StrategyInterface]):
        """Register a strategy class."""
        self._strategies[strategy_class.name] = strategy_class
        logger.info(f"Registered strategy: {strategy_class.name}")

    def get(self, name: str) -> Optional[Type[StrategyInterface]]:
        """Get a strategy class by name."""
        return self._strategies.get(name)

    def create(self, name: str, config: StrategyConfig) -> StrategyInterface:
        """Create a strategy instance."""
        strategy_class = self._strategies.get(name)
        if not strategy_class:
            raise ValueError(f"Unknown strategy: {name}")

        instance = strategy_class()
        self._instances[f"{name}_{id(instance)}"] = instance
        return instance

    def list_strategies(self) -> List[Dict[str, Any]]:
        """List all registered strategies."""
        return [
            {
                "name": name,
                "version": cls.version,
                "parameters": cls().get_parameters() if hasattr(cls, 'get_parameters') else {},
            }
            for name, cls in self._strategies.items()
        ]

    def list_instances(self) -> List[str]:
        """List active strategy instances."""
        return list(self._instances.keys())


# Global strategy registry
strategy_registry = StrategyRegistry()


class StrategyService(ServiceBase):
    """
    Strategy execution service via NNG.

    Provides:
    - Signal generation
    - Strategy management
    - Performance tracking
    """

    def __init__(
        self,
        name: str = "strategy_service",
        address: str = "ipc:///tmp/dgbit_strategy.ipc",
    ):
        super().__init__(
            name=name,
            service_type=ServiceType.STRATEGY,
            addresses={"cmd": address}
        )

        self._address = address
        self._socket = None
        self._running = False
        self._strategy_registry = strategy_registry
        self._metrics: Dict[str, StrategyMetrics] = {}

        # Register built-in strategies
        self._register_builtin_strategies()

    def _register_builtin_strategies(self):
        """Register built-in strategies."""
        from dgbit_core.trading.strategy import WaveletReversalStrategy, BaseStrategy

        # Register wavelet strategy
        class WaveletWrapper(BaseStrategy, StrategyInterface):
            @property
            def name(self):
                return "wavelet_reversal"

            def generate_signal(self, data):
                signal_value = super().generate_signal(data)
                from dgbit_core.trading.strategy import TradeDirection
                return Signal(
                    strategy_name=self.name,
                    symbol=data.iloc[0]['symbol'] if 'symbol' in data.columns else 'UNKNOWN',
                    direction=TradeDirection.LONG.value,
                    confidence=signal_value,
                    timestamp=datetime.utcnow(),
                )

        self._strategy_registry.register(WaveletWrapper)

    async def start(self):
        """Start the strategy service."""
        self._socket = pynng.Rep0(listen=self._address)
        logger.info(f"Strategy service listening on {self._address}")

        # Register in service registry
        registry = ServiceRegistry()
        registry.register(self)

        # Publish startup event
        from dgbit_services.events import EventBus
        bus = EventBus()
        bus.publish_sync(EventType.SERVICE_STARTED.value, {
            "service": self.name,
            "address": self._address,
        }, source=self.name)

        self._running = True

        # Main loop
        while self._running:
            try:
                def _recv():
                    return self._socket.recv()

                loop = asyncio.get_event_loop()
                message_data = await loop.run_in_executor(None, _recv)
                message = Message.from_bytes(message_data)

                result = await self.handle_command(message)

                self._socket.send(json.dumps(result).encode("utf-8"))

            except pynng.Timeout:
                await asyncio.sleep(0.01)
            except Exception as e:
                logger.error(f"Strategy service error: {e}")

    async def stop(self):
        """Stop the strategy service."""
        self._running = False

        if self._socket:
            self._socket.close()
            self._socket = None

        logger.info("Strategy service stopped")

    async def handle_command(self, message: Message) -> Dict[str, Any]:
        """Handle strategy commands."""
        command = message.command
        payload = message.payload

        if command == "list_strategies":
            return {
                "success": True,
                "strategies": self._strategy_registry.list_strategies(),
            }

        elif command == "create_strategy":
            try:
                config = StrategyConfig(
                    strategy_name=payload["strategy_name"],
                    parameters=payload.get("parameters", {}),
                    capital=payload.get("capital", 10000.0),
                )
                instance = self._strategy_registry.create(config.strategy_name, config)
                return {
                    "success": True,
                    "instance_id": f"{config.strategy_name}_{id(instance)}",
                }
            except Exception as e:
                return {"success": False, "error": str(e)}

        elif command == "generate_signal":
            try:
                strategy_name = payload["strategy_name"]
                strategy_class = self._strategy_registry.get(strategy_name)

                if not strategy_class:
                    return {"success": False, "error": f"Unknown strategy: {strategy_name}"}

                # Create strategy instance
                instance = strategy_class()

                # Generate signal (data would come from Data Service)
                # For now, return a placeholder
                signal = Signal(
                    strategy_name=strategy_name,
                    symbol=payload.get("symbol", "BTCUSDT"),
                    direction="long",
                    confidence=0.5,
                    timestamp=datetime.utcnow(),
                )

                # Publish signal event
                from dgbit_services.events import EventBus
                bus = EventBus()
                bus.publish_sync(EventType.TRADE_SIGNAL.value, {
                    "strategy": strategy_name,
                    "symbol": signal.symbol,
                    "direction": signal.direction,
                    "confidence": signal.confidence,
                }, source=self.name)

                return {
                    "success": True,
                    "signal": {
                        "strategy_name": signal.strategy_name,
                        "symbol": signal.symbol,
                        "direction": signal.direction,
                        "confidence": signal.confidence,
                        "timestamp": signal.timestamp.isoformat(),
                    }
                }

            except Exception as e:
                logger.error(f"Signal generation error: {e}")
                return {"success": False, "error": str(e)}

        elif command == "get_metrics":
            strategy_name = payload.get("strategy_name")
            if strategy_name:
                metrics = self._metrics.get(strategy_name)
                if metrics:
                    return {"success": True, "metrics": metrics.__dict__}
                return {"success": False, "error": "Metrics not found"}
            else:
                return {
                    "success": True,
                    "metrics": {
                        name: m.__dict__
                        for name, m in self._metrics.items()
                    }
                }

        elif command == "ping":
            return {"status": "ok", "strategies": len(self._strategy_registry.list_strategies())}

        else:
            return {"error": f"Unknown command: {command}"}


# =============================================================================
# Strategy Client
# =============================================================================

class StrategyClient:
    """Client for the Strategy Service."""

    def __init__(self, address: str = "ipc:///tmp/dgbit_strategy.ipc"):
        self.address = address
        self._socket = None

    def _get_socket(self):
        """Get or create socket."""
        if self._socket is None:
            self._socket = pynng.Req0(dial=self.address, block=False)
        return self._socket

    def _send(self, command: str, payload: Dict = None) -> Dict:
        """Send a command and get response."""
        socket = self._get_socket()

        message = Message(
            command=command,
            payload=payload or {},
            source="strategy_client",
        )

        def _sync():
            socket.send(message.to_bytes())
            return socket.recv()

        loop = asyncio.new_event_loop()
        try:
            response = json.loads(loop.run_in_executor(None, _sync).decode("utf-8"))
            return response
        finally:
            loop.close()

    def list_strategies(self) -> List[Dict]:
        """List available strategies."""
        return self._send("list_strategies")

    def create_strategy(self, name: str, parameters: Dict = None) -> Dict:
        """Create a strategy instance."""
        return self._send("create_strategy", {
            "strategy_name": name,
            "parameters": parameters,
        })

    def generate_signal(self, strategy_name: str, symbol: str) -> Dict:
        """Generate a trading signal."""
        return self._send("generate_signal", {
            "strategy_name": strategy_name,
            "symbol": symbol,
        })

    def get_metrics(self, strategy_name: str = None) -> Dict:
        """Get strategy metrics."""
        return self._send("get_metrics", {"strategy_name": strategy_name})

    def close(self):
        """Close the client."""
        if self._socket:
            self._socket.close()
            self._socket = None


# =============================================================================
# Run as Service
# =============================================================================

async def run_strategy_service():
    """Run the strategy service as a standalone process."""
    import argparse

    parser = argparse.ArgumentParser(description="dgbit Strategy Service")
    parser.add_argument("--address", default="ipc:///tmp/dgbit_strategy.ipc")
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()

    # Setup logging
    logger.remove()
    logger.add(sys.stdout, level=args.log_level)

    # Create and run service
    service = StrategyService(address=args.address)

    try:
        await service.start()
    except KeyboardInterrupt:
        await service.stop()


if __name__ == "__main__":
    asyncio.run(run_strategy_service())
