"""
Binance Exchange Adapter

Provides unified interface for Binance Spot and Futures trading.
Uses ccxt library for comprehensive exchange coverage.

Features:
- Spot and futures market data
- Spot and futures trading
- Cross-margin and isolated margin support
- Testnet support

Author: dgbit
Version: 1.0.0
"""

import asyncio
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


class BinanceAdapter(DataAdapter, ExecutionAdapter):
    """
    Binance exchange adapter using ccxt.

    Supports:
    - Spot trading
    - USDT-M futures
    - Coin-M futures

    Example:
        ```python
        config = ExchangeConfig(
            api_key="your_api_key",
            api_secret="your_api_secret",
            testnet=True
        )
        adapter = BinanceAdapter(config)
        klines = adapter.get_klines("BTCUSDT", Interval.H1)
        ```
    """

    # Mapping of interval strings to ccxt values
    INTERVAL_MAP = {
        Interval.M1: "1m",
        Interval.M5: "5m",
        Interval.M15: "15m",
        Interval.M30: "30m",
        Interval.H1: "1h",
        Interval.H4: "4h",
        Interval.D1: "1d",
        Interval.W1: "1w",
        Interval.MN1: "1M",
    }

    def __init__(
        self,
        config: ExchangeConfig = None,
        futures: bool = False,
    ):
        """
        Initialize Binance adapter.

        Args:
            config: Exchange configuration
            futures: Use futures market (default: False for spot)
        """
        self.config = config or ExchangeConfig()
        self.futures = futures
        self._client = None
        self._spot_client = None
        self._futures_client = None

    @property
    def name(self) -> str:
        """Return exchange name."""
        return "binance"

    @property
    def exchange(self) -> Exchange:
        """Return exchange enum."""
        return Exchange.BINANCE

    def _get_client(self, spot: bool = True):
        """
        Get or create ccxt client.

        Args:
            spot: Get spot client (False for futures)

        Returns:
            ccxt exchange client
        """
        try:
            import ccxt
        except ImportError:
            raise ImportError(
                "ccxt is required for Binance adapter. "
                "Install with: pip install ccxt"
            )

        client_attr = "_spot_client" if spot else "_futures_client"
        client = getattr(self, client_attr)

        if client is None:
            # Build config
            exchange_config = {
                "enableRateLimit": self.config.rate_limit,
                "timeout": self.config.timeout * 1000,
            }

            if self.config.api_key:
                exchange_config["apiKey"] = self.config.api_key
                exchange_config["secret"] = self.config.api_secret

            # Use testnet if configured
            if self.config.testnet:
                if spot:
                    exchange_config["options"] = {"defaultType": "spot"}
                else:
                    exchange_config["urls"] = {
                        "api": {
                            "public": "https://testnet.binance.vision/api/v3",
                            "private": "https://testnet.binance.vision/api/v3",
                        }
                    }

            # Create client
            if spot:
                self._spot_client = ccxt.binance(exchange_config)
                client = self._spot_client
            else:
                self._futures_client = ccxt.binance(
                    {**exchange_config, "options": {"defaultType": "future"}}
                )
                client = self._futures_client

        return client

    def health_check(self) -> bool:
        """Check if exchange connection is healthy."""
        try:
            client = self._get_client()
            client.fetch_time()
            return True
        except Exception as e:
            logger.error(f"Binance health check failed: {e}")
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
            limit: Maximum number of candles

        Returns:
            KlineData object
        """
        client = self._get_client(spot=not self.futures)
        ccxt_interval = self.INTERVAL_MAP.get(interval, "1h")

        params = {"limit": limit}
        if start_time:
            params["startTime"] = start_time
        if end_time:
            params["endTime"] = end_time

        try:
            # Normalize symbol format
            if "/" not in symbol:
                # Convert BTCUSDT -> BTC/USDT
                if symbol.endswith("USDT"):
                    norm_symbol = f"{symbol[:-4]}/USDT"
                elif symbol.endswith("USD"):
                    norm_symbol = f"{symbol[:-3]}/USD"
                else:
                    norm_symbol = symbol
            else:
                norm_symbol = symbol

            ohlcv = client.fetch_ohlcv(
                symbol=norm_symbol,
                timeframe=ccxt_interval,
                params=params,
            )

            klines = [
                Kline(
                    timestamp=datetime.fromtimestamp(k[0] / 1000),
                    open=k[1],
                    high=k[2],
                    low=k[3],
                    close=k[4],
                    volume=k[5],
                )
                for k in ohlcv
            ]

            return KlineData(
                symbol=symbol,
                exchange=Exchange.BINANCE,
                interval=interval,
                data=klines,
                source="binance",
            )

        except Exception as e:
            logger.error(f"Failed to fetch klines from Binance: {e}")
            return KlineData(
                symbol=symbol,
                exchange=Exchange.BINANCE,
                interval=interval,
                data=[],
            )

    def get_symbols(self) -> List[Symbol]:
        """
        Fetch available trading pairs.

        Returns:
            List of Symbol objects
        """
        client = self._get_client()

        try:
            markets = client.load_markets()

            symbols = []
            for symbol, market in markets.items():
                if market.get("spot") and not self.futures:
                    # Skip suspended symbols
                    if market.get("active", True):
                        symbols.append(Symbol(
                            symbol=symbol,
                            base=market["base"],
                            quote=market["quote"],
                            precision=market.get("precision", {}).get("price", 8),
                            quantity_precision=market.get("precision", {}).get("amount", 4),
                            min_quantity=market.get("limits", {}).get("amount", {}).get("min", 0),
                            min_value=market.get("limits", {}).get("cost", {}).get("min", 0),
                            status="trading" if market.get("active") else "suspended",
                            maker_fee=market.get("maker", 0.001),
                            taker_fee=market.get("taker", 0.001),
                        ))
                elif market.get("future") and self.futures:
                    # Futures symbols
                    symbols.append(Symbol(
                        symbol=symbol,
                        base=market["base"],
                        quote=market["quote"],
                        precision=8,
                        quantity_precision=0,
                        status="trading" if market.get("active") else "suspended",
                    ))

            return symbols

        except Exception as e:
            logger.error(f"Failed to fetch symbols from Binance: {e}")
            return []

    def get_tickers(self, symbol: Optional[str] = None) -> List[Ticker]:
        """
        Fetch market tickers.

        Args:
            symbol: Optional symbol filter

        Returns:
            List of Ticker objects
        """
        client = self._get_client()

        try:
            if symbol:
                if "/" not in symbol:
                    if symbol.endswith("USDT"):
                        symbol = f"{symbol[:-4]}/USDT"
                tickers = client.fetch_ticker(symbol)
                return [self._parse_ticker(tickers)]
            else:
                all_tickers = client.fetch_tickers()
                return [
                    self._parse_ticker(t)
                    for t in all_tickers.values()
                ]

        except Exception as e:
            logger.error(f"Failed to fetch tickers from Binance: {e}")
            return []

    def _parse_ticker(self, ticker: Dict) -> Ticker:
        """Parse ccxt ticker to our format."""
        return Ticker(
            symbol=ticker.get("symbol", ""),
            price=ticker.get("last", 0),
            price_24h=ticker.get("open", 0),
            volume_24h=ticker.get("baseVolume", 0),
            change_24h=ticker.get("percentage", 0),
            high_24h=ticker.get("high", 0),
            low_24h=ticker.get("low", 0),
            timestamp=datetime.fromtimestamp(
                ticker.get("timestamp", 0) / 1000
            ) if ticker.get("timestamp") else datetime.utcnow(),
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
        client = self._get_client()

        try:
            if "/" not in symbol:
                if symbol.endswith("USDT"):
                    symbol = f"{symbol[:-4]}/USDT"

            orderbook = client.fetch_order_book(symbol, limit=depth)
            return OrderBook(
                symbol=orderbook.get("symbol", ""),
                bids=orderbook.get("bids", []),
                asks=orderbook.get("asks", []),
                timestamp=datetime.fromtimestamp(
                    orderbook.get("timestamp", 0) / 1000
                ) if orderbook.get("timestamp") else datetime.utcnow(),
            )

        except Exception as e:
            logger.error(f"Failed to fetch order book from Binance: {e}")
            return OrderBook(symbol=symbol, bids=[], asks=[])

    def get_balance(self) -> Dict[str, float]:
        """
        Fetch account balance.

        Returns:
            Dictionary of asset -> available balance
        """
        client = self._get_client()

        try:
            balance = client.fetch_balance()
            return {
                asset: info.get("free", 0)
                for asset, info in balance.get("total", {}).items()
                if info.get("total", 0) > 0
            }

        except Exception as e:
            logger.error(f"Failed to fetch balance from Binance: {e}")
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
        client = self._get_client(spot=not self.futures)

        try:
            # Normalize symbol
            if "/" not in symbol:
                if symbol.endswith("USDT"):
                    symbol = f"{symbol[:-4]}/USDT"

            # Build order params
            params = {
                "type": order_type.value,
                "side": side.value,
                "amount": str(quantity),
            }

            if order_type == OrderType.LIMIT:
                params["price"] = str(price)
                params["timeInForce"] = time_in_force
            elif order_type == OrderType.STOP:
                params["stopPrice"] = str(stop_price)
            elif order_type == OrderType.STOP_LIMIT:
                params["price"] = str(price)
                params["stopPrice"] = str(stop_price)
                params["timeInForce"] = time_in_force

            # Create order
            result = client.create_order(symbol, "limit", side.value, quantity, price, params)

            return Order(
                order_id=str(result.get("id", "")),
                symbol=symbol,
                side=side,
                order_type=order_type,
                quantity=quantity,
                price=price,
                status=OrderStatus.OPEN,
            )

        except Exception as e:
            logger.error(f"Failed to create order on Binance: {e}")
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
        client = self._get_client(spot=not self.futures)

        try:
            if "/" not in symbol:
                if symbol.endswith("USDT"):
                    symbol = f"{symbol[:-4]}/USDT"

            client.cancel_order(order_id, symbol)
            return True

        except Exception as e:
            logger.error(f"Failed to cancel order on Binance: {e}")
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
        client = self._get_client(spot=not self.futures)

        try:
            if "/" not in symbol:
                if symbol.endswith("USDT"):
                    symbol = f"{symbol[:-4]}/USDT"

            order = client.fetch_order(order_id, symbol)

            # Map status
            status_map = {
                "open": OrderStatus.OPEN,
                "closed": OrderStatus.FILLED,
                "canceled": OrderStatus.CANCELLED,
            }

            return Order(
                order_id=str(order.get("id", "")),
                symbol=order.get("symbol", ""),
                side=Side(order.get("side", "buy")),
                order_type=OrderType(order.get("type", "limit")),
                quantity=float(order.get("amount", 0)),
                price=float(order.get("price", 0)) if order.get("price") else None,
                filled_qty=float(order.get("filled", 0)),
                avg_price=float(order.get("average", 0)) if order.get("average") else None,
                status=status_map.get(order.get("status", ""), OrderStatus.PENDING),
                created_at=datetime.fromtimestamp(
                    order.get("timestamp", 0) / 1000
                ) if order.get("timestamp") else datetime.utcnow(),
            )

        except Exception as e:
            logger.error(f"Failed to get order from Binance: {e}")
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
        client = self._get_client(spot=not self.futures)

        try:
            params = {}
            if symbol:
                if "/" not in symbol:
                    if symbol.endswith("USDT"):
                        symbol = f"{symbol[:-4]}/USDT"
                params["symbol"] = symbol

            orders = client.fetch_open_orders(params=params)

            status_map = {
                "open": OrderStatus.OPEN,
            }

            return [
                Order(
                    order_id=str(o.get("id", "")),
                    symbol=o.get("symbol", ""),
                    side=Side(o.get("side", "buy")),
                    order_type=OrderType(o.get("type", "limit")),
                    quantity=float(o.get("amount", 0)),
                    price=float(o.get("price", 0)) if o.get("price") else None,
                    status=status_map.get(o.get("status", ""), OrderStatus.PENDING),
                    created_at=datetime.fromtimestamp(
                        o.get("timestamp", 0) / 1000
                    ) if o.get("timestamp") else datetime.utcnow(),
                )
                for o in orders
            ]

        except Exception as e:
            logger.error(f"Failed to get open orders from Binance: {e}")
            return []

    def get_positions(self, symbol: Optional[str] = None) -> List[Position]:
        """
        Get current positions.

        Args:
            symbol: Optional symbol filter

        Returns:
            List of Position objects
        """
        if self.futures:
            client = self._get_client(spot=False)
        else:
            # No positions in spot mode
            return []

        try:
            positions = client.fetch_positions()

            result = []
            for pos in positions:
                if symbol and pos.get("symbol") != symbol:
                    continue

                info = pos.get("info", {})
                size = float(info.get("positionAmt", 0))
                if size == 0:
                    continue

                side = PositionSide.LONG if size > 0 else PositionSide.SHORT

                result.append(Position(
                    symbol=pos.get("symbol", ""),
                    side=side,
                    quantity=abs(size),
                    entry_price=float(pos.get("entryPrice", 0)),
                    mark_price=float(pos.get("markPrice", 0)),
                    unrealized_pnl=float(pos.get("unrealizedPnl", 0)),
                    leverage=float(info.get("leverage", 1)),
                ))

            return result

        except Exception as e:
            logger.error(f"Failed to get positions from Binance: {e}")
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
        client = self._get_client(spot=False)

        try:
            # Get current position
            positions = client.fetch_positions()
            pos = next(
                (p for p in positions if p.get("symbol") == symbol),
                None
            )

            if not pos:
                return []

            info = pos.get("info", {})
            size = float(info.get("positionAmt", 0))

            if quantity is None:
                quantity = abs(size)

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
            logger.error(f"Failed to close position on Binance: {e}")
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
        if not self.futures:
            logger.warning("Cannot set leverage in spot mode")
            return False

        client = self._get_client(spot=False)

        try:
            client.set_leverage(leverage, symbol)
            return True

        except Exception as e:
            logger.error(f"Failed to set leverage on Binance: {e}")
            return False


# Alias for backwards compatibility
BinanceDataAdapter = BinanceAdapter
BinanceExecutionAdapter = BinanceAdapter
