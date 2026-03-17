from contextlib import contextmanager
from typing import Generator

import pynng


class CommandSocket:
    """Simple req/rep socket wrapper used to communicate with workers."""

    def __init__(self, address: str) -> None:
        self.address = address
        self._socket = pynng.Req0()
        self._socket.dial(address, block=False)

    def send(self, message: bytes) -> bytes:
        self._socket.send(message)
        return self._socket.recv()

    def close(self) -> None:
        self._socket.close()


@contextmanager
def worker_command_socket(address: str) -> Generator[pynng.Rep0, None, None]:
    """Context manager for worker-side reply socket."""

    sock = pynng.Rep0(listen=address)
    try:
        yield sock
    finally:
        sock.close()
