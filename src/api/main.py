import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.api.analytics import router as analytics_router
from src.api.db import db_service
from src.api.history import router as history_router
from src.api.orderbook import router as orderbook_router

logger = logging.getLogger(__name__)


# Startup/shutdown handlers
@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator:
    """Manage app lifecycle"""
    # Startup
    logger.info("Starting up API...")

    # Analytics engine is managed by CLI and injected via set_analytics_engine()
    # Just initialise database
    await db_service.initialise()

    yield

    # Shutdown
    logger.info("Shutting down API...")
    # Analytics engine is stopped by CLI
    await db_service.close()


# Create app
app = FastAPI(
    title="Hermes Market Engine API", description="Real-time orderbook analytics and market data", version="0.1.0", lifespan=lifespan
)

# Register routers
app.include_router(analytics_router)
app.include_router(orderbook_router)
app.include_router(history_router)


@app.get("/")
async def root() -> dict:
    """Root endpoint"""
    return {"service": "hermes-market-engine", "docs": "/docs", "openapi_schema": "/openapi.json"}
