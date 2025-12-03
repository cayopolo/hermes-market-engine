
# Ensure project root is in PYTHONPATH for direct script execution
import sys
from pathlib import Path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import asyncio
import logging
import os
import signal

from src.config import settings
from src.data_collection.ingestor import DataCollectionService
from src.logging_config import get_logger, setup_logging

logger = get_logger(__name__)

async def main() -> None:
    service = DataCollectionService()

    # Graceful shutdown handler
    def shutdown_handler(sig, frame) -> None:
        asyncio.create_task(service.stop())

    # When SIGINT or SIGTERM is triggered (like ctrl + c ) use shutdown_handler
    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    await service.start()

if __name__ == "__main__":
    setup_logging(level=settings.log_level)
    asyncio.run(main())
