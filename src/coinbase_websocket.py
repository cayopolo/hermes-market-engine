##########################################################
# THIS FILE HAS NOW BEEN DEPRECATED. KEEPING FOR REFERENCE
##########################################################

import asyncio
import json
import uuid
from datetime import datetime
from operator import neg
from pathlib import Path

import asyncpg
import websockets
from sortedcontainers import SortedDict
from websockets.exceptions import ConnectionClosedError, ConnectionClosedOK

from config import Settings
from logging_config import get_logger, setup_logging

logger = get_logger(__name__)

# Load configuration
settings = Settings()

DB_USER = settings.db_user
DB_NAME = settings.db_name
DB_PASSWORD = settings.db_password

COINBASE_WEBSOCKET_URL = settings.coinbase_ws_url
PRODUCT_ID = settings.product_id
CHANNEL = settings.channel

OUTPUT_PATH = Path(f"{CHANNEL.lower()}_{PRODUCT_ID.lower()}.json")


async def insert_raw_event(conn: asyncpg.connection.Connection, connection_id: uuid.UUID, message: dict) -> None:
    """Insert raw WebSocket event into database with connection tracking."""
    # Extract event details - handle cases where events array might be empty
    events = message.get("events", [])
    if not events:
        logger.warning("Empty events array in message seq=%s", message.get("sequence_num"))
        return

    # For l2_data, there's typically only one event
    # TODO: Check whether we will miss data due to assumption of one event
    first_event = events[0]
    event_type = first_event.get("type")
    product_id = first_event.get("product_id")

    # Skip subscription confirmation messages
    if event_type is None or product_id is None:
        return

    await conn.execute(
        """
        INSERT INTO raw_events_stream (
            connection_id,
            sequence_num,
            product_id,
            channel,
            exchange_timestamp,
            event_type,
            raw_message
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        """,
        connection_id,
        message["sequence_num"],
        product_id,
        message["channel"],
        datetime.fromisoformat(message["timestamp"].replace("Z", "+00:00")),
        event_type,
        json.dumps(message),
    )


async def local_order_book(
    event_type: str, event_sequence_num: int, orderbook_sequence_num: int, updates: list[dict[str, str]], bids: SortedDict, asks: SortedDict
) -> tuple[SortedDict, SortedDict, int, bool]:
    """
    Maintain local order book from WebSocket updates.

    Processes snapshots (full book initialisation) and updates (incremental changes).
    Removes price levels when quantity is 0.

    TODOs:
        - Add snapshot freshness checks
        - Investigate why zero-quantity updates reference non-existent price levels.
    """
    # TODO: Add checks for most up to date snapshot. Happy path is ID_{snapshot} < Upd_{first}
    if event_type == "snapshot":
        # Start orderbook updates from snapshot sequence number
        orderbook_sequence_num = event_sequence_num
        logger.info("Initialising order book with snapshot, event_seq=%s", orderbook_sequence_num)
        # Bulk initialise snapshot - more efficient than individual inserts
        bid_items = []
        ask_items = []

        for update in updates:
            price = float(update["price_level"])
            quantity = float(update["new_quantity"])

            if update["side"] == "bid":
                bid_items.append((price, quantity))
            else:
                ask_items.append((price, quantity))

        bids.update(bid_items)
        asks.update(ask_items)

    else:  # event_type == "update"
        if event_sequence_num <= orderbook_sequence_num:
            logger.warning("Received a stale order book update: seq=%s <= last_seq=%s", event_sequence_num, orderbook_sequence_num)
            return bids, asks, orderbook_sequence_num, True

        if event_sequence_num != orderbook_sequence_num + 1:
            logger.error(
                "CRITICAL GAP DETECTED! expected_seq=%s, received_seq=%s. MUST RE-SNAPSHOT.", orderbook_sequence_num + 1, event_sequence_num
            )
            return bids, asks, orderbook_sequence_num, False

        for update in updates:
            price = float(update["price_level"])
            quantity = float(update["new_quantity"])
            side = update["side"]

            if side == "bid":
                if quantity == 0.0:
                    # Using pop as we are seeing cases where quantity set to 0.0 but price level not in the orderbook.
                    # TODO: Check what the cause of this issue could be.
                    bids.pop(price, None)
                else:
                    bids[price] = quantity
            else:
                if quantity == 0.0:
                    asks.pop(price, None)
                else:
                    asks[price] = quantity

        orderbook_sequence_num = event_sequence_num

    return bids, asks, orderbook_sequence_num, True


async def websocket_listener() -> None:
    # Generate unique connection ID for this WebSocket session
    connection_id = uuid.uuid4()
    logger.info("Starting new connection session: %s", connection_id)

    subscribe_message = json.dumps({"type": "subscribe", "channel": CHANNEL, "product_ids": [PRODUCT_ID]})

    conn = None
    websocket = None
    bids = None
    asks = None

    try:
        # Connect to PostgreSQL
        conn = await asyncpg.connect(user=DB_USER, database=DB_NAME, password=DB_PASSWORD)
        logger.info("Connected to PostgreSQL")

        # Connect to Coinbase WebSocket
        logger.info("Connecting to %s...", COINBASE_WEBSOCKET_URL)
        async with websockets.connect(COINBASE_WEBSOCKET_URL, max_size=None, ping_interval=None) as websocket:
            logger.info("Connected to Coinbase WebSocket")

            # Subscribe to channel
            await websocket.send(subscribe_message)
            logger.info("Subscribed to %s channel for %s", CHANNEL, PRODUCT_ID)

            message_count = 0
            # Initialise order book with SortedDict
            # Bids: highest to lowest (negative key)
            # Asks: lowest to highest
            bids = SortedDict(neg)
            asks = SortedDict()
            orderbook_sequence_num = -1

            while True:
                # Receive next message
                response = await websocket.recv()
                json_response = json.loads(response)

                event_sequence_num = json_response["sequence_num"]

                # Handle subscription acknowledgement
                if json_response.get("channel") == "subscriptions":
                    logger.info("Subscription confirmed: %s", json_response)
                    orderbook_sequence_num = event_sequence_num
                    continue

                events = json_response["events"]
                updates = events[0]["updates"]
                event_type = events[0]["type"]

                # Process all messages
                bids, asks, orderbook_sequence_num, is_success = await local_order_book(
                    event_type, event_sequence_num, orderbook_sequence_num, updates, bids=bids, asks=asks
                )

                if not is_success:
                    # Gap detected: break the loop, forcing a clean restart/reconnect
                    logger.error("Order book corrupted due to gap. Restarting WebSocket connection.")
                    break  # Will exit the 'async with websockets.connect' block and restart/crash the outer function

                # Insert event into database
                await insert_raw_event(conn, connection_id, json_response)

                message_count += 1
                if message_count % 100 == 0:
                    logger.info("Processed %s messages", message_count)

    except ConnectionClosedOK as e:
        logger.info("WebSocket closed normally: %s", e)

    except ConnectionClosedError as e:
        logger.error("WebSocket closed with error: %s", e)

    except Exception as e:
        logger.exception("Unexpected error: %s: %s", type(e).__name__, e)
        raise

    finally:
        # Save order book snapshot before closing
        if conn and (bids and asks):
            try:
                await delete_existing_snapshots(conn)
                await insert_orderbook_snapshot(conn, bids, asks)
            except Exception as e:
                logger.error("Failed to save order book snapshot: %s", e)

        # Clean up connections
        if conn:
            await conn.close()
            logger.info("PostgreSQL connection closed")

        if bids:
            # Display order book
            logger.info("BIDS (highest to lowest):")
            for price, qty in list(bids.items())[:10]:
                logger.info("  %s: %s", price, qty)
        if asks:
            logger.info("ASKS (lowest to highest):")
            for price, qty in list(asks.items())[:10]:
                logger.info("  %s: %s", price, qty)


async def delete_existing_snapshots(conn: asyncpg.connection.Connection) -> None:
    """Delete existing order book snapshots from database."""
    await conn.execute("DELETE FROM bid_orderbook_snapshot")
    await conn.execute("DELETE FROM ask_orderbook_snapshot")
    logger.info("Cleared existing order book snapshots from database")


async def insert_orderbook_snapshot(conn: asyncpg.connection.Connection, bids: SortedDict, asks: SortedDict) -> None:
    """Insert current order book snapshot into database."""
    try:
        # Insert bids
        bid_records = [(i + 1, price, quantity) for i, (price, quantity) in enumerate(bids.items())]
        await conn.executemany("INSERT INTO bid_orderbook_snapshot (id, price, quantity) VALUES ($1, $2, $3)", bid_records)
        logger.info("Inserted %s bid levels", len(bid_records))

        # Insert asks
        ask_records = [(i + 1, price, quantity) for i, (price, quantity) in enumerate(asks.items())]
        await conn.executemany("INSERT INTO ask_orderbook_snapshot (id, price, quantity) VALUES ($1, $2, $3)", ask_records)
        logger.info("Inserted %s ask levels", len(ask_records))

        logger.info("Order book snapshot saved to database")
    except Exception as e:
        logger.error("Error saving order book snapshot: %s", e)


async def unsubscribe(websocket: websockets.ClientConnection) -> None:
    """Unsubscribe from WebSocket channel before closing."""
    unsubscribe_message = {"type": "unsubscribe", "product_ids": [PRODUCT_ID], "channel": CHANNEL}
    await websocket.send(json.dumps(unsubscribe_message))
    logger.info("Unsubscribed from %s %s channel", PRODUCT_ID, CHANNEL)


async def main_loop() -> None:
    # Main loop to manage WebSocket connection with automatic reconnection
    while True:
        try:
            await websocket_listener()
        except Exception as e:
            logger.error("WebSocket listener failed with unexpected error: %s", e)

        sleep_seconds = 3
        logger.info("Waiting %s seconds before attempting reconnect.", sleep_seconds)
        await asyncio.sleep(sleep_seconds)


if __name__ == "__main__":
    setup_logging(level="INFO")

    try:
        asyncio.run(main_loop())

    except KeyboardInterrupt:
        logger.info("Shutting down gracefully...")
