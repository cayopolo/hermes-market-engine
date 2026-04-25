from src.logging_config import get_logger

logger = get_logger(__name__)


# TODO: add psycopg3 dep and implement
def fetch_midprice_history(product_id: str, start: str, end: str, bucket: str) -> list[dict]:  # noqa: ARG001
    logger.warning("db_client.fetch_midprice_history: not yet implemented (stub)")
    return []


# TODO: add psycopg3 dep and implement
def fetch_spread_history(product_id: str, start: str, end: str, bucket: str) -> list[dict]:  # noqa: ARG001
    logger.warning("db_client.fetch_spread_history: not yet implemented (stub)")
    return []
