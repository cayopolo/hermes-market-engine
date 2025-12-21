from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field


class ServiceStatus(str, Enum):
    """Service health status values"""

    RUNNING = "running"
    STOPPED = "stopped"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    UNINITIALISED = "uninitialised"


class AnalyticsResponse(BaseModel):
    """Real-time orderbook analytics snapshot"""

    product_id: str
    timestamp: datetime
    best_bid: Decimal | None
    best_ask: Decimal | None
    spread: Decimal | None
    midprice: Decimal | None

    model_config = {
        "json_schema_extra": {
            "example": {
                "product_id": "ETH-EUR",
                "timestamp": "2025-12-15T10:30:45.123Z",
                "best_bid": "2500.50",
                "best_ask": "2500.75",
                "spread": "0.25",
                "midprice": "2500.625",
            }
        }
    }


class OrderbookLevelResponse(BaseModel):
    """Single level in orderbook (price, size)"""

    price: Decimal
    size: Decimal


class OrderbookSnapshot(BaseModel):
    """Complete orderbook state"""

    product_id: str
    timestamp: datetime
    bids: list[OrderbookLevelResponse] = Field(..., description="Sorted highest to lowest")
    asks: list[OrderbookLevelResponse] = Field(..., description="Sorted lowest to highest")
    best_bid: Decimal | None
    best_ask: Decimal | None
    spread: Decimal | None
    midprice: Decimal | None

    model_config = {
        "json_schema_extra": {
            "example": {
                "product_id": "ETH-EUR",
                "timestamp": "2025-12-15T10:30:45.123Z",
                "bids": [{"price": "2500.50", "size": "1.5"}, {"price": "2500.00", "size": "2.0"}],
                "asks": [{"price": "2500.75", "size": "1.0"}, {"price": "2501.00", "size": "2.5"}],
                "best_bid": "2500.50",
                "best_ask": "2500.75",
                "spread": "0.25",
                "midprice": "2500.625",
            }
        }
    }


class RawEvent(BaseModel):
    """Raw market event from database"""

    id: int
    sequence_num: int
    raw_message: dict

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": 12345,
                "sequence_num": 2,
                "raw_message": {
                    "events": [
                        {
                            "type": "update",
                            "updates": [
                                {
                                    "side": "bid",
                                    "event_time": "2025-12-16T10:50:13.415877Z",
                                    "price_level": "2509.24",
                                    "new_quantity": "0.33892332",
                                },
                                {
                                    "side": "offer",
                                    "event_time": "2025-12-16T10:50:13.415877Z",
                                    "price_level": "2509.75",
                                    "new_quantity": "0.33885526",
                                },
                                {
                                    "side": "offer",
                                    "event_time": "2025-12-16T10:50:13.415877Z",
                                    "price_level": "2523.74",
                                    "new_quantity": "0",
                                },
                            ],
                            "product_id": "ETH-EUR",
                        }
                    ],
                    "channel": "l2_data",
                    "timestamp": "2025-12-16T10:50:13.443296Z",
                    "sequence_num": 2,
                },
            }
        }
    }


class HealthResponse(BaseModel):
    """Health check response"""

    status: str
    analytics: ServiceStatus
    redis: ServiceStatus
    postgres: ServiceStatus

    model_config = {
        "json_schema_extra": {"example": {"status": "healthy", "analytics": "running", "redis": "connected", "postgres": "connected"}}
    }
