from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


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
