import logging
from datetime import datetime

import asyncpg

from src.config import settings

logger = logging.getLogger(__name__)


class DatabaseService:
    """Service for querying historical market data"""

    def __init__(self):
        self.pool: asyncpg.Pool | None = None

    async def initialise(self) -> None:
        """Create connection pool"""
        database_url = f"postgresql://{settings.db_user}:{settings.db_password}@{settings.db_host}:{settings.db_port}/{settings.db_name}"
        self.pool = await asyncpg.create_pool(
            database_url, min_size=settings.db_pool_min_size, max_size=settings.db_pool_max_size, command_timeout=60
        )
        logger.info("Database connection pool initialised")

    async def close(self) -> None:
        """Close connection pool"""
        if self.pool:
            await self.pool.close()
            logger.info("Database connection pool closed")

    async def get_orderbook_snapshots(self, product_id: str, start_time: datetime, end_time: datetime, limit: int = 100) -> list[dict]:
        """
        Query historical orderbook snapshots.

        Args:
            product_id: Trading pair (e.g., 'ETH-EUR')
            start_time: Earliest snapshot to fetch
            end_time: Latest snapshot to fetch
            limit: Max number of snapshots to return

        Returns:
            List of orderbook snapshots with analytics
        """
        if not self.pool:
            raise RuntimeError("Database not initialised")

        query = """
        SELECT id, exchange_timestamp, bids_snapshot, asks_snapshot, analytics
        FROM order_book_snapshot
        WHERE product_id = $1
            AND exchange_timestamp BETWEEN $2 AND $3
        ORDER BY exchange_timestamp DESC
        LIMIT $4
        """

        rows = await self.pool.fetch(query, product_id, start_time, end_time, limit)

        return [dict(row) for row in rows]

    async def get_raw_events(
        self, product_id: str, start_time: datetime, end_time: datetime, event_type: str | None = None, limit: int = 100
    ) -> list[dict]:
        """
        Query raw market events.

        Args:
            product_id: Trading pair
            start_time: Earliest event
            end_time: Latest event
            event_type: Filter by 'snapshot' or 'update' (optional)
            limit: Max events to return

        Returns:
            List of raw events
        """
        if not self.pool:
            raise RuntimeError("Database not initialised")

        base_query = """
        SELECT id, sequence_num, raw_message
        FROM raw_events_stream
        WHERE product_id = $1
            AND exchange_timestamp BETWEEN $2 AND $3
        """

        params = [product_id, start_time, end_time]
        param_idx = 4

        if event_type:
            base_query += f" AND event_type = ${param_idx}"
            params.append(event_type)
            param_idx += 1

        base_query += f" ORDER BY exchange_timestamp DESC LIMIT ${param_idx}"
        params.append(limit)

        rows = await self.pool.fetch(base_query, *params)

        return [dict(row) for row in rows]


# Global instance (initialised at startup)
db_service = DatabaseService()
