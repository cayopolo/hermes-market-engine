from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from src.analytics.engine import AnalyticsEngine
from src.api.dependencies import get_analytics_engine
from src.api.responses import OrderbookLevelResponse, OrderbookSnapshot

router = APIRouter(prefix="/orderbook", tags=["orderbook"])


@router.get("/snapshot/{product_id}", response_model=OrderbookSnapshot)
async def get_orderbook_snapshot(
    product_id: str,
    engine: Annotated[AnalyticsEngine, Depends(get_analytics_engine)],
    depth: int = Query(default=10, ge=1, le=100, description="Number of levels to return"),
) -> OrderbookSnapshot:
    """
    Get current orderbook snapshot.

    Returns top N price levels for bids and asks.
    """
    if engine.orderbooks is None:
        raise HTTPException(status_code=503, detail="Analytics engine not initialised")

    if product_id not in engine.orderbooks:
        raise HTTPException(status_code=404, detail=f"Product '{product_id}' not found")

    if not engine.orderbooks[product_id].initialised:
        raise HTTPException(status_code=503, detail="Orderbook snapshot not yet received")

    orderbook = engine.orderbooks[product_id]

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


@router.get("/bids/{product_id}", response_model=list[OrderbookLevelResponse])
async def get_bids(
    product_id: str,
    engine: Annotated[AnalyticsEngine, Depends(get_analytics_engine)],
    depth: int = Query(default=10, ge=1, le=100, description="Number of levels to return"),
) -> list[OrderbookLevelResponse]:
    if engine.orderbooks is None:
        raise HTTPException(status_code=503, detail="Analytics engine not initialised")

    if product_id not in engine.orderbooks:
        raise HTTPException(status_code=404, detail=f"Product '{product_id}' not found")

    if not engine.orderbooks[product_id].initialised:
        raise HTTPException(status_code=503, detail="Orderbook snapshot not yet received")

    orderbook = engine.orderbooks[product_id]
    bid_levels = [OrderbookLevelResponse(price=price, size=size) for price, size in list(orderbook.bids.items())[:depth]]

    return bid_levels


@router.get("/asks/{product_id}", response_model=list[OrderbookLevelResponse])
async def get_asks(
    product_id: str,
    engine: Annotated[AnalyticsEngine, Depends(get_analytics_engine)],
    depth: int = Query(default=10, ge=1, le=100, description="Number of levels to return"),
) -> list[OrderbookLevelResponse]:
    if engine.orderbooks is None:
        raise HTTPException(status_code=503, detail="Analytics engine not initialised")

    if product_id not in engine.orderbooks:
        raise HTTPException(status_code=404, detail=f"Product '{product_id}' not found")

    if not engine.orderbooks[product_id].initialised:
        raise HTTPException(status_code=503, detail="Orderbook snapshot not yet received")

    orderbook = engine.orderbooks[product_id]
    ask_levels = [OrderbookLevelResponse(price=price, size=size) for price, size in list(orderbook.asks.items())[:depth]]

    return ask_levels


@router.get("/depth/{product_id}", response_model=dict[str, int])
async def get_full_orderbook_depth(product_id: str, engine: Annotated[AnalyticsEngine, Depends(get_analytics_engine)]) -> dict[str, int]:
    """Get full orderbook depth (number of levels on bid and ask sides)"""
    if engine.orderbooks is None:
        raise HTTPException(status_code=503, detail="Analytics engine not initialised")

    if product_id not in engine.orderbooks:
        raise HTTPException(status_code=404, detail=f"Product '{product_id}' not found")

    if not engine.orderbooks[product_id].initialised:
        raise HTTPException(status_code=503, detail="Orderbook snapshot not yet received")
    return {"bid_levels": len(engine.orderbooks[product_id].bids), "ask_levels": len(engine.orderbooks[product_id].asks)}
