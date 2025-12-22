from datetime import UTC, datetime
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


@router.get("/midprice", response_model=dict)
async def get_midprice(engine: Annotated[AnalyticsEngine, Depends(get_analytics_engine)]) -> dict:
    """Get current mid-price (average of best bid and ask)."""
    if engine.orderbook is None or not engine.orderbook.initialised:
        raise HTTPException(status_code=503, detail="Not ready")

    midprice = engine.orderbook.midprice()
    return {"product_id": engine.orderbook.product_id, "timestamp": datetime.now(UTC), "midprice": midprice}


@router.get("/spread", response_model=dict)
async def get_spread(engine: Annotated[AnalyticsEngine, Depends(get_analytics_engine)]) -> dict:
    """Get current bid-ask spread."""
    if engine.orderbook is None or not engine.orderbook.initialised:
        raise HTTPException(status_code=503, detail="Not ready")

    spread = engine.orderbook.spread()
    return {"product_id": engine.orderbook.product_id, "timestamp": datetime.now(UTC), "spread": spread}


@router.get("/imbalance", response_model=dict)
async def get_imbalance(engine: Annotated[AnalyticsEngine, Depends(get_analytics_engine)]) -> dict:
    """Get current order book imbalance.

    Imbalance = (sum of bid quantities - sum of ask quantities) / (sum of bid quantities + sum of ask quantities)

    Returns a value between -1 and 1, where positive indicates more bid volume.
    """
    if engine.orderbook is None or not engine.orderbook.initialised:
        raise HTTPException(status_code=503, detail="Not ready")

    imbalance = engine.orderbook.imbalance()
    return {"product_id": engine.orderbook.product_id, "timestamp": datetime.now(UTC), "imbalance": imbalance}


@router.get("/vamp", response_model=dict)
async def get_vamp(engine: Annotated[AnalyticsEngine, Depends(get_analytics_engine)]) -> dict:
    """Get volume-adjusted midprice (best bid/ask only).

    VAMP = (P_best_bid x Q_best_ask + P_best_ask x Q_best_bid) / (Q_best_bid + Q_best_ask)

    Prices and quantities are cross-multiplied between bid and ask sides.
    """
    if engine.orderbook is None or not engine.orderbook.initialised:
        raise HTTPException(status_code=503, detail="Not ready")

    vamp = engine.orderbook.volume_adjusted_midprice()
    if vamp is None:
        raise HTTPException(status_code=503, detail="Unable to calculate VAMP")

    return {"product_id": engine.orderbook.product_id, "timestamp": datetime.now(UTC), "vamp": vamp}


@router.get("/vamp_n", response_model=dict)
async def get_vamp_n(engine: Annotated[AnalyticsEngine, Depends(get_analytics_engine)], depth_percent: float = 1.0) -> dict:
    """Get volume-adjusted midprice with n% market depth.

    Aggregates quantities within n% of the midprice on each side, then applies VAMP formula.
    For 1% market depth: bid side from mid x 0.99 to mid, ask side from mid to mid x 1.01

    Args:
        depth_percent: Percentage depth (default 1.0 for 1% market depth)
    """
    if engine.orderbook is None or not engine.orderbook.initialised:
        raise HTTPException(status_code=503, detail="Not ready")

    vamp_n = engine.orderbook.volume_adjusted_midprice_n(depth_percent)
    if vamp_n is None:
        raise HTTPException(status_code=503, detail="Unable to calculate VAMP_n")

    return {"product_id": engine.orderbook.product_id, "timestamp": datetime.now(UTC), "vamp_n": vamp_n, "depth_percent": depth_percent}
