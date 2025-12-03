import logging
from uuid import uuid4

import orjson

from src.data_collection.coinbase_client import CoinbaseWebsocketClient
from src.data_collection.publisher import Publisher
from src.data_models import CoinbaseMessage, HotPathPacket

logger = logging.getLogger(__name__)


class DataCollectionService:
    """Main orchestrator for data collection"""

    def __init__(self):
        self.connection_id = uuid4()
        self.sequence_tracker = -1

        # Components
        self.redis_publisher = Publisher()
        self.ws_client: CoinbaseWebsocketClient | None = None

    async def initialise(self) -> None:
        """Set up all connections"""
        logger.info("Initializing Data Collection Service (ID: %s)", self.connection_id)
        await self.redis_publisher.connect()
        self.ws_client = CoinbaseWebsocketClient(self._handle_message)

    async def start(self) -> None:
        """Start the service"""
        await self.initialise()
        logger.info("Data Collection Service started")

        if self.ws_client is None:
            raise RuntimeError("WebSocket client not initialized")
        await self.ws_client.start()

    async def stop(self) -> None:
        """Graceful shutdown"""
        logger.info("Stopping Data Collection Service...")

        if self.ws_client:
            await self.ws_client.stop()
        await self.redis_publisher.disconnect()

        logger.info("Data Collection Service stopped")

    async def _handle_message(self, raw_message: str | bytes, recv_time: float) -> None:
        """
        Process incoming WebSocket message. Publish to Hot Path + enqueue to Cold Path (TODO)
        """
        try:
            # Parse with orjson for performance
            data = orjson.loads(raw_message)

            # Skip subscription confirmations
            if data.get("channel") == "subscriptions":
                logger.info("Subscription confirmed")
                self.sequence_tracker = data["sequence_num"]
                return

            # Handle error messages separately
            if data.get("type") == "error":
                logger.error("WebSocket error: %s", data.get("message", data))
                return

            # Validate and parse
            message = CoinbaseMessage(**data)

            # Sequence gap detection
            if self.sequence_tracker >= 0:
                gap = message.sequence_num - self.sequence_tracker - 1

                if gap > 1:  # Gap detected, restart
                    logger.error(
                        "SEQUENCE GAP DETECTED! Expected %s, got %s (gap: %s). Restarting connection...",
                        self.sequence_tracker + 1,
                        message.sequence_num,
                        gap,
                    )
                    if self.ws_client:
                        await self.ws_client.stop()
                    return

                if gap < 0:  # Stale message, skip
                    logger.warning("Stale message: %s < %s", message.sequence_num, self.sequence_tracker + 1)
                    return

            self.sequence_tracker = message.sequence_num

            # HOT PATH: Publish to Redis
            hot_packet = HotPathPacket(ts_ingest=recv_time, connection_id=str(self.connection_id), payload=message)
            await self.redis_publisher.publish(hot_packet)

            # TODO: COLD PATH: Enqueue for batched DB write

        except Exception as e:
            logger.error("Error handling message: %s", e)
