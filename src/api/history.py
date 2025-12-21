from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Query

from .db import db_service

router = APIRouter(prefix="/history", tags=["history"])


@router.get("/raw-events", response_model=list[dict])
async def get_raw_event_history(
    product_id: Annotated[str, Query(example="ETH-EUR")],
    start_time: Annotated[datetime, Query(example="2023-01-01T00:00:00Z")],
    end_time: Annotated[datetime, Query(example="2023-01-02T00:00:00Z")],
    event_type: str | None = Query(None, description="Filter by 'snapshot' or 'update'"),
    limit: int = Query(100, ge=1, le=1000),
) -> list[dict]:
    raw_events = await db_service.get_raw_events(product_id, start_time, end_time, event_type=event_type, limit=limit)
    return raw_events
