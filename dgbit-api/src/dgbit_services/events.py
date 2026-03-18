"""
Event Bus Service - PUB/SUB for real-time events

Provides async event distribution for:
- Job status updates
- Trade notifications
- System alerts
- Metrics
"""

import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

# Add parent to path
SRC_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(SRC_DIR))

import pynng
from loguru import logger

from dgbit_services import Event, EventType, ServiceBase, ServiceType


class EventBus:
    """
    Central event bus for pub/sub communication.

    Usage:
        # Publisher
        bus = EventBus()
        bus.publish(Event("job.completed", {"job_id": "123"}))

        # Subscriber
        bus.subscribe("job.*", handler)
        bus.start()
    """

    DEFAULT_ADDRESS = "ipc:///tmp/dgbit_evt.ipc"

    def __init__(self, address: str = None):
        self.address = address or self.DEFAULT_ADDRESS
        self._pub_socket = None
        self._running = False
        self._subscriptions: Dict[str, List[Callable]] = {}

    def _ensure_pub_socket(self):
        """Ensure publisher socket is connected."""
        if self._pub_socket is None:
            self._pub_socket = pynng.Pub0(listen=self.address)
            logger.info(f"Event bus publisher listening on {self.address}")

    def publish(self, event: Event) -> None:
        """Publish an event to all subscribers."""
        self._ensure_pub_socket()

        try:
            self._pub_socket.send(event.to_bytes())
            logger.debug(f"Published event: {event.event_type}")
        except Exception as e:
            logger.error(f"Failed to publish event: {e}")

    def publish_sync(self, event_type: str, data: Dict[str, Any], source: str = "system") -> None:
        """Convenience method to publish synchronously."""
        event = Event(
            event_type=event_type,
            data=data,
            source=source,
        )
        self.publish(event)

    def subscribe(self, event_pattern: str, handler: Callable) -> None:
        """
        Subscribe to events matching pattern.

        Patterns support wildcards:
        - "job.*" matches "job.created", "job.completed", etc.
        - "trade.*" matches all trade events
        - "*" matches all events
        """
        if event_pattern not in self._subscriptions:
            self._subscriptions[event_pattern] = []
        self._subscriptions[event_pattern].append(handler)
        logger.info(f"Subscribed to {event_pattern}")

    def unsubscribe(self, event_pattern: str, handler: Callable = None) -> None:
        """Unsubscribe from events."""
        if event_pattern in self._subscriptions:
            if handler:
                self._subscriptions[event_pattern].remove(handler)
            else:
                del self._subscriptions[event_pattern]

    def _match_pattern(self, event_type: str, pattern: str) -> bool:
        """Check if event type matches pattern."""
        if pattern == "*" or pattern == event_type:
            return True

        if pattern.endswith("*"):
            prefix = pattern[:-1]
            if event_type.startswith(prefix):
                return True

        if pattern.startswith("*"):
            suffix = pattern[1:]
            if event_type.endswith(suffix):
                return True

        return False

    def _dispatch(self, event: Event) -> None:
        """Dispatch event to matching handlers."""
        for pattern, handlers in self._subscriptions.items():
            if self._match_pattern(event.event_type, pattern):
                for handler in handlers:
                    try:
                        if asyncio.iscoroutinefunction(handler):
                            asyncio.create_task(handler(event))
                        else:
                            handler(event)
                    except Exception as e:
                        logger.error(f"Error in event handler: {e}")

    async def start(self, blocking: bool = True):
        """Start the event bus subscriber."""
        self._running = True

        # Create subscriber socket
        sub_socket = pynng.Sub0(dial=self.address)
        sub_socket.recv_timeout = 100  # Non-blocking with timeout

        # Subscribe to all events
        sub_socket.subscribe(b"")

        logger.info(f"Event bus subscriber connected to {self.address}")

        while self._running:
            try:
                message = sub_socket.recv()
                event = Event.from_bytes(message)
                self._dispatch(event)
            except pynng.Timeout:
                await asyncio.sleep(0.01)
            except Exception as e:
                logger.error(f"Event bus error: {e}")

    def start_background(self):
        """Start event bus in background."""
        asyncio.create_task(self.start())

    def stop(self):
        """Stop the event bus."""
        self._running = False
        logger.info("Event bus stopped")

    def close(self):
        """Close all connections."""
        self.stop()
        if self._pub_socket:
            self._pub_socket.close()
            self._pub_socket = None


class EventBusService(ServiceBase):
    """
    Full event bus service that runs as a standalone process.

    Combines publisher and subscriber functionality.
    """

    def __init__(
        self,
        name: str = "event_bus",
        pub_address: str = "ipc:///tmp/dgbit_evt.ipc",
        sub_address: str = "ipc:///tmp/dgbit_evt.ipc",
    ):
        super().__init__(
            name=name,
            service_type=ServiceType.METRICS,
            addresses={"pub": pub_address, "sub": sub_address}
        )
        self._pub_address = pub_address
        self._sub_address = sub_address
        self._event_bus = EventBus(pub_address)
        self._sub_socket = None

    async def start(self):
        """Start the event bus service."""
        from dgbit_services import ServiceRegistry, Event, EventType

        self._running = True

        # Connect subscriber
        self._sub_socket = pynng.Sub0(dial=self._sub_address)
        self._sub_socket.subscribe(b"")

        # Register in service registry
        registry = ServiceRegistry()
        registry.register(self)

        # Publish startup event
        self._event_bus.publish(Event(
            event_type=EventType.SERVICE_STARTED.value,
            data={"service": self.name, "address": self._pub_address},
            source=self.name,
        ))

        logger.info(f"Event bus service started on {self._pub_address}")

        # Main loop
        while self._running:
            try:
                message = self._sub_socket.recv()
                event = Event.from_bytes(message)

                # Re-publish to all connected subscribers
                self._event_bus.publish(event)

            except pynng.Timeout:
                await asyncio.sleep(0.01)
            except Exception as e:
                logger.error(f"Event bus service error: {e}")

    async def stop(self):
        """Stop the event bus service."""
        from dgbit_services import ServiceRegistry, Event, EventType

        self._running = False

        # Unregister from registry
        registry = ServiceRegistry()
        registry.unregister(self.name, self.service_type)

        # Publish shutdown event
        self._event_bus.publish(Event(
            event_type=EventType.SERVICE_STOPPED.value,
            data={"service": self.name},
            source=self.name,
        ))

        if self._sub_socket:
            self._sub_socket.close()
            self._sub_socket = None

        self._event_bus.close()
        logger.info("Event bus service stopped")

    async def handle_command(self, message) -> Dict[str, Any]:
        """Handle admin commands."""
        if message.command == "ping":
            return {"status": "ok", "events": len(self._event_bus._subscriptions)}
        elif message.command == "stats":
            return {
                "subscriptions": len(self._event_bus._subscriptions),
                "patterns": list(self._event_bus._subscriptions.keys()),
            }
        else:
            return {"error": f"Unknown command: {message.command}"}


# =============================================================================
# Event Handlers for Common Use Cases
# =============================================================================

def create_job_event_handler(event_bus: EventBus) -> Callable:
    """Create a handler that forwards job events to logging."""
    def handler(event: Event):
        logger.info(f"[JOB] {event.event_type}: {event.data}")
    return handler


def create_metrics_event_handler(event_bus: EventBus) -> Callable:
    """Create a handler that collects metrics."""
    _metrics = {}

    def handler(event: Event):
        event_type = event.event_type
        if event_type not in _metrics:
            _metrics[event_type] = 0
        _metrics[event_type] += 1

    def get_metrics():
        return _metrics.copy()

    handler.get_metrics = get_metrics
    return handler


def create_webhook_event_handler(event_bus: EventBus, webhook_url: str) -> Callable:
    """Create a handler that forwards events to a webhook."""
    import httpx

    async def handler(event: Event):
        try:
            async with httpx.AsyncClient() as client:
                await client.post(webhook_url, json=event.model_dump())
        except Exception as e:
            logger.error(f"Webhook error: {e}")

    return handler


# =============================================================================
# Run as Service
# =============================================================================

async def run_event_bus_service():
    """Run the event bus service as a standalone process."""
    import argparse

    parser = argparse.ArgumentParser(description="dgbit Event Bus Service")
    parser.add_argument("--address", default="ipc:///tmp/dgbit_evt.ipc")
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()

    # Setup logging
    logger.remove()
    logger.add(sys.stdout, level=args.log_level)

    # Create and run service
    service = EventBusService(pub_address=args.address, sub_address=args.address)

    try:
        await service.start()
    except KeyboardInterrupt:
        await service.stop()


if __name__ == "__main__":
    asyncio.run(run_event_bus_service())
