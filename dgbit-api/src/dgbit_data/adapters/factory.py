"""
Adapter Factory

Central factory for creating exchange adapters.
Automatically registers all available adapters.

Author: dgbit
Version: 1.0.0
"""

from typing import Dict, List, Optional, Type, Union
from loguru import logger

from .base import (
    DataAdapter,
    ExecutionAdapter,
    ExchangeConfig,
    Exchange,
)
from .bybit import BybitAdapter
from .binance import BinanceAdapter
from .coinbase import CoinbaseAdapter
from .okx import OKXAdapter


class AdapterFactory:
    """
    Factory for creating exchange adapters.

    Provides a unified interface for creating data and execution adapters
    for all supported exchanges.

    Usage:
        ```python
        from dgbit_data.adapters import AdapterFactory, Exchange

        # Create a data adapter
        adapter = AdapterFactory.create_data_adapter(
            exchange=Exchange.BINANCE,
            config=ExchangeConfig(api_key="...", api_secret="...")
        )

        # Create an execution adapter
        executor = AdapterFactory.create_execution_adapter(
            exchange=Exchange.BINANCE,
            config=ExchangeConfig(api_key="...", api_secret="...")
        )

        # Get supported exchanges
        exchanges = AdapterFactory.supported_exchanges()
        ```

    Attributes:
        _data_adapters: Registry of data adapters
        _execution_adapters: Registry of execution adapters
    """

    # Registry of data adapters (by exchange)
    _data_adapters: Dict[Exchange, Type[DataAdapter]] = {}

    # Registry of execution adapters (by exchange)
    _execution_adapters: Dict[Exchange, Type[ExecutionAdapter]] = {}

    @classmethod
    def _init_factory(cls):
        """Initialize factory with all available adapters."""
        # Auto-register all adapters
        if not cls._data_adapters:
            cls.register_data_adapter(Exchange.BYBIT, BybitAdapter)
            cls.register_data_adapter(Exchange.BINANCE, BinanceAdapter)
            cls.register_data_adapter(Exchange.COINBASE, CoinbaseAdapter)
            cls.register_data_adapter(Exchange.OKX, OKXAdapter)

            cls.register_execution_adapter(Exchange.BYBIT, BybitAdapter)
            cls.register_execution_adapter(Exchange.BINANCE, BinanceAdapter)
            cls.register_execution_adapter(Exchange.COINBASE, CoinbaseAdapter)
            cls.register_execution_adapter(Exchange.OKX, OKXAdapter)

    @classmethod
    def register_data_adapter(
        cls,
        exchange: Exchange,
        adapter_class: Type[DataAdapter],
    ):
        """
        Register a data adapter for an exchange.

        Args:
            exchange: Exchange enum value
            adapter_class: Adapter class (must implement DataAdapter)
        """
        cls._data_adapters[exchange] = adapter_class
        logger.debug(f"Registered data adapter for {exchange.value}")

    @classmethod
    def register_execution_adapter(
        cls,
        exchange: Exchange,
        adapter_class: Type[ExecutionAdapter],
    ):
        """
        Register an execution adapter for an exchange.

        Args:
            exchange: Exchange enum value
            adapter_class: Adapter class (must implement ExecutionAdapter)
        """
        cls._execution_adapters[exchange] = adapter_class
        logger.debug(f"Registered execution adapter for {exchange.value}")

    @classmethod
    def create_data_adapter(
        cls,
        exchange: Union[Exchange, str],
        config: ExchangeConfig = None,
        **kwargs,
    ) -> DataAdapter:
        """
        Create a data adapter for the specified exchange.

        Args:
            exchange: Exchange enum value or string
            config: Exchange configuration
            **kwargs: Additional adapter-specific arguments

        Returns:
            DataAdapter instance

        Raises:
            ValueError: If exchange is not supported
        """
        cls._init_factory()

        # Convert string to enum if needed
        if isinstance(exchange, str):
            try:
                exchange = Exchange(exchange.lower())
            except ValueError:
                raise ValueError(f"Unknown exchange: {exchange}")

        adapter_class = cls._data_adapters.get(exchange)
        if adapter_class is None:
            supported = [e.value for e in cls._data_adapters.keys()]
            raise ValueError(
                f"Unsupported exchange: {exchange.value}. "
                f"Supported: {', '.join(supported)}"
            )

        # Merge config with kwargs
        if config is None:
            config = ExchangeConfig()

        # Pass config to adapter
        adapter = adapter_class(config=config, **kwargs)

        logger.info(f"Created data adapter for {exchange.value}")
        return adapter

    @classmethod
    def create_execution_adapter(
        cls,
        exchange: Union[Exchange, str],
        config: ExchangeConfig = None,
        **kwargs,
    ) -> ExecutionAdapter:
        """
        Create an execution adapter for the specified exchange.

        Args:
            exchange: Exchange enum value or string
            config: Exchange configuration
            **kwargs: Additional adapter-specific arguments

        Returns:
            ExecutionAdapter instance

        Raises:
            ValueError: If exchange is not supported
        """
        cls._init_factory()

        # Convert string to enum if needed
        if isinstance(exchange, str):
            try:
                exchange = Exchange(exchange.lower())
            except ValueError:
                raise ValueError(f"Unknown exchange: {exchange}")

        adapter_class = cls._execution_adapters.get(exchange)
        if adapter_class is None:
            supported = [e.value for e in cls._execution_adapters.keys()]
            raise ValueError(
                f"Unsupported exchange: {exchange.value}. "
                f"Supported: {', '.join(supported)}"
            )

        # Merge config with kwargs
        if config is None:
            config = ExchangeConfig()

        # Pass config to adapter
        adapter = adapter_class(config=config, **kwargs)

        logger.info(f"Created execution adapter for {exchange.value}")
        return adapter

    @classmethod
    def create(
        cls,
        exchange: Union[Exchange, str],
        config: ExchangeConfig = None,
        mode: str = "both",  # "data", "execution", or "both"
        **kwargs,
    ) -> Union[DataAdapter, ExecutionAdapter, tuple]:
        """
        Create adapters for an exchange.

        Args:
            exchange: Exchange enum value or string
            config: Exchange configuration
            mode: Which adapters to create ("data", "execution", or "both")
            **kwargs: Additional adapter-specific arguments

        Returns:
            Depending on mode:
            - "data": DataAdapter instance
            - "execution": ExecutionAdapter instance
            - "both": tuple of (DataAdapter, ExecutionAdapter)
        """
        if mode == "data":
            return cls.create_data_adapter(exchange, config, **kwargs)
        elif mode == "execution":
            return cls.create_execution_adapter(exchange, config, **kwargs)
        elif mode == "both":
            data = cls.create_data_adapter(exchange, config, **kwargs)
            execution = cls.create_execution_adapter(exchange, config, **kwargs)
            return data, execution
        else:
            raise ValueError(f"Unknown mode: {mode}")

    @classmethod
    def supported_exchanges(cls, mode: str = "data") -> List[Exchange]:
        """
        List supported exchanges.

        Args:
            mode: Which adapters to check ("data", "execution", or "all")

        Returns:
            List of supported Exchange enums
        """
        cls._init_factory()

        if mode == "data":
            return list(cls._data_adapters.keys())
        elif mode == "execution":
            return list(cls._execution_adapters.keys())
        elif mode == "all":
            return list(set(cls._data_adapters.keys()) | set(cls._execution_adapters.keys()))
        else:
            raise ValueError(f"Unknown mode: {mode}")

    @classmethod
    def exchange_info(cls, exchange: Union[Exchange, str]) -> dict:
        """
        Get information about an exchange.

        Args:
            exchange: Exchange enum value or string

        Returns:
            Dictionary with exchange information
        """
        cls._init_factory()

        # Convert string to enum if needed
        if isinstance(exchange, str):
            try:
                exchange = Exchange(exchange.lower())
            except ValueError:
                return {"error": f"Unknown exchange: {exchange}"}

        has_data = exchange in cls._data_adapters
        has_execution = exchange in cls._execution_adapters

        return {
            "exchange": exchange.value,
            "display_name": exchange.name.replace("_", " ").title(),
            "data_adapter": has_data,
            "execution_adapter": has_execution,
            "features": [
                "market_data" if has_data else None,
                "trading" if has_execution else None,
            ],
        }

    @classmethod
    def health_check_all(cls, config: ExchangeConfig = None) -> Dict[str, bool]:
        """
        Check health of all exchanges.

        Args:
            config: Exchange configuration (used for API key testing)

        Returns:
            Dictionary of exchange -> health status
        """
        cls._init_factory()

        results = {}
        for exchange in cls.supported_exchanges("data"):
            try:
                adapter = cls.create_data_adapter(exchange, config)
                results[exchange.value] = adapter.health_check()
            except Exception as e:
                logger.error(f"Health check failed for {exchange.value}: {e}")
                results[exchange.value] = False

        return results


# Convenience function for quick adapter creation
def create_adapter(
    exchange: str,
    api_key: str = "",
    api_secret: str = "",
    testnet: bool = True,
    mode: str = "data",
) -> Union[DataAdapter, ExecutionAdapter, tuple]:
    """
    Quick function to create an adapter.

    Args:
        exchange: Exchange name (e.g., "bybit", "binance")
        api_key: API key
        api_secret: API secret
        testnet: Use testnet
        mode: "data", "execution", or "both"

    Returns:
        Adapter instance(s)
    """
    config = ExchangeConfig(
        api_key=api_key,
        api_secret=api_secret,
        testnet=testnet,
    )

    return AdapterFactory.create(exchange, config, mode=mode)
