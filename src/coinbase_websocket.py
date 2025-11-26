import asyncio
import json
import os
import uuid
from datetime import datetime
from pathlib import Path

import asyncpg
import websockets
from dotenv import load_dotenv
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


async def websocket_listener() -> None:
    # Generate unique connection ID for this WebSocket session
    connection_id = uuid.uuid4()
    print(f"Starting new connection session: {connection_id}")

    subscribe_message = json.dumps({"type": "subscribe", "channel": CHANNEL, "product_ids": [PRODUCT_ID]})

    conn = None
    websocket = None

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
            while True:
                # Receive next message
                response = await websocket.recv()
                json_response = json.loads(response)

                # Handle subscription acknowledgement
                if json_response.get("channel") == "subscriptions":
                    print(f"Subscription confirmed: {json_response}")
                    continue

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
