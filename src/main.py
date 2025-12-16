import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.analytics.engine import AnalyticsEngine
from src.api.analytics import router as analytics_router
from src.api.db import db_service
from src.api.dependencies import set_analytics_engine
from src.api.orderbook import router as orderbook_router

logger = logging.getLogger(__name__)


# Startup/shutdown handlers
@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator:
    """Manage app lifecycle"""
    # Startup
    logger.info("Starting up...")

    # Initialise analytics engine
    engine = AnalyticsEngine()
    set_analytics_engine(engine)

    # Start analytics engine in background
    import asyncio

    engine_task = asyncio.create_task(engine.start())

    # Initialise database
    await db_service.initialise()

    yield

    # Shutdown
    logger.info("Shutting down...")
    engine_task.cancel()
    await engine.stop()
    await db_service.close()


# Create app
app = FastAPI(
    title="Hermes Market Engine API", description="Real-time orderbook analytics and market data", version="0.1.0", lifespan=lifespan
)

# Register routers
app.include_router(analytics_router)
app.include_router(orderbook_router)


@app.get("/")
async def root() -> dict:
    """Root endpoint"""
    return {"service": "hermes-market-engine", "docs": "/docs", "openapi_schema": "/openapi.json"}
