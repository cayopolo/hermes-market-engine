import logging
from typing import Annotated

from fastapi import APIRouter, Depends

from .dependencies import check_analytics_status, check_database_connection, check_redis_connection
from .responses import HealthResponse, ServiceStatus

router = APIRouter(tags=["health"])
logger = logging.getLogger(__name__)


@router.get("/health", response_model=HealthResponse)
async def health_check(
    analytics_status: Annotated[ServiceStatus, Depends(check_analytics_status)],
    redis_status: Annotated[ServiceStatus, Depends(check_redis_connection)],
    postgres_status: Annotated[ServiceStatus, Depends(check_database_connection)],
) -> HealthResponse:
    """
    Check health of all system components.

    Returns status of analytics engine, Redis, and PostgreSQL.
    """
    # Overall status is healthy only if all services are operational
    all_healthy = (
        analytics_status in (ServiceStatus.RUNNING, ServiceStatus.STOPPED)
        and redis_status == ServiceStatus.CONNECTED
        and postgres_status == ServiceStatus.CONNECTED
    )

    return HealthResponse(
        status="healthy" if all_healthy else "degraded", analytics=analytics_status, redis=redis_status, postgres=postgres_status
    )
