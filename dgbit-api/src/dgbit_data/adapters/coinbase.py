"""
Coinbase Exchange Adapter

Provides unified interface for Coinbase Advanced Trade API.
Uses ccxt library for comprehensive coverage.

Features:
- Spot trading via Advanced Trade API
- Market data
- USD and stablecoin pairs
- Testnet via sandbox API

Note:
    Coinbase has regulatory restrictions in some jurisdictions.
    Some features may not be available based on your location.

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


class CoinbaseAdapter(DataAdapter, ExecutionAdapter):
    """
    Coinbase exchange adapter using ccxt.

    Supports:
    - Spot trading (Advanced Trade API)
    - Market data

    Example:
        ```python
        config = ExchangeConfig(
            api_key="your_api_key",
            api_secret="your_api_secret",
            passphrase="your_passphrase",
            testnet=True  # Uses sandbox
        )
        adapter = CoinbaseAdapter(config)
        klines = adapter.get_klines("BTC-USD", Interval.H1)
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
    }

    def __init__(
        self,
        config: ExchangeConfig = None,
    ):
        """
        Initialize Coinbase adapter.

        Args:
            config: Exchange configuration
        """
        self.config = config or ExchangeConfig()
        self._client = None

    @property
    def name(self) -> str:
        """Return exchange name."""
        return "coinbase"

    @property
    def exchange(self) -> Exchange:
        """Return exchange enum."""
        return Exchange.COINBASE

    def _get_client(self):
        """
        Get or create ccxt client.

        Returns:
            ccxt coinbase advanced client
        """
        try:
            import ccxt
        except ImportError:
            raise ImportError(
                "ccxt is required for Coinbase adapter. "
                "Install with: pip install ccxt"
            )

        if self._client is not None:
            return self._client

        # Build config
        exchange_config = {
            "enableRateLimit": self.config.rate_limit,
            "timeout": self.config.timeout * 1000,
        }

        if self.config.api_key:
            exchange_config["apiKey"] = self.config.api_key
            exchange_config["secret"] = self.config.api_secret
            if self.config.passphrase:
                exchange_config["password"] = self.config.passphrase

        # Use sandbox for testnet
        if self.config.testnet:
            exchange_config["urls"] = {
                "api": {
                    "public": "https://api-public.sandbox.exchange.coinbase.com",
                    "private": "https://api-public.sandbox.exchange.coinbase.com",
                }
            }

        self._client = ccxt.coinbase(exchange_config)

        return self._client

    def health_check(self) -> bool:
        """Check if exchange connection is healthy."""
        try:
            client = self._get_client()
            client.fetch_time()
            return True
        except Exception as e:
            logger.error(f"Coinbase health check failed: {e}")
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

        Note:
            Coinbase uses granularities (60, 300, 900, 3600, etc.)
            instead of standard intervals.

        Args:
            symbol: Trading pair (e.g., "BTC-USD")
            interval: Time interval
            start_time: Start time in milliseconds
            end_time: End time in milliseconds
            limit: Maximum number of candles

        Returns:
            KlineData object
        """
        client = self._get_client()

        # Convert interval to Coinbase granularity
        granularity_map = {
            Interval.M1: 60,
            Interval.M5: 300,
            Interval.M15: 900,
            Interval.M30: 1800,
            Interval.H1: 3600,
            Interval.H4: 14400,
            Interval.D1: 86400,
        }
        granularity = granularity_map.get(interval, 3600)

        try:
            # Normalize symbol (Coinbase uses BTC-USD format)
            if "/" in symbol:
                symbol = symbol.replace("/", "-")

            # Build params
            params = {
                "granularity": granularity,
                "limit": limit,
            }
            if start_time:
                params["start"] = str(start_time)
            if end_time:
                params["end"] = str(end_time)

            ohlcv = client.fetch_ohlcv(symbol, granularity, params=params)

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
                exchange=Exchange.COINBASE,
                interval=interval,
                data=klines,
                source="coinbase",
            )

        except Exception as e:
            logger.error(f"Failed to fetch klines from Coinbase: {e}")
            return KlineData(
                symbol=symbol,
                exchange=Exchange.COINBASE,
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
                if market.get("spot") and market.get("active", True):
                    # Parse base/quote from symbol (e.g., "BTC-USD")
                    parts = symbol.split("-")
                    base = parts[0] if len(parts) > 1 else ""
                    quote = parts[1] if len(parts) > 1 else ""

                    symbols.append(Symbol(
                        symbol=symbol,
                        base=base,
                        quote=quote,
                        precision=market.get("precision", {}).get("price", 8),
                        quantity_precision=market.get("precision", {}).get("amount", 4),
                        min_quantity=market.get("limits", {}).get("amount", {}).get("min", 0),
                        min_value=market.get("limits", {}).get("cost", {}).get("min", 0),
                        status="trading" if market.get("active") else "suspended",
                        maker_fee=0.004,  # Coinbase Advanced Trade maker fee
                        taker_fee=0.006,  # Coinbase Advanced Trade taker fee
                    ))

            return symbols

        except Exception as e:
            logger.error(f"Failed to fetch symbols from Coinbase: {e}")
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
                if "/" in symbol:
                    symbol = symbol.replace("/", "-")
                ticker = client.fetch_ticker(symbol)
                return [self._parse_ticker(ticker)]
            else:
                all_tickers = client.fetch_tickers()
                return [
                    self._parse_ticker(t)
                    for t in all_tickers.values()
                ]

        except Exception as e:
            logger.error(f"Failed to fetch tickers from Coinbase: {e}")
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
            if "/" in symbol:
                symbol = symbol.replace("/", "-")

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
            logger.error(f"Failed to fetch order book from Coinbase: {e}")
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
            logger.error(f"Failed to fetch balance from Coinbase: {e}")
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

        Note:
            Coinbase Advanced Trade supports market, limit, and stop orders.
            Stop orders are created as limit orders with stop parameters.

        Args:
            symbol: Trading pair
            side: Order side (buy/sell)
            order_type: Order type
            quantity: Order quantity
            price: Limit price
            stop_price: Stop price for stop orders
            time_in_force: Time in force (GTC, IOC, POST_ONLY)

        Returns:
            Order object with order ID
        """
        client = self._get_client()

        try:
            # Normalize symbol
            if "/" in symbol:
                symbol = symbol.replace("/", "-")

            # Build order params
            if order_type == OrderType.MARKET:
                order_config = {
                    "order_configuration": {
                        "market_market_ioc": {
                            "base_size": str(quantity),
                        } if side == Side.BUY else {
                            "quote_size": str(quantity * (price or 1)),
                        }
                    }
                }
            elif order_type == OrderType.LIMIT:
                time_in_force_map = {
                    "GTC": "GOOD_TIL_CANCELLED",
                    "IOC": "IMMEDIATE_OR_CANCEL",
                    "FOK": "FILL_OR_KILL",
                    "PO": "POST_ONLY",
                }
                order_config = {
                    "order_configuration": {
                        "limit_limit_gtc": {
                            "base_size": str(quantity),
                            "limit_price": str(price),
                        }
                    }
                }
            else:
                # Stop orders
                order_config = {
                    "order_configuration": {
                        "stop_limit_stop_limit_gtc": {
                            "base_size": str(quantity),
                            "limit_price": str(price),
                            "stop_price": str(stop_price),
                            "stop_direction": "STOP_UP" if side == Side.BUY else "STOP_DOWN",
                        }
                    }
                }

            # Create order via ccxt wrapper
            result = client.create_order(
                symbol,
                order_type.value,
                side.value,
                quantity,
                price,
            )

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
            logger.error(f"Failed to create order on Coinbase: {e}")
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
        client = self._get_client()

        try:
            if "/" in symbol:
                symbol = symbol.replace("/", "-")

            client.cancel_order(order_id, symbol)
            return True

        except Exception as e:
            logger.error(f"Failed to cancel order on Coinbase: {e}")
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
        client = self._get_client()

        try:
            if "/" in symbol:
                symbol = symbol.replace("/", "-")

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
            logger.error(f"Failed to get order from Coinbase: {e}")
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
        client = self._get_client()

        try:
            params = {}
            if symbol:
                if "/" in symbol:
                    symbol = symbol.replace("/", "-")
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
            logger.error(f"Failed to get open orders from Coinbase: {e}")
            return []

    def get_positions(self, symbol: Optional[str] = None) -> List[Position]:
        """
        Get current positions.

        Note:
            Coinbase Advanced Trade doesn't have traditional positions
            like futures exchanges. This returns spot holdings with
            associated value.

        Args:
            symbol: Optional symbol filter

        Returns:
            List of Position objects
        """
        # Coinbase is spot-only for retail
        # Positions are represented as "long" with current holdings
        balance = self.get_balance()

        if not balance:
            return []

        # Get prices for all balances
        client = self._get_client()
        positions = []

        for asset, amount in balance.items():
            if amount <= 0:
                continue

            if asset in ["USD", "USDC", "USDT"]:
                continue  # Skip quote currencies

            try:
                # Get price for this asset
                ticker = client.fetch_ticker(f"{asset}-USD")
                price = ticker.get("last", 0)

                if price > 0:
                    positions.append(Position(
                        symbol=f"{asset}-USD",
                        side=PositionSide.LONG,
                        quantity=amount,
                        entry_price=price,  # Using current price as proxy
                        mark_price=price,
                    ))
            except Exception:
                continue

        return positions

    def close_position(
        self,
        symbol: str,
        side: PositionSide,
        quantity: Optional[float] = None,
    ) -> List[Trade]:
        """
        Close a position.

        Note:
            For spot, this means selling the asset.

        Args:
            symbol: Trading pair
            side: Position side to close
            quantity: Quantity to close (None = all)

        Returns:
            List of executed trades
        """
        try:
            if "/" in symbol:
                symbol = symbol.replace("/", "-")

            # Get current balance
            base = symbol.split("-")[0] if "-" in symbol else ""
            balance = self.get_balance()
            available = balance.get(base, 0)

            if quantity is None:
                quantity = available

            if quantity <= 0:
                return []

            # Create market sell order
            trade = self.create_order(
                symbol=symbol,
                side=Side.SELL,
                order_type=OrderType.MARKET,
                quantity=quantity,
            )

            return [
                Trade(
                    trade_id=f"close_{trade.order_id}",
                    order_id=trade.order_id,
                    symbol=symbol,
                    side=Side.SELL,
                    quantity=quantity,
                    price=trade.avg_price or 0,
                    fee=quantity * (trade.avg_price or 0) * 0.006,  # Coinbase taker fee
                )
            ]

        except Exception as e:
            logger.error(f"Failed to close position on Coinbase: {e}")
            return []

    def set_leverage(self, symbol: str, leverage: int) -> bool:
        """
        Set position leverage.

        Note:
            Coinbase Advanced Trade doesn't support leverage
            for spot trading.

        Args:
            symbol: Trading pair
            leverage: Leverage multiplier

        Returns:
            Always False for spot-only exchange
        """
        logger.warning("Coinbase Advanced Trade doesn't support leverage for spot")
        return False


# Aliases for backwards compatibility
CoinbaseDataAdapter = CoinbaseAdapter
CoinbaseExecutionAdapter = CoinbaseAdapter
