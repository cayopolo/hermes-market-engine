import asyncio
import contextlib
import logging
from collections import deque
from datetime import UTC, datetime
from typing import Any

import asyncpg
import orjson

from src.data_models import CoinbaseMessage

logger = logging.getLogger(__name__)


class BatchedDBWriter:
    """Handles batched writing of raw messages to PostgreSQL with time-based flushing."""

    def __init__(self, pool: asyncpg.Pool, connection_id: str, batch_interval: float, batch_size: int, max_retries: int):
        self.pool = pool
        self.connection_id = connection_id
        self.batch_interval = batch_interval
        self.batch_size = batch_size
        self.max_retries = max_retries

        # Thread-safe buffer with overflow protection
        self._buffer: deque[dict[str, Any]] = deque(maxlen=batch_size * 2)
        self._buffer_lock = asyncio.Lock()

        self._flush_task: asyncio.Task | None = None
        self._running = False

    async def start(self) -> None:
        """Start the periodic flush task"""
        self._running = True
        self._flush_task = asyncio.create_task(self._periodic_flush())
        logger.info("BatchedDBWriter started (flush interval: %ss)", self.batch_interval)

    async def stop(self) -> None:
        """Stop the flush task and flush remaining buffer"""
        logger.info("Stopping BatchedDBWriter...")
        self._running = False

        if self._flush_task:
            self._flush_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._flush_task

        await self._flush()
        logger.info("BatchedDBWriter stopped")

    async def enqueue(self, message: CoinbaseMessage, received_at: float) -> None:
        """Add message to buffer (thread-safe)"""
        async with self._buffer_lock:
            if len(self._buffer) >= self.batch_size * 2:
                logger.warning("Buffer overflow! Dropping oldest message")

            row = self._transform_message(message, received_at)
            self._buffer.append(row)

    async def _periodic_flush(self) -> None:
        """Background task that flushes buffer every N seconds"""
        while self._running:
            try:
                await asyncio.sleep(self.batch_interval)
                await self._flush()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in periodic flush: %s", e)

    async def _flush(self) -> None:
        """Extract batch from buffer and write to database"""
        async with self._buffer_lock:
            if not self._buffer:
                return

            batch_size = min(len(self._buffer), self.batch_size)
            batch = [self._buffer.popleft() for _ in range(batch_size)]

        if batch:
            logger.debug("Flushing %d messages to database", len(batch))
            await self._execute_batch_with_retry(batch)

    async def _execute_batch_with_retry(self, batch: list[dict[str, Any]]) -> None:
        """Execute batch insert with exponential backoff"""
        for attempt in range(self.max_retries):
            try:
                async with self.pool.acquire() as conn:
                    await conn.executemany(
                        """
                        INSERT INTO raw_events_stream (
                            connection_id, sequence_num, product_id, channel,
                            exchange_timestamp, received_at, event_type, raw_message
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                        ON CONFLICT (connection_id, product_id, sequence_num) DO NOTHING
                        """,
                        [
                            (
                                row["connection_id"],
                                row["sequence_num"],
                                row["product_id"],
                                row["channel"],
                                row["exchange_timestamp"],
                                row["received_at"],
                                row["event_type"],
                                row["raw_message"],
                            )
                            for row in batch
                        ],
                    )
                logger.debug("Successfully wrote %d messages to database", len(batch))
                return

            except Exception as e:
                wait_time = 2**attempt
                logger.error("Database write failed (attempt %d/%d): %s. Retrying in %ds...", attempt + 1, self.max_retries, e, wait_time)

                if attempt < self.max_retries - 1:
                    await asyncio.sleep(wait_time)
                else:
                    logger.error("Max retries reached. Dropping batch of %d messages", len(batch))

    def _transform_message(self, message: CoinbaseMessage, received_at: float) -> dict[str, Any]:
        """Transform CoinbaseMessage to database row format"""
        event_type = message.events[0].type if message.events else "unknown"
        product_id = message.events[0].product_id if message.events else "unknown"
        raw_message_json = orjson.dumps(message.model_dump(mode="json")).decode("utf-8")

        return {
            "connection_id": self.connection_id,
            "sequence_num": message.sequence_num,
            "product_id": product_id,
            "channel": message.channel,
            "exchange_timestamp": message.timestamp,
            "received_at": datetime.fromtimestamp(received_at, tz=UTC),
            "event_type": event_type,
            "raw_message": raw_message_json,
        }
