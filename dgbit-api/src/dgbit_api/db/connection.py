import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from tortoise import Tortoise, connections
from loguru import logger

from dgbit_api.core.config import settings

DATABASE_URL = "sqlite://db/dgbit.db"


async def init_db() -> None:
    """Initialize database connection and generate schemas."""
    logger.info("Initializing database connection...")

    await Tortoise.init(
        db_url=DATABASE_URL,
        modules={"models": ["dgbit_api.db.models"]},
    )

    # Generate schemas
    await Tortoise.generate_schemas()
    logger.info("Database initialized and schemas generated")


async def close_db() -> None:
    """Close database connections."""
    logger.info("Closing database connections...")
    await connections.close_all()


@asynccontextmanager
async def get_db() -> AsyncGenerator[Tortoise, None]:
    """Get database connection context."""
    await init_db()
    try:
        yield Tortoise.get_connection("default")
    finally:
        await close_db()
