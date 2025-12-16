import logging

from src.analytics.engine import AnalyticsEngine

logger = logging.getLogger(__name__)

# Global instances
_analytics_engine: AnalyticsEngine | None = None


async def get_analytics_engine() -> AnalyticsEngine:
    """Dependency injection for analytics engine"""
    if _analytics_engine is None:
        raise RuntimeError("Analytics engine not initialised")
    return _analytics_engine


def set_analytics_engine(engine: AnalyticsEngine) -> None:
    """Set global analytics engine instance"""
    global _analytics_engine
    _analytics_engine = engine
    logger.info("Analytics engine dependency set")
