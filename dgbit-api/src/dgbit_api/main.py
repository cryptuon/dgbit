from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from dgbit_api.api.routes import router
from dgbit_api.core.config import settings

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/", tags=["system"], summary="Root ping")
async def root() -> dict:
    return {"message": f"{settings.app_name} is running"}
