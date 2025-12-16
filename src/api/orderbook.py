from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from src.analytics.engine import AnalyticsEngine
from src.api.dependencies import get_analytics_engine
from src.api.responses import OrderbookLevelResponse, OrderbookSnapshot

router = APIRouter(prefix="/orderbook", tags=["orderbook"])


@router.get("/snapshot", response_model=OrderbookSnapshot)
async def get_orderbook_snapshot(
    engine: Annotated[AnalyticsEngine, Depends(get_analytics_engine)],
    depth: int = Query(default=10, ge=1, le=100, description="Number of levels to return"),
) -> OrderbookSnapshot:
    """
    Get current orderbook snapshot.

    Returns top N price levels for bids and asks.
    """
    if engine.orderbook is None:
        raise HTTPException(status_code=503, detail="Analytics engine not initialised")

    if not engine.orderbook.initialised:
        raise HTTPException(status_code=503, detail="Orderbook snapshot not yet received")

    orderbook = engine.orderbook

    # Get top N levels
    bid_levels = [OrderbookLevelResponse(price=price, size=size) for price, size in list(orderbook.bids.items())[:depth]]
    ask_levels = [OrderbookLevelResponse(price=price, size=size) for price, size in list(orderbook.asks.items())[:depth]]

    analytics = orderbook.get_analytics()

    return OrderbookSnapshot(
        product_id=orderbook.product_id,
        timestamp=analytics.timestamp,
        bids=bid_levels,
        asks=ask_levels,
        best_bid=analytics.best_bid,
        best_ask=analytics.best_ask,
        spread=analytics.spread,
        midprice=analytics.midprice,
    )


@router.get("/bids", response_model=list[OrderbookLevelResponse])
async def get_bids(
    engine: Annotated[AnalyticsEngine, Depends(get_analytics_engine)],
    depth: int = Query(default=10, ge=1, le=100, description="Number of levels to return"),
) -> list[OrderbookLevelResponse]:
    if engine.orderbook is None:
        raise HTTPException(status_code=503, detail="Analytics engine not initialised")

    if not engine.orderbook.initialised:
        raise HTTPException(status_code=503, detail="Orderbook snapshot not yet received")

    orderbook = engine.orderbook
    bid_levels = [OrderbookLevelResponse(price=price, size=size) for price, size in list(orderbook.bids.items())[:depth]]

    return bid_levels


@router.get("/asks", response_model=list[OrderbookLevelResponse])
async def get_asks(
    engine: Annotated[AnalyticsEngine, Depends(get_analytics_engine)],
    depth: int = Query(default=10, ge=1, le=100, description="Number of levels to return"),
) -> list[OrderbookLevelResponse]:
    if engine.orderbook is None:
        raise HTTPException(status_code=503, detail="Analytics engine not initialised")

    if not engine.orderbook.initialised:
        raise HTTPException(status_code=503, detail="Orderbook snapshot not yet received")

    orderbook = engine.orderbook
    ask_levels = [OrderbookLevelResponse(price=price, size=size) for price, size in list(orderbook.asks.items())[:depth]]

    return ask_levels
