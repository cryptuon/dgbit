"""
Service Bus Orchestrator - Central coordinator for all dgbit services

Starts and manages all services, handles graceful shutdown,
and provides unified health monitoring.
"""

import asyncio
import signal
import sys
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass

SRC_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(SRC_DIR))

from loguru import logger


@dataclass
class ServiceConfig:
    """Configuration for a service."""
    name: str
    module: str
    func: str
    address: str
    auto_start: bool = True
    depends_on: List[str] = None


class ServiceBusOrchestrator:
    """
    Central orchestrator for all dgbit services.

    Manages service lifecycle, dependencies, and provides
    a unified entry point for running all services.
    """

    # Default service configurations
    SERVICES = [
        ServiceConfig(
            name="event_bus",
            module="dgbit_services.events",
            func="run_event_bus_service",
            address="ipc:///tmp/dgbit_evt.ipc",
            auto_start=True,
            depends_on=None,
        ),
        ServiceConfig(
            name="data_service",
            module="dgbit_data.service",
            func="run_service",
            address="ipc:///tmp/dgbit_data.ipc",
            auto_start=True,
            depends_on=["event_bus"],
        ),
        ServiceConfig(
            name="job_queue",
            module="dgbit_services.jobs",
            func="run_job_queue_service",
            address="ipc:///tmp/dgbit_queue.ipc",
            auto_start=True,
            depends_on=["event_bus"],
        ),
        ServiceConfig(
            name="strategy_service",
            module="dgbit_services.strategy",
            func="run_strategy_service",
            address="ipc:///tmp/dgbit_strategy.ipc",
            auto_start=True,
            depends_on=["event_bus", "data_service"],
        ),
        ServiceConfig(
            name="execution_service",
            module="dgbit_services.execution",
            func="run_execution_service",
            address="ipc:///tmp/dgbit_execution.ipc",
            auto_start=True,
            depends_on=["event_bus"],
        ),
    ]

    def __init__(self, services: List[ServiceConfig] = None):
        self._services = services or self.SERVICES
        self._running_services: Dict[str, asyncio.Task] = {}
        self._shutdown_event = asyncio.Event()

    async def start_service(self, config: ServiceConfig) -> asyncio.Task:
        """Start a single service."""
        logger.info(f"Starting service: {config.name}")

        # Import the service function
        import importlib
        module = importlib.import_module(config.module)
        service_func = getattr(module, config.func)

        # Create task
        task = asyncio.create_task(service_func())
        self._running_services[config.name] = task

        # Wait a bit for service to initialize
        await asyncio.sleep(0.5)

        logger.info(f"Service started: {config.name}")
        return task

    async def stop_service(self, name: str):
        """Stop a single service."""
        if name in self._running_services:
            task = self._running_services[name]
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            del self._running_services[name]
            logger.info(f"Service stopped: {name}")

    async def start_all(self):
        """Start all configured services."""
        logger.info("=" * 60)
        logger.info("Starting dgbit Service Bus")
        logger.info("=" * 60)

        # Build dependency graph and start in order
        started = set()
        remaining = {s.name: s for s in self._services}

        while remaining:
            # Find services whose dependencies are all started
            for name, config in list(remaining.items()):
                dependencies_met = all(
                    d in started or d is None
                    for d in (config.depends_on or [])
                )

                if dependencies_met:
                    await self.start_service(config)
                    started.add(name)
                    del remaining[name]

            # Safety check for circular dependencies
            if remaining and all(
                not all(d in started or d is None for d in s.depends_on or [])
                for s in remaining.values()
            ):
                # Try to start anyway - might fail but at least we try
                name, config = next(iter(remaining.items()))
                logger.warning(f"Starting {name} with unmet dependencies")
                await self.start_service(config)
                started.add(name)
                del remaining[name]

        logger.info("=" * 60)
        logger.info(f"All services started: {', '.join(started)}")
        logger.info("=" * 60)

    async def stop_all(self):
        """Stop all running services."""
        logger.info("Stopping all services...")

        # Stop in reverse order
        for name in reversed(list(self._running_services.keys())):
            await self.stop_service(name)

        logger.info("All services stopped")

    async def wait_for_shutdown(self):
        """Wait for shutdown signal."""
        await self._shutdown_event.wait()

    def signal_handler(self):
        """Handle shutdown signals."""
        def handle(sig):
            logger.info(f"Received signal {sig}")
            asyncio.create_task(self.stop_all())
            self._shutdown_event.set()

        return handle

    async def run(self):
        """Run the orchestrator."""
        # Setup signal handlers
        loop = asyncio.get_running_loop()

        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, self.signal_handler())

        # Start all services
        await self.start_all()

        # Wait for shutdown
        await self.wait_for_shutdown()


async def run_service_bus():
    """Run the complete service bus."""
    orchestrator = ServiceBusOrchestrator()

    try:
        await orchestrator.run()
    except KeyboardInterrupt:
        logger.info("Interrupted")
    finally:
        await orchestrator.stop_all()


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="dgbit Service Bus")
    parser.add_argument(
        "--services", nargs="+",
        help="Specific services to start (default: all)"
    )
    parser.add_argument(
        "--log-level", default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Log level"
    )

    args = parser.parse_args()

    # Setup logging
    logger.remove()
    logger.add(sys.stdout, level=args.log_level)

    # Filter services if requested
    if args.services:
        services = [
            s for s in ServiceBusOrchestrator.SERVICES
            if s.name in args.services
        ]
    else:
        services = None

    # Run orchestrator
    orchestrator = ServiceBusOrchestrator(services=services)
    asyncio.run(orchestrator.run())


if __name__ == "__main__":
    main()
