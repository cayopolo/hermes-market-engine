from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

BASE_URL = "http://localhost:8000"
TIMEOUT = 5.0


def _get(path: str, params: dict[str, Any] | None = None) -> Any | None:  # noqa: ANN401
    try:
        resp = httpx.get(f"{BASE_URL}{path}", params=params, timeout=TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except (httpx.ConnectError, httpx.TimeoutException):
        logger.debug("API unreachable: %s", path)
        return None
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 503:
            logger.debug("API warming up: %s", path)
            return None
        logger.warning("API error %s for %s", exc.response.status_code, path)
        return None


def fetch_products() -> list[str]:
    data = _get("/analytics/products")
    return data if isinstance(data, list) else []


def fetch_analytics(product_id: str) -> dict[str, Any] | None:
    return _get(f"/analytics/current/{product_id}")


def fetch_orderbook(product_id: str, depth: int = 20) -> dict[str, Any] | None:
    return _get(f"/orderbook/snapshot/{product_id}", params={"depth": depth})
