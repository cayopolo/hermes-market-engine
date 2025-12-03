import asyncio
import logging
from typing import TYPE_CHECKING

import orjson
import redis.asyncio as redis

from src.config import settings
from src.data_models import HotPathPacket

from .orderbook import OrderBook

if TYPE_CHECKING:
    from redis.asyncio.client import PubSub

logger = logging.getLogger(__name__)


class AnalyticsEngine:
    """Subscribes to market data and computes analytics (Service 4.2)"""

    def __init__(self):
        self.redis_client: redis.Redis | None = None
        self.pubsub: PubSub | None = None
        self.orderbook: OrderBook | None = None
        self.should_run = False

    async def start(self) -> None:
        """Start the analytics engine"""
        logger.info("Starting Analytics Engine")

        # Connect to Redis
        self.redis_client = redis.from_url(settings.redis_url)

        # Check if there are any publishers on the channel
        num_publishers = await self.redis_client.pubsub_numsub(settings.redis_channel)
        if num_publishers and num_publishers[0][1] == 0:
            logger.warning("No publishers found on channel %s. Waiting for publishers...", settings.redis_channel)

        self.pubsub = self.redis_client.pubsub()
        await self.pubsub.subscribe(settings.redis_channel)
        logger.info("Subscribed to %s", settings.redis_channel)

        # Initialise order book
        self.orderbook = OrderBook(settings.product_id)

        self.should_run = True
        await self._listen()

    async def stop(self) -> None:
        """Graceful shutdown"""
        logger.info("Stopping Analytics Engine")
        self.should_run = False

        if self.pubsub:
            await self.pubsub.unsubscribe(settings.redis_channel)
            await self.pubsub.close()
        if self.redis_client:
            await self.redis_client.close()

    async def _listen(self) -> None:
        """Listen for messages and process"""
        assert self.orderbook is not None, "OrderBook must be initialized before listening"
        logger.info("Analytics Engine listening for messages...")
        if self.pubsub:
            try:
                while self.should_run:
                    # Use timeout check is should_run periodically (every ~0.1s)
                    message = await self.pubsub.get_message(ignore_subscribe_messages=True, timeout=0.1)

                    if message is None:
                        # No message available, loop will check should_run flag
                        continue

                    if message["type"] != "message":
                        continue

                    try:
                        # Deserialise
                        packet = HotPathPacket(**orjson.loads(message["data"]))

                        # Process each event
                        for event in packet.payload.events:
                            # Skip events for other products
                            if event.product_id != self.orderbook.product_id:
                                continue

                            success = self.orderbook.apply_event(event, packet.payload.sequence_num)

                            if not success:
                                logger.error("Order book corrupted, restarting service...")
                                await self.stop()
                                return

                        # Calculate and log analytics (only if initialised)
                        if self.orderbook.initialised:
                            analytics = self.orderbook.get_analytics()
                            logger.info(
                                "Analytics | Bid: %s | Ask: %s | Spread: %s | Mid: %s",
                                analytics.best_bid,
                                analytics.best_ask,
                                analytics.spread,
                                analytics.midprice,
                            )

                    except Exception:
                        logger.exception("Error processing message")

            except asyncio.CancelledError:
                logger.info("Listen task cancelled, shutting down...")
                raise
