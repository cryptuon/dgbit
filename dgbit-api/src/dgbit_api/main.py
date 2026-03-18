from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from dgbit_api.api.routes import router
from dgbit_api.core.config import settings
from dgbit_api.core.logging import setup_logging
from dgbit_api.db.connection import init_db, close_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup/shutdown."""
    # Startup
    setup_logging(
        log_level=settings.log_level,
        format="json" if settings.environment == "production" else "pretty"
    )
    logger.info(f"Starting {settings.app_name} in {settings.environment} mode")

    # Initialize database
    await init_db()

    yield

    # Shutdown
    logger.info("Shutting down application...")
    await close_db()


app = FastAPI(
    title=settings.app_name,
    version="0.2.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


app.include_router(router)


@app.get("/", tags=["system"], summary="Root ping")
async def root() -> dict:
    return {"message": f"{settings.app_name} is running", "version": "0.2.0"}
