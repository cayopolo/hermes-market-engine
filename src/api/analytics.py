from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from src.analytics.engine import AnalyticsEngine
from src.api.dependencies import get_analytics_engine
from src.api.responses import AnalyticsResponse

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/products", response_model=list[str])
async def get_available_products(engine: Annotated[AnalyticsEngine, Depends(get_analytics_engine)]) -> list[str]:
    """Get list of configured product IDs"""
    if engine.orderbooks is None:
        raise HTTPException(status_code=503, detail="Analytics engine not initialised")
    return list(engine.orderbooks.keys())


@router.get("/current/{product_id}", response_model=AnalyticsResponse)
async def get_current_analytics(product_id: str, engine: Annotated[AnalyticsEngine, Depends(get_analytics_engine)]) -> AnalyticsResponse:
    """Fetch the current analytics snapshot"""

    if engine.orderbooks is None:
        raise HTTPException(status_code=503, detail="Analytics engine not initialised")

    if product_id not in engine.orderbooks:
        raise HTTPException(status_code=404, detail=f"Product '{product_id}' not found")

    if not engine.orderbooks[product_id].initialised:
        raise HTTPException(status_code=503, detail="Orderbook snapshot not yet received")

    analytics = engine.orderbooks[product_id].get_analytics()
    return AnalyticsResponse(**analytics.model_dump())


@router.get("/midprice/{product_id}", response_model=dict)
async def get_midprice(product_id: str, engine: Annotated[AnalyticsEngine, Depends(get_analytics_engine)]) -> dict:
    """Get current mid-price (average of best bid and ask)."""
    if engine.orderbooks is None:
        raise HTTPException(status_code=503, detail="Not ready")

    if product_id not in engine.orderbooks:
        raise HTTPException(status_code=404, detail=f"Product '{product_id}' not found")

    if not engine.orderbooks[product_id].initialised:
        raise HTTPException(status_code=503, detail="Not ready")

    midprice = engine.orderbooks[product_id].midprice()
    return {"product_id": engine.orderbooks[product_id].product_id, "timestamp": datetime.now(UTC), "midprice": midprice}


@router.get("/spread/{product_id}", response_model=dict)
async def get_spread(product_id: str, engine: Annotated[AnalyticsEngine, Depends(get_analytics_engine)]) -> dict:
    """Get current bid-ask spread."""
    if engine.orderbooks is None:
        raise HTTPException(status_code=503, detail="Not ready")

    if product_id not in engine.orderbooks:
        raise HTTPException(status_code=404, detail=f"Product '{product_id}' not found")

    if not engine.orderbooks[product_id].initialised:
        raise HTTPException(status_code=503, detail="Not ready")

    spread = engine.orderbooks[product_id].spread()
    return {"product_id": engine.orderbooks[product_id].product_id, "timestamp": datetime.now(UTC), "spread": spread}


@router.get("/imbalance/{product_id}", response_model=dict)
async def get_imbalance(product_id: str, engine: Annotated[AnalyticsEngine, Depends(get_analytics_engine)]) -> dict:
    """Get current order book imbalance.

    Imbalance = (sum of bid quantities - sum of ask quantities) / (sum of bid quantities + sum of ask quantities)

    Returns a value between -1 and 1, where positive indicates more bid volume.
    """
    if engine.orderbooks is None:
        raise HTTPException(status_code=503, detail="Not ready")

    if product_id not in engine.orderbooks:
        raise HTTPException(status_code=404, detail=f"Product '{product_id}' not found")

    if not engine.orderbooks[product_id].initialised:
        raise HTTPException(status_code=503, detail="Not ready")

    imbalance = engine.orderbooks[product_id].imbalance()
    return {"product_id": engine.orderbooks[product_id].product_id, "timestamp": datetime.now(UTC), "imbalance": imbalance}


@router.get("/vamp/{product_id}", response_model=dict)
async def get_vamp(product_id: str, engine: Annotated[AnalyticsEngine, Depends(get_analytics_engine)]) -> dict:
    """Get volume-adjusted midprice (best bid/ask only).

    VAMP = (P_best_bid x Q_best_ask + P_best_ask x Q_best_bid) / (Q_best_bid + Q_best_ask)

    Prices and quantities are cross-multiplied between bid and ask sides.
    """
    if engine.orderbooks is None:
        raise HTTPException(status_code=503, detail="Not ready")

    if product_id not in engine.orderbooks:
        raise HTTPException(status_code=404, detail=f"Product '{product_id}' not found")

    if not engine.orderbooks[product_id].initialised:
        raise HTTPException(status_code=503, detail="Not ready")

    vamp = engine.orderbooks[product_id].volume_adjusted_midprice()
    if vamp is None:
        raise HTTPException(status_code=503, detail="Unable to calculate VAMP")

    return {"product_id": engine.orderbooks[product_id].product_id, "timestamp": datetime.now(UTC), "vamp": vamp}


@router.get("/vamp_n/{product_id}", response_model=dict)
async def get_vamp_n(
    product_id: str, engine: Annotated[AnalyticsEngine, Depends(get_analytics_engine)], depth_percent: float = 1.0
) -> dict:
    """Get volume-adjusted midprice with n% market depth.

    Aggregates quantities within n% of the midprice on each side, then applies VAMP formula.
    For 1% market depth: bid side from mid x 0.99 to mid, ask side from mid to mid x 1.01

    Args:
        depth_percent: Percentage depth (default 1.0 for 1% market depth)
    """
    if engine.orderbooks is None:
        raise HTTPException(status_code=503, detail="Not ready")

    if product_id not in engine.orderbooks:
        raise HTTPException(status_code=404, detail=f"Product '{product_id}' not found")

    if not engine.orderbooks[product_id].initialised:
        raise HTTPException(status_code=503, detail="Not ready")

    vamp_n = engine.orderbooks[product_id].volume_adjusted_midprice_n(depth_percent)
    if vamp_n is None:
        raise HTTPException(status_code=503, detail="Unable to calculate VAMP_n")

    return {
        "product_id": engine.orderbooks[product_id].product_id,
        "timestamp": datetime.now(UTC),
        "vamp_n": vamp_n,
        "depth_percent": depth_percent,
    }
