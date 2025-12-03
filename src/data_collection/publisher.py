import logging

import orjson
import redis.asyncio as redis

from src.config import settings
from src.data_models import HotPathPacket

logger = logging.getLogger(__name__)


class Publisher:
    """Publishes market data to Redis (Hot Path)"""

    def __init__(self):
        self.client: redis.Redis | None = None

    async def connect(self) -> None:
        """Establish Redis connection"""
        self.client = redis.from_url(settings.redis_url)

        if self.client is None:
            raise RuntimeError("Failed to create Redis client")

        # Verify connection with ping
        await self.client.ping()  # type: ignore[misc]
        logger.info("Connected to Redis")

    async def disconnect(self) -> None:
        """Close Redis connection"""
        if self.client:
            await self.client.close()
            logger.info("Disconnected from Redis")

    async def publish(self, packet: HotPathPacket) -> None:
        """Publish hot path packet to Redis channel"""
        try:
            message = orjson.dumps(packet.model_dump(mode="json"))
            if self.client:
                await self.client.publish(settings.redis_channel, message)
        except Exception as e:
            logger.error("Redis publish failed: %s", e)
