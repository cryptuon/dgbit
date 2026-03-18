"""
Execution Service - Trade execution via NNG

Provides:
- Order management (create, cancel, modify)
- Position tracking
- Trade execution with multiple exchange support
- Risk management integration
"""

import asyncio
import json
import logging
import sys
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add parent to path
SRC_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(SRC_DIR))

import pynng
from loguru import logger

from dgbit_services import (
    Message, ServiceBase, ServiceType, ServiceRegistry,
    Event, EventType
)


class OrderSide(str, Enum):
    """Order side."""
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    """Order type."""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderStatus(str, Enum):
    """Order status."""
    PENDING = "pending"
    OPEN = "open"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class PositionSide(str, Enum):
    """Position side."""
    LONG = "long"
    SHORT = "short"
    BOTH = "both"


@dataclass
class Order:
    """Trading order."""
    order_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: float
    price: Optional[float] = None
    stop_price: Optional[float] = None
    status: OrderStatus = OrderStatus.PENDING
    filled_qty: float = 0.0
    avg_price: Optional[float] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    executed_at: Optional[datetime] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "order_id": self.order_id,
            "symbol": self.symbol,
            "side": self.side.value,
            "order_type": self.order_type.value,
            "quantity": self.quantity,
            "price": self.price,
            "stop_price": self.stop_price,
            "status": self.status.value,
            "filled_qty": self.filled_qty,
            "avg_price": self.avg_price,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass
class Position:
    """Trading position."""
    symbol: str
    side: PositionSide
    quantity: float
    entry_price: float
    mark_price: Optional[float] = None
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    leverage: float = 1.0
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "side": self.side.value,
            "quantity": self.quantity,
            "entry_price": self.entry_price,
            "mark_price": self.mark_price,
            "unrealized_pnl": self.unrealized_pnl,
            "realized_pnl": self.realized_pnl,
            "leverage": self.leverage,
        }


@dataclass
class Trade:
    """Executed trade."""
    trade_id: str
    order_id: str
    symbol: str
    side: OrderSide
    quantity: float
    price: float
    fee: float = 0.0
    fee_currency: str = "USDT"
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trade_id": self.trade_id,
            "order_id": self.order_id,
            "symbol": self.symbol,
            "side": self.side.value,
            "quantity": self.quantity,
            "price": self.price,
            "fee": self.fee,
            "fee_currency": self.fee_currency,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class ExecutionConfig:
    """Configuration for execution service."""
    exchange: str = "bybit"
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    testnet: bool = True
    default_quantity: float = 0.001
    max_leverage: float = 10.0
    risk_per_trade: float = 0.02


class ExchangeAdapter:
    """Abstract adapter for exchange operations."""

    @property
    def name(self) -> str:
        raise NotImplementedError

    async def create_order(self, order: Order) -> Order:
        raise NotImplementedError

    async def cancel_order(self, order_id: str, symbol: str) -> bool:
        raise NotImplementedError

    async def get_order(self, order_id: str, symbol: str) -> Optional[Order]:
        raise NotImplementedError

    async def get_positions(self, symbol: str = None) -> List[Position]:
        raise NotImplementedError

    async def get_balance(self) -> Dict[str, float]:
        raise NotImplementedError


class BybitAdapter(ExchangeAdapter):
    """Bybit exchange adapter."""

    def __init__(self, config: ExecutionConfig):
        self.config = config
        self._client = None

    @property
    def name(self) -> str:
        return "bybit"

    async def _get_client(self):
        """Get or create Bybit client."""
        if self._client is None:
            from pybit import HTTP
            self._client = HTTP(
                endpoint="https://api.bybit.com" if not self.config.testnet else "https://api-testnet.bybit.com",
                api_key=self.config.api_key,
                api_secret=self.config.api_secret,
            )
        return self._client

    async def create_order(self, order: Order) -> Order:
        """Create an order on Bybit."""
        client = await self._get_client()

        try:
            # Map order to Bybit format
            action = "Buy" if order.side == OrderSide.BUY else "Sell"

            if order.order_type == OrderType.MARKET:
                response = client.place_active_order(
                    symbol=order.symbol.replace("USDT", ""),
                    side=action,
                    order_type="Market",
                    qty=str(order.quantity),
                    time_in_force="GoodTillCancel",
                )
            elif order.order_type == OrderType.LIMIT:
                response = client.place_active_order(
                    symbol=order.symbol.replace("USDT", ""),
                    side=action,
                    order_type="Limit",
                    qty=str(order.quantity),
                    price=str(order.price),
                    time_in_force="GoodTillCancel",
                )
            else:
                raise ValueError(f"Unsupported order type: {order.order_type}")

            order.order_id = response["result"]["order_id"]
            order.status = OrderStatus.OPEN

            logger.info(f"Created order {order.order_id} on Bybit")

        except Exception as e:
            order.status = OrderStatus.REJECTED
            order.error = str(e)
            logger.error(f"Failed to create order: {e}")

        return order

    async def cancel_order(self, order_id: str, symbol: str) -> bool:
        """Cancel an order."""
        client = await self._get_client()

        try:
            client.cancel_active_order(
                symbol=symbol.replace("USDT", ""),
                order_id=order_id,
            )
            logger.info(f"Cancelled order {order_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to cancel order {order_id}: {e}")
            return False

    async def get_order(self, order_id: str, symbol: str) -> Optional[Order]:
        """Get order status."""
        client = await self._get_client()

        try:
            response = client.get_active_order(
                symbol=symbol.replace("USDT", ""),
                order_id=order_id,
            )

            result = response["result"]
            if result:
                order_data = result[0]
                return Order(
                    order_id=order_data["order_id"],
                    symbol=symbol,
                    side=OrderSide.BUY if order_data["side"] == "Buy" else OrderSide.SELL,
                    order_type=OrderType(order_data["order_type"].lower()),
                    quantity=float(order_data["qty"]),
                    price=float(order_data["price"]) if order_data["price"] else None,
                    filled_qty=float(order_data["cum_exec_qty"]),
                    avg_price=float(order_data["avg_price"]) if order_data["avg_price"] else None,
                    status=self._map_status(order_data["order_status"]),
                )
        except Exception as e:
            logger.error(f"Failed to get order {order_id}: {e}")

        return None

    def _map_status(self, status: str) -> OrderStatus:
        """Map Bybit status to OrderStatus."""
        status_map = {
            "Created": OrderStatus.PENDING,
            "New": OrderStatus.OPEN,
            "PartiallyFilled": OrderStatus.OPEN,
            "Filled": OrderStatus.FILLED,
            "Cancelled": OrderStatus.CANCELLED,
            "Rejected": OrderStatus.REJECTED,
        }
        return status_map.get(status, OrderStatus.PENDING)

    async def get_positions(self, symbol: str = None) -> List[Position]:
        """Get positions."""
        client = await self._get_client()

        positions = []
        try:
            response = client.my_position(
                symbol=symbol.replace("USDT", "") if symbol else None
            )

            for pos in response["result"]:
                if float(pos["size"]) > 0:
                    side = PositionSide.LONG if pos["side"] == "Buy" else PositionSide.SHORT
                    positions.append(Position(
                        symbol=pos["symbol"] + "USDT",
                        side=side,
                        quantity=float(pos["size"]),
                        entry_price=float(pos["entry_price"]),
                        mark_price=float(pos["mark_price"]),
                        unrealized_pnl=float(pos["unrealised_pnl"]),
                        leverage=float(pos["leverage"]),
                    ))
        except Exception as e:
            logger.error(f"Failed to get positions: {e}")

        return positions

    async def get_balance(self) -> Dict[str, float]:
        """Get account balance."""
        client = await self._get_client()

        try:
            response = client.get_wallet_balance()
            balance = {}
            for coin, data in response["result"].items():
                balance[coin] = float(data["available_balance"])
            return balance
        except Exception as e:
            logger.error(f"Failed to get balance: {e}")
            return {}


class SimulatedAdapter(ExchangeAdapter):
    """Simulated exchange adapter for backtesting."""

    def __init__(self, config: ExecutionConfig):
        self.config = config
        self._orders: Dict[str, Order] = {}
        self._positions: Dict[str, Position] = {}
        self._trades: List[Trade] = []
        self._balance: Dict[str, float] = {"USDT": 100000.0}
        self._order_counter = 0

    @property
    def name(self) -> str:
        return "simulated"

    async def create_order(self, order: Order) -> Order:
        """Simulate order creation."""
        self._order_counter += 1
        order.order_id = f"sim_{self._order_counter}"
        order.status = OrderStatus.OPEN
        self._orders[order.order_id] = order
        logger.info(f"[SIMULATED] Created order {order.order_id}")
        return order

    async def cancel_order(self, order_id: str, symbol: str) -> bool:
        """Simulate order cancellation."""
        if order_id in self._orders:
            self._orders[order_id].status = OrderStatus.CANCELLED
            logger.info(f"[SIMULATED] Cancelled order {order_id}")
            return True
        return False

    async def get_order(self, order_id: str, symbol: str) -> Optional[Order]:
        """Get simulated order."""
        return self._orders.get(order_id)

    async def get_positions(self, symbol: str = None) -> List[Position]:
        """Get simulated positions."""
        positions = list(self._positions.values())
        if symbol:
            positions = [p for p in positions if p.symbol == symbol]
        return positions

    async def get_balance(self) -> Dict[str, float]:
        """Get simulated balance."""
        return self._balance.copy()

    async def execute_order(self, order: Order, current_price: float) -> Order:
        """Simulate order execution at current price."""
        if order.status != OrderStatus.OPEN:
            return order

        # Fill the order
        order.status = OrderStatus.FILLED
        order.filled_qty = order.quantity
        order.avg_price = current_price
        order.executed_at = datetime.utcnow()

        # Update position
        pos_key = f"{order.symbol}_{order.side.value}"
        if order.side == OrderSide.BUY:
            if pos_key in self._positions:
                pos = self._positions[pos_key]
                avg_price = (pos.entry_price * pos.quantity + current_price * order.quantity) / (pos.quantity + order.quantity)
                pos.quantity += order.quantity
                pos.entry_price = avg_price
            else:
                self._positions[pos_key] = Position(
                    symbol=order.symbol,
                    side=PositionSide.LONG,
                    quantity=order.quantity,
                    entry_price=current_price,
                )
        else:
            if pos_key in self._positions:
                pos = self._positions[pos_key]
                avg_price = (pos.entry_price * pos.quantity + current_price * order.quantity) / (pos.quantity + order.quantity)
                pos.quantity += order.quantity
                pos.entry_price = avg_price
            else:
                self._positions[pos_key] = Position(
                    symbol=order.symbol,
                    side=PositionSide.SHORT,
                    quantity=order.quantity,
                    entry_price=current_price,
                )

        # Record trade
        trade = Trade(
            trade_id=f"trade_{order.order_id}",
            order_id=order.order_id,
            symbol=order.symbol,
            side=order.side,
            quantity=order.quantity,
            price=current_price,
            fee=order.quantity * current_price * 0.001,  # 0.1% fee
        )
        self._trades.append(trade)

        # Update balance
        cost = order.quantity * current_price
        if order.side == OrderSide.BUY:
            self._balance["USDT"] -= cost + trade.fee
        else:
            self._balance["USDT"] += cost - trade.fee

        logger.info(f"[SIMULATED] Executed order {order.order_id} at {current_price}")
        return order


class ExecutionService(ServiceBase):
    """
    Trade execution service via NNG.

    Provides:
    - Order management
    - Position tracking
    - Multi-exchange support via adapters
    - Risk management
    """

    def __init__(
        self,
        name: str = "execution_service",
        address: str = "ipc:///tmp/dgbit_execution.ipc",
        exchange: str = "simulated",
        **kwargs
    ):
        super().__init__(
            name=name,
            service_type=ServiceType.EXECUTION,
            addresses={"cmd": address}
        )

        self._address = address
        self._socket = None
        self._running = False
        self._config = ExecutionConfig(exchange=exchange, **kwargs)
        self._adapter = self._create_adapter()
        self._orders: Dict[str, Order] = {}
        self._trades: List[Trade] = []
        self._subscribers: List[str] = []

    def _create_adapter(self) -> ExchangeAdapter:
        """Create exchange adapter."""
        if self._config.exchange == "bybit":
            return BybitAdapter(self._config)
        return SimulatedAdapter(self._config)

    def _get_socket(self):
        """Get or create REP socket."""
        if self._socket is None:
            self._socket = pynng.Rep0(listen=self._address)
            logger.info(f"Execution service listening on {self._address}")
        return self._socket

    async def start(self):
        """Start the execution service."""
        self._get_socket()

        # Register in service registry
        registry = ServiceRegistry()
        registry.register(self)

        # Publish startup event
        from dgbit_services.events import EventBus
        bus = EventBus()
        bus.publish_sync(EventType.SERVICE_STARTED.value, {
            "service": self.name,
            "address": self._address,
            "exchange": self._config.exchange,
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
                logger.error(f"Execution service error: {e}")

    async def stop(self):
        """Stop the execution service."""
        self._running = False

        if self._socket:
            self._socket.close()
            self._socket = None

        logger.info("Execution service stopped")

    async def handle_command(self, message: Message) -> Dict[str, Any]:
        """Handle execution commands."""
        command = message.command
        payload = message.payload

        if command == "create_order":
            return await self._create_order(payload)

        elif command == "cancel_order":
            return await self._cancel_order(payload)

        elif command == "get_order":
            return self._get_order(payload)

        elif command == "get_orders":
            return self._get_orders(payload)

        elif command == "get_positions":
            return await self._get_positions(payload)

        elif command == "get_balance":
            return await self._get_balance()

        elif command == "get_trades":
            return self._get_trades(payload)

        elif command == "close_position":
            return await self._close_position(payload)

        elif command == "ping":
            return {"status": "ok", "exchange": self._config.exchange}

        else:
            return {"error": f"Unknown command: {command}"}

    async def _create_order(self, payload: Dict) -> Dict[str, Any]:
        """Create a new order."""
        try:
            order = Order(
                order_id="",  # Will be set by adapter
                symbol=payload["symbol"],
                side=OrderSide(payload["side"]),
                order_type=OrderType(payload.get("order_type", "market")),
                quantity=float(payload["quantity"]),
                price=float(payload["price"]) if payload.get("price") else None,
                stop_price=float(payload["stop_price"]) if payload.get("stop_price") else None,
            )

            # Apply risk management
            if self._config.risk_per_trade < 1.0:
                max_qty = self._config.default_quantity * (1 + self._config.risk_per_trade)
                order.quantity = min(order.quantity, max_qty)

            order = await self._adapter.create_order(order)

            self._orders[order.order_id] = order

            # Publish event
            from dgbit_services.events import EventBus
            bus = EventBus()
            bus.publish_sync(EventType.TRADE_SIGNAL.value, {
                "type": "order_created",
                "order_id": order.order_id,
                "symbol": order.symbol,
                "side": order.side.value,
                "quantity": order.quantity,
            }, source=self.name)

            return {"success": True, "order": order.to_dict()}

        except Exception as e:
            logger.error(f"Create order error: {e}")
            return {"success": False, "error": str(e)}

    async def _cancel_order(self, payload: Dict) -> Dict[str, Any]:
        """Cancel an order."""
        try:
            order_id = payload["order_id"]
            symbol = payload["symbol"]

            success = await self._adapter.cancel_order(order_id, symbol)

            if order_id in self._orders:
                self._orders[order_id].status = OrderStatus.CANCELLED

            return {"success": success, "order_id": order_id}

        except Exception as e:
            logger.error(f"Cancel order error: {e}")
            return {"success": False, "error": str(e)}

    def _get_order(self, payload: Dict) -> Dict[str, Any]:
        """Get order status."""
        try:
            order = self._orders.get(payload["order_id"])
            if order:
                return {"success": True, "order": order.to_dict()}
            return {"success": False, "error": "Order not found"}

        except Exception as e:
            logger.error(f"Get order error: {e}")
            return {"success": False, "error": str(e)}

    def _get_orders(self, payload: Dict) -> Dict[str, Any]:
        """Get all orders."""
        try:
            symbol = payload.get("symbol")
            status = payload.get("status")

            orders = list(self._orders.values())
            if symbol:
                orders = [o for o in orders if o.symbol == symbol]
            if status:
                orders = [o for o in orders if o.status.value == status]

            return {
                "success": True,
                "orders": [o.to_dict() for o in orders],
                "count": len(orders),
            }

        except Exception as e:
            logger.error(f"Get orders error: {e}")
            return {"success": False, "error": str(e)}

    async def _get_positions(self, payload: Dict) -> Dict[str, Any]:
        """Get positions."""
        try:
            positions = await self._adapter.get_positions(payload.get("symbol"))
            return {
                "success": True,
                "positions": [p.to_dict() for p in positions],
            }

        except Exception as e:
            logger.error(f"Get positions error: {e}")
            return {"success": False, "error": str(e)}

    async def _get_balance(self) -> Dict[str, Any]:
        """Get account balance."""
        try:
            balance = await self._adapter.get_balance()
            return {"success": True, "balance": balance}

        except Exception as e:
            logger.error(f"Get balance error: {e}")
            return {"success": False, "error": str(e)}

    def _get_trades(self, payload: Dict) -> Dict[str, Any]:
        """Get trades."""
        try:
            symbol = payload.get("symbol")
            trades = self._trades
            if symbol:
                trades = [t for t in trades if t.symbol == symbol]

            return {
                "success": True,
                "trades": [t.to_dict() for t in trades],
            }

        except Exception as e:
            logger.error(f"Get trades error: {e}")
            return {"success": False, "error": str(e)}

    async def _close_position(self, payload: Dict) -> Dict[str, Any]:
        """Close a position."""
        try:
            symbol = payload["symbol"]
            side = PositionSide(payload.get("side", "both"))

            positions = await self._adapter.get_positions(symbol)
            for pos in positions:
                if side == PositionSide.BOTH or pos.side == side:
                    # Create closing order
                    order = Order(
                        order_id="",
                        symbol=symbol,
                        side=OrderSide.SELL if pos.side == PositionSide.LONG else OrderSide.BUY,
                        order_type=OrderType.MARKET,
                        quantity=pos.quantity,
                    )
                    order = await self._adapter.create_order(order)
                    self._orders[order.order_id] = order

            return {"success": True, "message": "Position close requested"}

        except Exception as e:
            logger.error(f"Close position error: {e}")
            return {"success": False, "error": str(e)}


# =============================================================================
# Execution Client
# =============================================================================

class ExecutionClient:
    """Client for the Execution Service."""

    def __init__(self, address: str = "ipc:///tmp/dgbit_execution.ipc"):
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
            source="execution_client",
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

    def create_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        order_type: str = "market",
        price: float = None,
    ) -> Dict:
        """Create an order."""
        return self._send("create_order", {
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "order_type": order_type,
            "price": price,
        })

    def cancel_order(self, order_id: str, symbol: str) -> Dict:
        """Cancel an order."""
        return self._send("cancel_order", {
            "order_id": order_id,
            "symbol": symbol,
        })

    def get_order(self, order_id: str) -> Dict:
        """Get order status."""
        return self._send("get_order", {"order_id": order_id})

    def get_orders(self, symbol: str = None, status: str = None) -> Dict:
        """Get all orders."""
        return self._send("get_orders", {"symbol": symbol, "status": status})

    def get_positions(self, symbol: str = None) -> Dict:
        """Get positions."""
        return self._send("get_positions", {"symbol": symbol})

    def get_balance(self) -> Dict:
        """Get account balance."""
        return self._send("get_balance")

    def close_position(self, symbol: str, side: str = "both") -> Dict:
        """Close a position."""
        return self._send("close_position", {"symbol": symbol, "side": side})

    def close(self):
        """Close the client."""
        if self._socket:
            self._socket.close()
            self._socket = None


# =============================================================================
# Run as Service
# =============================================================================

async def run_execution_service():
    """Run the execution service as a standalone process."""
    import argparse

    parser = argparse.ArgumentParser(description="dgbit Execution Service")
    parser.add_argument("--address", default="ipc:///tmp/dgbit_execution.ipc")
    parser.add_argument("--exchange", default="simulated")
    parser.add_argument("--testnet", action="store_true", default=True)
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()

    # Setup logging
    logger.remove()
    logger.add(sys.stdout, level=args.log_level)

    # Create and run service
    service = ExecutionService(
        address=args.address,
        exchange=args.exchange,
        testnet=args.testnet,
    )

    try:
        await service.start()
    except KeyboardInterrupt:
        await service.stop()


if __name__ == "__main__":
    asyncio.run(run_execution_service())
