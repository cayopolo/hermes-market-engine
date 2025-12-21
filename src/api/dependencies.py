import logging

from src.analytics.engine import AnalyticsEngine

from .db import db_service
from .responses import ServiceStatus

logger = logging.getLogger(__name__)

# Global instances
_analytics_engine: AnalyticsEngine | None = None


async def get_analytics_engine() -> AnalyticsEngine:
    """Dependency injection for analytics engine"""
    if _analytics_engine is None:
        raise RuntimeError("Analytics engine not initialised")
    return _analytics_engine


async def check_analytics_status() -> ServiceStatus:
    """Check analytics engine status"""
    if _analytics_engine is None:
        return ServiceStatus.UNINITIALISED
    return ServiceStatus.RUNNING if _analytics_engine.should_run else ServiceStatus.STOPPED


async def check_redis_connection() -> ServiceStatus:
    """Dependency injection for checking Redis connection"""
    if _analytics_engine is None:
        return ServiceStatus.UNINITIALISED
    if _analytics_engine.pubsub is None:
        return ServiceStatus.DISCONNECTED
    try:
        await _analytics_engine.pubsub.check_health()
        return ServiceStatus.CONNECTED
    except Exception:
        return ServiceStatus.DISCONNECTED


async def check_database_connection() -> ServiceStatus:
    """Dependency injection for checking Database connection"""
    if db_service.pool is None:
        return ServiceStatus.DISCONNECTED

    try:
        async with db_service.pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        return ServiceStatus.CONNECTED
    except Exception as e:
        logger.error("PostgreSQL check failed: %s", e)
        return ServiceStatus.ERROR


def set_analytics_engine(engine: AnalyticsEngine) -> None:
    """Set global analytics engine instance"""
    global _analytics_engine
    _analytics_engine = engine
    logger.info("Analytics engine dependency set")
