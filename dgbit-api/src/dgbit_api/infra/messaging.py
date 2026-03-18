import asyncio
import json
from contextlib import asynccontextmanager
from typing import Optional, Any, Dict

import pynng
from loguru import logger


class NNGClient:
    """Async NNG request-reply client for API to worker communication."""

    def __init__(self, address: str, timeout_ms: int = 30000):
        self.address = address
        self.timeout_ms = timeout_ms
        self._socket: Optional[pynng.Req0] = None

    async def connect(self) -> None:
        """Establish connection to the worker."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._sync_connect)

    def _sync_connect(self) -> None:
        self._socket = pynng.Req0(dial=self.address, block=False)
        logger.info(f"NNG client connected to {self.address}")

    async def send(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Send a message and wait for response."""
        if self._socket is None:
            await self.connect()

        data = json.dumps(message).encode("utf-8")
        loop = asyncio.get_event_loop()

        def _send_recv():
            self._socket.send(data)
            response = self._socket.recv()
            return json.loads(response.decode("utf-8"))

        return await loop.run_in_executor(None, _send_recv)

    async def close(self) -> None:
        """Close the connection."""
        if self._socket:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._socket.close)
            self._socket = None
            logger.info("NNG client connection closed")


class NNGWorker:
    """NNG reply socket for worker-side communication."""

    def __init__(self, address: str):
        self.address = address
        self._socket: Optional[pynng.Rep0] = None

    async def start(self) -> None:
        """Start listening for messages."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._sync_listen)

    def _sync_listen(self) -> None:
        self._socket = pynng.Rep0(listen=self.address)
        logger.info(f"NNG worker listening on {self.address}")

    async def recv(self) -> Dict[str, Any]:
        """Receive a message."""
        if self._socket is None:
            raise RuntimeError("Worker not started")

        loop = asyncio.get_event_loop()

        def _recv():
            message = self._socket.recv()
            return json.loads(message.decode("utf-8"))

        return await loop.run_in_executor(None, _recv)

    async def send(self, response: Dict[str, Any]) -> None:
        """Send a response."""
        if self._socket is None:
            raise RuntimeError("Worker not started")

        loop = asyncio.get_event_loop()
        data = json.dumps(response).encode("utf-8")

        def _send():
            self._socket.send(data)

        await loop.run_in_executor(None, _send)

    async def close(self) -> None:
        """Close the socket."""
        if self._socket:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._socket.close)
            self._socket = None


# Global client instance
_api_client: Optional[NNGClient] = None


def get_api_client() -> NNGClient:
    """Get the global API client."""
    global _api_client
    if _api_client is None:
        from dgbit_api.core.config import settings
        _api_client = NNGClient(settings.nng_command_address)
    return _api_client
