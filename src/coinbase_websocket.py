import asyncio
import json
import os
import uuid
from datetime import datetime
from operator import neg
from pathlib import Path

import asyncpg
import websockets
from dotenv import load_dotenv
from sortedcontainers import SortedDict
from websockets.exceptions import ConnectionClosedError, ConnectionClosedOK

load_dotenv()

DB_USER = os.getenv("DB_USER")
DB_NAME = os.getenv("DB_NAME")
DB_PASSWORD = os.getenv("DB_PASSWORD")


COINBASE_WEBSOCKET_URL = "wss://advanced-trade-ws.coinbase.com"
PRODUCT_ID = "XRP-USD"
CHANNEL = "level2"

OUTPUT_PATH = Path(f"{CHANNEL.lower()}_{PRODUCT_ID.lower()}.json")


async def insert_raw_event(conn: asyncpg.connection.Connection, connection_id: uuid.UUID, message: dict) -> None:
    """Insert raw WebSocket event into database with connection tracking."""
    # Extract event details - handle cases where events array might be empty
    events = message.get("events", [])
    if not events:
        print(f"Warning: Empty events array in message seq={message.get('sequence_num')}")
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
    event_type: str, updates: list[dict[str, str]], bids: SortedDict, asks: SortedDict
) -> tuple[SortedDict, SortedDict]:
    """
    Maintain local order book from WebSocket updates.

    Processes snapshots (full book initialisation) and updates (incremental changes).
    Removes price levels when quantity is 0.

    TODOs:
        - Add snapshot freshness checks
        - Implement gap detection via sequence_num
        - Investigate why zero-quantity updates reference non-existent price levels.
    """
    # TODO: Add checks for most up to date snapshot. Happy path is ID_{snapshot} < Upd_{first}
    if event_type == "snapshot":
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
        # TODO: Implement gap detection based on sequence_num
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

    return bids, asks


async def websocket_listener() -> None:
    # Generate unique connection ID for this WebSocket session
    connection_id = uuid.uuid4()
    print(f"Starting new connection session: {connection_id}")

    subscribe_message = json.dumps({"type": "subscribe", "channel": CHANNEL, "product_ids": [PRODUCT_ID]})

    conn = None
    websocket = None
    bids = None
    asks = None

    try:
        # Connect to PostgreSQL
        conn = await asyncpg.connect(user=DB_USER, database=DB_NAME, password=DB_PASSWORD)
        print("Connected to PostgreSQL")

        # Connect to Coinbase WebSocket
        print(f"Connecting to {COINBASE_WEBSOCKET_URL}...")
        async with websockets.connect(COINBASE_WEBSOCKET_URL, max_size=None, ping_interval=None) as websocket:
            print("Connected to Coinbase WebSocket")

            # Subscribe to channel
            await websocket.send(subscribe_message)
            print(f"Subscribed to {CHANNEL} channel for {PRODUCT_ID}")

            message_count = 0
            # Initialise order book with SortedDict
            # Bids: highest to lowest (negative key)
            # Asks: lowest to highest
            bids = SortedDict(neg)
            asks = SortedDict()

            while True:
                # Receive next message
                response = await websocket.recv()
                json_response = json.loads(response)

                # Handle subscription acknowledgement
                if json_response.get("channel") == "subscriptions":
                    print(f"Subscription confirmed: {json_response}")
                    continue

                # Process all messages
                events = json_response["events"]
                updates = events[0]["updates"]
                event_type = events[0]["type"]
                bids, asks = await local_order_book(event_type, updates, bids, asks)

                # Insert event into database
                await insert_raw_event(conn, connection_id, json_response)

                message_count += 1
                if message_count % 100 == 0:
                    print(f"Processed {message_count} messages")

    except ConnectionClosedOK as e:
        print(f"WebSocket closed normally: {e}")

    except ConnectionClosedError as e:
        print(f"WebSocket closed with error: {e}")

    except Exception as e:
        print(f"Unexpected error: {type(e).__name__}: {e}")
        raise

    finally:
        # Clean up connections
        if conn:
            await conn.close()
            print("\nPostgreSQL connection closed")

            if bids:
                # Display order book
                print("BIDS (highest to lowest):")
                for price, qty in list(bids.items())[:10]:
                    print(f"  {price}: {qty}")
            if asks:
                print("\nASKS (lowest to highest):")
                for price, qty in list(asks.items())[:10]:
                    print(f"  {price}: {qty}")


async def unsubscribe(websocket: websockets.ClientConnection) -> None:
    """Unsubscribe from WebSocket channel before closing."""
    unsubscribe_message = {"type": "unsubscribe", "product_ids": [PRODUCT_ID], "channel": CHANNEL}
    await websocket.send(json.dumps(unsubscribe_message))
    print(f"Unsubscribed from {PRODUCT_ID} {CHANNEL} channel")


if __name__ == "__main__":
    try:
        asyncio.run(websocket_listener())

    except KeyboardInterrupt:
        print("\n\nShutting down gracefully...")
