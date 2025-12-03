import asyncio
import signal
import sys
from pathlib import Path
from types import FrameType

from src.analytics.engine import AnalyticsEngine
from src.config import settings
from src.logging_config import get_logger, setup_logging

logger = get_logger(__name__)

# Ensure project root is in PYTHONPATH for direct script execution
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


async def main() -> None:
    engine = AnalyticsEngine()
    shutdown_task: asyncio.Task | None = None

    def shutdown_handler(_sig: int, _frame: FrameType | None) -> None:
        nonlocal shutdown_task
        shutdown_task = asyncio.create_task(engine.stop())

    # When SIGINT or SIGTERM is triggered (like ctrl + c ) use shutdown_handler
    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    await engine.start()


if __name__ == "__main__":
    logger = setup_logging(settings.log_level)
    asyncio.run(main())
