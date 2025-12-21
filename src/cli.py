"""CLI for running Hermes Market Engine services."""

import asyncio
import contextlib
import signal
from types import FrameType

import click
import uvicorn

from src.analytics.engine import AnalyticsEngine
from src.api.dependencies import set_analytics_engine
from src.api.main import app
from src.config import settings
from src.data_collection.ingestor import DataCollectionService
from src.logging_config import get_logger, setup_logging

logger = get_logger(__name__)


@click.command()
@click.option("--log-level", type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"], case_sensitive=False), help="Set logging level")
def cli(log_level: str | None) -> None:
    """Hermes Market Engine - Real-time market data platform.

    Starts the data collection and analytics services.
    """
    setup_logging(level=log_level or settings.log_level)
    logger.info("Starting Hermes Market Engine...")

    async def run() -> None:
        collector_service = DataCollectionService()
        analytics_engine = AnalyticsEngine()

        # API
        set_analytics_engine(analytics_engine)

        config = uvicorn.Config(app=app, host=settings.api_host, port=settings.api_port, log_level=settings.log_level.lower())
        server = uvicorn.Server(config)

        collector_task: asyncio.Task | None = None
        analytics_task: asyncio.Task | None = None
        api_task: asyncio.Task | None = None
        shutdown_event = asyncio.Event()

        def shutdown_handler(_sig: int, _frame: FrameType | None) -> None:
            logger.info("Shutdown signal received")
            shutdown_event.set()

            # Stop collector
            if collector_service.ws_client:
                collector_service.ws_client.should_run = False

            # Stop analytics
            analytics_engine.should_run = False

            # Stop API server
            server.should_exit = True

            if analytics_task and not analytics_task.done():
                analytics_task.cancel()
            if collector_task and not collector_task.done():
                collector_task.cancel()
            if api_task and not api_task.done():
                api_task.cancel()

        signal.signal(signal.SIGINT, shutdown_handler)
        signal.signal(signal.SIGTERM, shutdown_handler)

        try:
            # Start all services concurrently
            api_task = asyncio.create_task(server.serve(), name="api")
            collector_task = asyncio.create_task(collector_service.start(), name="collector")
            analytics_task = asyncio.create_task(analytics_engine.start(), name="analytics")

            logger.info("All services started successfully")
            logger.info("FastAPI server running at http://%s:%s", settings.api_host, settings.api_port)
            logger.info("API docs available at http://%s:%s/docs", settings.api_host, settings.api_port)

            # Wait for shutdown signal or any task to fail
            done, pending = await asyncio.wait(
                [api_task, collector_task, analytics_task, asyncio.create_task(shutdown_event.wait())], return_when=asyncio.FIRST_COMPLETED
            )

            # If a service task completed/failed, trigger shutdown
            for task in done:
                if task.get_name() in ["api", "collector", "analytics"] and not shutdown_event.is_set():
                    logger.error("Service %s stopped unexpectedly", task.get_name())
                    shutdown_event.set()

            # Cancel remaining tasks
            for task in pending:
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task

        except asyncio.CancelledError:
            logger.info("All services cancelled")
        finally:
            # Graceful shutdown
            logger.info("Stopping all services...")
            await collector_service.stop()
            await analytics_engine.stop()
            logger.info("All services stopped")

    asyncio.run(run())


if __name__ == "__main__":
    cli()
