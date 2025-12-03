# Ensure project root is in PYTHONPATH for direct script execution
# ruff: noqa: E402
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import asyncio
import signal
from pathlib import Path
from types import FrameType

from src.analytics.engine import AnalyticsEngine
from src.config import settings
from src.logging_config import get_logger, setup_logging

logger = get_logger(__name__)


async def main() -> None:
    engine = AnalyticsEngine()
    engine_task: asyncio.Task | None = None

    def shutdown_handler(_sig: int, _frame: FrameType | None) -> None:
        logger.info("Shutdown signal received")
        engine.should_run = False
        if engine_task and not engine_task.done():
            engine_task.cancel()

    # When SIGINT or SIGTERM is triggered (like ctrl + c ) use shutdown_handler
    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    try:
        engine_task = asyncio.create_task(engine.start())
        await engine_task
    except asyncio.CancelledError:
        logger.info("Engine task cancelled")
    finally:
        await engine.stop()


if __name__ == "__main__":
    setup_logging(settings.log_level)
    asyncio.run(main())
