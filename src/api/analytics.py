from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from src.analytics.engine import AnalyticsEngine
from src.api.dependencies import get_analytics_engine
from src.api.responses import AnalyticsResponse

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/current", response_model=AnalyticsResponse)
async def get_current_analytics(engine: Annotated[AnalyticsEngine, Depends(get_analytics_engine)]) -> AnalyticsResponse:
    """Fetch the current analytics snapshot"""

    if engine.orderbook is None:
        raise HTTPException(status_code=503, detail="Analytics engine not initialised")

    if not engine.orderbook.initialised:
        raise HTTPException(status_code=503, detail="Orderbook snapshot not yet received")

    analytics = engine.orderbook.get_analytics()
    return AnalyticsResponse(**analytics.model_dump())


@router.get("/spread", response_model=dict)
async def get_spread(engine: Annotated[AnalyticsEngine, Depends(get_analytics_engine)]) -> dict:
    """Get current bid-ask spread."""
    if engine.orderbook is None or not engine.orderbook.initialised:
        raise HTTPException(status_code=503, detail="Not ready")

    analytics = engine.orderbook.get_analytics()
    return {"product_id": analytics.product_id, "timestamp": analytics.timestamp, "spread": analytics.spread}


@router.get("/midprice", response_model=dict)
async def get_midprice(engine: Annotated[AnalyticsEngine, Depends(get_analytics_engine)]) -> dict:
    """Get current mid-price (average of best bid and ask)."""
    if engine.orderbook is None or not engine.orderbook.initialised:
        raise HTTPException(status_code=503, detail="Not ready")

    analytics = engine.orderbook.get_analytics()
    return {"product_id": analytics.product_id, "timestamp": analytics.timestamp, "midprice": analytics.midprice}
