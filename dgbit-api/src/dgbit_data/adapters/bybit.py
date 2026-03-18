"""
Bybit Exchange Adapter

Provides unified interface for Bybit trading.
Uses pybit library for comprehensive coverage.

Features:
- Spot trading
- USDT-M futures
- Coin-M futures
- Testnet support

Author: dgbit
Version: 1.0.0
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from loguru import logger

from .base import (
    DataAdapter,
    ExecutionAdapter,
    ExchangeConfig,
    Exchange,
    Kline,
    KlineData,
    Interval,
    Order,
    OrderBook,
    OrderType,
    OrderStatus,
    Position,
    PositionSide,
    Side,
    Symbol,
    Ticker,
    Trade,
)


class BybitAdapter(DataAdapter, ExecutionAdapter):
    """
    Bybit exchange adapter using pybit.

    Supports:
    - Spot trading
    - USDT-M perpetual futures
    - Inverse perpetual futures
    - Testnet

    Example:
        ```python
        config = ExchangeConfig(
            api_key="your_api_key",
            api_secret="your_api_secret",
            testnet=True
        )
        adapter = BybitAdapter(config)
        klines = adapter.get_klines("BTCUSDT", Interval.H1)
        ```
    """

    # Mapping of interval strings to Bybit values
    INTERVAL_MAP = {
        Interval.M1: "1",
        Interval.M5: "5",
        Interval.M15: "15",
        Interval.M30: "30",
        Interval.H1: "60",
        Interval.H4: "240",
        Interval.D1: "D",
    }

    def __init__(
        self,
        config: ExchangeConfig = None,
        category: str = "spot",  # spot, linear, inverse
    ):
        """
        Initialize Bybit adapter.

        Args:
            config: Exchange configuration
            category: Market category (spot, linear, inverse)
        """
        self.config = config or ExchangeConfig()
        self.category = category
        self._session = None

    @property
    def name(self) -> str:
        """Return exchange name."""
        return "bybit"

    @property
    def exchange(self) -> Exchange:
        """Return exchange enum."""
        return Exchange.BYBIT

    def _get_session(self):
        """
        Get or create pybit session.

        Returns:
            pybit HTTP session
        """
        try:
            from pybit.unified_trading import HTTP
        except ImportError:
            raise ImportError(
                "pybit is required for Bybit adapter. "
                "Install with: pip install pybit"
            )

        if self._session is not None:
            return self._session

        self._session = HTTP(
            testnet=self.config.testnet,
            api_key=self.config.api_key,
            api_secret=self.config.api_secret,
        )

        return self._session

    def health_check(self) -> bool:
        """Check if exchange connection is healthy."""
        try:
            session = self._get_session()
            # Try to fetch server time
            session.get_server_time()
            return True
        except Exception as e:
            logger.error(f"Bybit health check failed: {e}")
            return False

    # ==================== Data Methods ====================

    def get_klines(
        self,
        symbol: str,
        interval: Interval,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        limit: int = 100,
    ) -> KlineData:
        """
        Fetch kline/candlestick data.

        Args:
            symbol: Trading pair (e.g., "BTCUSDT")
            interval: Time interval
            start_time: Start time in milliseconds
            end_time: End time in milliseconds
            limit: Maximum number of candles (max 1000 for Bybit)

        Returns:
            KlineData object
        """
        session = self._get_session()
        bybit_interval = self.INTERVAL_MAP.get(interval, "1")

        try:
            params = {
                "category": self.category,
                "symbol": symbol.upper(),
                "interval": bybit_interval,
                "limit": min(limit, 1000),
            }

            if start_time:
                params["startTime"] = start_time
            if end_time:
                params["endTime"] = end_time

            response = session.get_kline(**params)

            if "result" not in response or "list" not in response["result"]:
                return KlineData(
                    symbol=symbol,
                    exchange=Exchange.BYBIT,
                    interval=interval,
                    data=[],
                )

            raw_data = response["result"]["list"]

            # Parse klines
            klines = []
            for k in raw_data:
                klines.append(Kline(
                    timestamp=datetime.fromtimestamp(int(k[0]) / 1000),
                    open=float(k[1]),
                    high=float(k[2]),
                    low=float(k[3]),
                    close=float(k[4]),
                    volume=float(k[5]),
                    turnover=float(k[6]) if len(k) > 6 else 0.0,
                ))

            return KlineData(
                symbol=symbol,
                exchange=Exchange.BYBIT,
                interval=interval,
                data=klines,
                source="bybit",
            )

        except Exception as e:
            logger.error(f"Failed to fetch klines from Bybit: {e}")
            return KlineData(
                symbol=symbol,
                exchange=Exchange.BYBIT,
                interval=interval,
                data=[],
            )

    def get_symbols(self) -> List[Symbol]:
        """
        Fetch available trading pairs.

        Returns:
            List of Symbol objects
        """
        session = self._get_session()

        try:
            response = session.get_symbols(category=self.category)

            symbols = []
            for s in response.get("result", {}).get("list", []):
                # Parse base/quote from symbol
                symbol = s.get("symbol", "")
                quote = s.get("quoteCoin", "")

                # Determine base from symbol
                if symbol.endswith(quote):
                    base = symbol[:-len(quote)]
                else:
                    base = symbol

                # Get filter values
                price_filter = s.get("priceFilter", {})
                lot_size = s.get("lotSizeFilter", {})

                symbols.append(Symbol(
                    symbol=symbol,
                    base=base,
                    quote=quote,
                    precision=int(price_filter.get("tickSize", "1e-8").replace(".", "").find("1")),
                    quantity_precision=int(lot_size.get("qtyStep", "1").replace(".", "").find("1")),
                    min_quantity=float(lot_size.get("minOrderQty", "0")),
                    min_value=float(lot_size.get("minOrderAmt", "0")),
                    status="trading" if s.get("status", "") == "Trading" else "suspended",
                    maker_fee=0.001,  # Bybit maker fee
                    taker_fee=0.001,  # Bybit taker fee
                ))

            return symbols

        except Exception as e:
            logger.error(f"Failed to fetch symbols from Bybit: {e}")
            return []

    def get_tickers(self, symbol: Optional[str] = None) -> List[Ticker]:
        """
        Fetch market tickers.

        Args:
            symbol: Optional symbol filter

        Returns:
            List of Ticker objects
        """
        session = self._get_session()

        try:
            params = {"category": self.category}
            if symbol:
                params["symbol"] = symbol.upper()

            response = session.get_tickers(**params)

            tickers = []
            for t in response.get("result", {}).get("list", []):
                tickers.append(Ticker(
                    symbol=t.get("symbol", ""),
                    price=float(t.get("lastPrice", 0)),
                    price_24h=float(t.get("price24hPcnt", 0)) * 100,
                    volume_24h=float(t.get("volume24h", 0)),
                    change_24h=float(t.get("price24hPcnt", 0)) * 100,
                    high_24h=float(t.get("highPrice24h", 0)),
                    low_24h=float(t.get("lowPrice24h", 0)),
                    timestamp=datetime.fromtimestamp(
                        int(t.get("time", 0)) / 1000
                    ) if t.get("time") else datetime.utcnow(),
                ))

            return tickers

        except Exception as e:
            logger.error(f"Failed to fetch tickers from Bybit: {e}")
            return []

    def _parse_ticker(self, ticker: Dict) -> Ticker:
        """Parse Bybit ticker response."""
        return Ticker(
            symbol=ticker.get("symbol", ""),
            price=float(ticker.get("lastPrice", 0)),
            price_24h=float(ticker.get("price24h", 0)),
            volume_24h=float(ticker.get("volume24h", 0)),
            change_24h=float(ticker.get("price24hPcnt", 0)) * 100,
            high_24h=float(ticker.get("highPrice24h", 0)),
            low_24h=float(ticker.get("lowPrice24h", 0)),
            timestamp=datetime.fromtimestamp(
                int(ticker.get("time", 0)) / 1000
            ) if ticker.get("time") else datetime.utcnow(),
        )

    def get_order_book(
        self,
        symbol: str,
        depth: int = 100,
    ) -> OrderBook:
        """
        Fetch order book.

        Args:
            symbol: Trading pair
            depth: Order book depth

        Returns:
            OrderBook object
        """
        session = self._get_session()

        try:
            response = session.get_orderbook(
                category=self.category,
                symbol=symbol.upper(),
                limit=depth,
            )

            orderbook = response.get("result", {})
            return OrderBook(
                symbol=symbol.upper(),
                bids=[[float(b[0]), float(b[1])] for b in orderbook.get("b", [])],
                asks=[[float(a[0]), float(a[1])] for a in orderbook.get("a", [])],
                timestamp=datetime.fromtimestamp(
                    int(orderbook.get("ts", 0)) / 1000
                ) if orderbook.get("ts") else datetime.utcnow(),
            )

        except Exception as e:
            logger.error(f"Failed to fetch order book from Bybit: {e}")
            return OrderBook(symbol=symbol, bids=[], asks=[])

    def get_balance(self) -> Dict[str, float]:
        """
        Fetch account balance.

        Returns:
            Dictionary of asset -> available balance
        """
        session = self._get_session()

        try:
            response = session.get_wallet_balance(accountType="UNIFIED")

            balance = {}
            for coin in response.get("result", {}).get("list", [{}])[0].get("coin", []):
                currency = coin.get("coin", "")
                available = float(coin.get("available", 0))
                if available > 0:
                    balance[currency] = available

            return balance

        except Exception as e:
            logger.error(f"Failed to fetch balance from Bybit: {e}")
            return {}

    # ==================== Execution Methods ====================

    def create_order(
        self,
        symbol: str,
        side: Side,
        order_type: OrderType,
        quantity: float,
        price: Optional[float] = None,
        stop_price: Optional[float] = None,
        time_in_force: str = "GTC",
    ) -> Order:
        """
        Create a new order.

        Args:
            symbol: Trading pair
            side: Order side (buy/sell)
            order_type: Order type
            quantity: Order quantity
            price: Limit price
            stop_price: Stop price for stop orders
            time_in_force: Time in force (GTC, IOC, FOK)

        Returns:
            Order object with order ID
        """
        session = self._get_session()

        try:
            # Build order params
            order_type_map = {
                OrderType.MARKET: "Market",
                OrderType.LIMIT: "Limit",
                OrderType.STOP: "Market",
                OrderType.STOP_LIMIT: "Limit",
            }

            params = {
                "category": self.category,
                "symbol": symbol.upper(),
                "side": "Buy" if side == Side.BUY else "Sell",
                "orderType": order_type_map.get(order_type, "Limit"),
                "qty": str(quantity),
                "timeInForce": time_in_force,
            }

            if order_type in [OrderType.LIMIT, OrderType.STOP_LIMIT]:
                params["price"] = str(price)

            if order_type in [OrderType.STOP, OrderType.STOP_LIMIT]:
                params["triggerPrice"] = str(stop_price)
                params["orderType"] = "Limit"  # Stop orders are submitted as limit

            response = session.place_order(**params)

            if response.get("retCode") == 0:
                order_id = response["result"]["orderId"]
                return Order(
                    order_id=order_id,
                    symbol=symbol,
                    side=side,
                    order_type=order_type,
                    quantity=quantity,
                    price=price,
                    status=OrderStatus.OPEN,
                )
            else:
                logger.error(f"Bybit order failed: {response.get('retMsg')}")
                return Order(
                    order_id="",
                    symbol=symbol,
                    side=side,
                    order_type=order_type,
                    quantity=quantity,
                    price=price,
                    status=OrderStatus.REJECTED,
                )

        except Exception as e:
            logger.error(f"Failed to create order on Bybit: {e}")
            return Order(
                order_id="",
                symbol=symbol,
                side=side,
                order_type=order_type,
                quantity=quantity,
                price=price,
                status=OrderStatus.REJECTED,
            )

    def cancel_order(
        self,
        order_id: str,
        symbol: str,
    ) -> bool:
        """
        Cancel an order.

        Args:
            order_id: Order ID
            symbol: Trading pair

        Returns:
            True if successful
        """
        session = self._get_session()

        try:
            response = session.cancel_order(
                category=self.category,
                symbol=symbol.upper(),
                orderId=order_id,
            )
            return response.get("retCode", -1) == 0

        except Exception as e:
            logger.error(f"Failed to cancel order on Bybit: {e}")
            return False

    def get_order(
        self,
        order_id: str,
        symbol: str,
    ) -> Optional[Order]:
        """
        Get order status.

        Args:
            order_id: Order ID
            symbol: Trading pair

        Returns:
            Order object or None
        """
        session = self._get_session()

        try:
            response = session.get_order(
                category=self.category,
                symbol=symbol.upper(),
                orderId=order_id,
            )

            if response.get("retCode") != 0:
                return None

            order_data = response["result"]["list"][0]

            # Map status
            status_map = {
                "Created": OrderStatus.PENDING,
                "New": OrderStatus.OPEN,
                "PartiallyFilled": OrderStatus.OPEN,
                "Filled": OrderStatus.FILLED,
                "Cancelled": OrderStatus.CANCELLED,
                "Rejected": OrderStatus.REJECTED,
            }

            side_map = {"Buy": Side.BUY, "Sell": Side.SELL}
            type_map = {"Market": OrderType.MARKET, "Limit": OrderType.LIMIT}

            return Order(
                order_id=order_data.get("orderId", ""),
                symbol=order_data.get("symbol", ""),
                side=side_map.get(order_data.get("side", "Buy"), Side.BUY),
                order_type=type_map.get(order_data.get("orderType", "Limit"), OrderType.LIMIT),
                quantity=float(order_data.get("qty", 0)),
                price=float(order_data.get("price", 0)) if order_data.get("price") else None,
                filled_qty=float(order_data.get("cumExecQty", 0)),
                avg_price=float(order_data.get("avgPrice", 0)) if order_data.get("avgPrice") else None,
                status=status_map.get(order_data.get("orderStatus", ""), OrderStatus.PENDING),
                created_at=datetime.fromtimestamp(
                    int(order_data.get("createdTime", 0)) / 1000
                ) if order_data.get("createdTime") else datetime.utcnow(),
            )

        except Exception as e:
            logger.error(f"Failed to get order from Bybit: {e}")
            return None

    def get_open_orders(
        self,
        symbol: Optional[str] = None,
    ) -> List[Order]:
        """
        Get all open orders.

        Args:
            symbol: Optional symbol filter

        Returns:
            List of open Order objects
        """
        session = self._get_session()

        try:
            params = {
                "category": self.category,
                "openOnly": 0,  # Open orders only
            }
            if symbol:
                params["symbol"] = symbol.upper()

            response = session.get_orders(**params)

            if response.get("retCode") != 0:
                return []

            status_map = {
                "Created": OrderStatus.PENDING,
                "New": OrderStatus.OPEN,
            }

            side_map = {"Buy": Side.BUY, "Sell": Side.SELL}
            type_map = {"Market": OrderType.MARKET, "Limit": OrderType.LIMIT}

            return [
                Order(
                    order_id=o.get("orderId", ""),
                    symbol=o.get("symbol", ""),
                    side=side_map.get(o.get("side", "Buy"), Side.BUY),
                    order_type=type_map.get(o.get("orderType", "Limit"), OrderType.LIMIT),
                    quantity=float(o.get("qty", 0)),
                    price=float(o.get("price", 0)) if o.get("price") else None,
                    status=status_map.get(o.get("orderStatus", ""), OrderStatus.PENDING),
                    created_at=datetime.fromtimestamp(
                        int(o.get("createdTime", 0)) / 1000
                    ) if o.get("createdTime") else datetime.utcnow(),
                )
                for o in response["result"]["list"]
            ]

        except Exception as e:
            logger.error(f"Failed to get open orders from Bybit: {e}")
            return []

    def get_positions(self, symbol: Optional[str] = None) -> List[Position]:
        """
        Get current positions.

        Args:
            symbol: Optional symbol filter

        Returns:
            List of Position objects
        """
        session = self._get_session()

        try:
            params = {"category": self.category}
            if symbol:
                params["symbol"] = symbol.upper()

            response = session.get_positions(**params)

            if response.get("retCode") != 0:
                return []

            positions = []
            for pos in response["result"]["list"]:
                size = float(pos.get("size", 0))
                if size == 0:
                    continue

                side = PositionSide.LONG if pos.get("side", "") == "Buy" else PositionSide.SHORT

                positions.append(Position(
                    symbol=pos.get("symbol", ""),
                    side=side,
                    quantity=size,
                    entry_price=float(pos.get("avgPrice", 0)),
                    mark_price=float(pos.get("markPrice", 0)),
                    unrealized_pnl=float(pos.get("unrealisedPnl", 0)),
                    leverage=float(pos.get("leverage", 1)),
                ))

            return positions

        except Exception as e:
            logger.error(f"Failed to get positions from Bybit: {e}")
            return []

    def close_position(
        self,
        symbol: str,
        side: PositionSide,
        quantity: Optional[float] = None,
    ) -> List[Trade]:
        """
        Close a position.

        Args:
            symbol: Trading pair
            side: Position side to close
            quantity: Quantity to close (None = all)

        Returns:
            List of executed trades
        """
        session = self._get_session()

        try:
            # Get position info
            response = session.get_positions(
                category=self.category,
                symbol=symbol.upper(),
            )

            if response.get("retCode") != 0:
                return []

            pos_data = response["result"]["list"][0]
            size = float(pos_data.get("size", 0))

            if size == 0:
                return []

            if quantity is None:
                quantity = abs(size)

            if quantity <= 0:
                return []

            # Create market order to close
            close_side = Side.SELL if side == PositionSide.LONG else Side.BUY
            trade = self.create_order(
                symbol=symbol,
                side=close_side,
                order_type=OrderType.MARKET,
                quantity=quantity,
            )

            return [
                Trade(
                    trade_id=f"close_{trade.order_id}",
                    order_id=trade.order_id,
                    symbol=symbol,
                    side=close_side,
                    quantity=quantity,
                    price=trade.avg_price or 0,
                    fee=quantity * (trade.avg_price or 0) * 0.001,
                )
            ]

        except Exception as e:
            logger.error(f"Failed to close position on Bybit: {e}")
            return []

    def set_leverage(self, symbol: str, leverage: int) -> bool:
        """
        Set position leverage.

        Args:
            symbol: Trading pair
            leverage: Leverage multiplier

        Returns:
            True if successful
        """
        session = self._get_session()

        try:
            response = session.set_leverage(
                category=self.category,
                symbol=symbol.upper(),
                buyLeverage=str(leverage),
                sellLeverage=str(leverage),
            )
            return response.get("retCode", -1) == 0

        except Exception as e:
            logger.error(f"Failed to set leverage on Bybit: {e}")
            return False


# Aliases for backwards compatibility
BybitDataAdapter = BybitAdapter
BybitExecutionAdapter = BybitAdapter
