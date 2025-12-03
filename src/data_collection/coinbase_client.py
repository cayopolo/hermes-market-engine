import asyncio
import json
import logging
from collections.abc import Awaitable, Callable

import websockets

from src.config import settings

MessageHandler = Callable[[str | bytes, float], Awaitable[None]]

logger = logging.getLogger(__name__)


class CoinbaseWebsocketClient:
    """A client for connecting to Coinbase's WebSocket feed (with auto-reconnect)."""

    def __init__(self, on_message: MessageHandler) -> None:
        self.on_message = on_message
        self.should_run = False
        self._connection = None

    async def start(self) -> None:
        """Start the WebSocket with auto-reconnect."""
        self.should_run = True

        while self.should_run:
            try:
                await self._connect_and_listen()

            except Exception as e:
                logger.error("WebSocket connection error: %s", e)

            if self.should_run:
                logger.info("Reconnecting in 3 seconds...")
                # Wait before reconnecting
                await asyncio.sleep(3)

    async def stop(self) -> None:
        """Gracefully stop the WebSocket connection."""
        self.should_run = False
        if self._connection:
            await self._connection.close()

    async def _connect_and_listen(self) -> None:
        """Establish the WebSocket connection and process messages."""
        logger.info("Connecting to %s", settings.coinbase_ws_url)

        async with websockets.connect(settings.coinbase_ws_url, max_size=None, ping_interval=None) as websocket:
            self._connection = websocket

            # Subscribe
            subscribe_message = {"type": "subscribe", "channel": settings.channel, "product_ids": [settings.product_id]}

            await websocket.send(json.dumps(subscribe_message))
            logger.info("Subscribed to %s for %s", settings.channel, settings.product_id)

            # Listen loop
            while self.should_run:
                try:
                    message = await websocket.recv()
                    recv_time = asyncio.get_event_loop().time()
                    await self.on_message(message, recv_time)

                except websockets.ConnectionClosed:
                    logger.warning("WebSocket connection closed")
                    break
