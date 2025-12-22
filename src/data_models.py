from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class CoinbaseUpdate(BaseModel):
    """Single update from Coinbase level2 channel"""

    side: Literal["bid", "offer"]
    event_time: datetime
    price_level: float
    new_quantity: float


class CoinbaseEvent(BaseModel):
    """Single event in the events array"""

    type: Literal["snapshot", "update"]
    product_id: str
    updates: list[CoinbaseUpdate]


class CoinbaseMessage(BaseModel):
    """Complete message from Coinbase WebSocket"""

    channel: str
    sequence_num: int
    timestamp: datetime
    events: list[CoinbaseEvent]


class HotPathPacket(BaseModel):
    """Wrapper for hot path transmission with metadata"""

    ts_ingest: float  # Unix timestamp when received
    connection_id: str
    payload: CoinbaseMessage


class Analytics(BaseModel):
    """Computed analytics snapshot"""

    product_id: str
    timestamp: datetime
    best_bid: float | None
    best_ask: float | None
    spread: float | None
    midprice: float | None
    imbalance: float | None
    volume_adjusted_midprice: float | None
    volume_adjusted_midprice_n: float | None
