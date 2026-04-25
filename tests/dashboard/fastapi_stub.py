"""Canned FastAPI stub for dashboard E2E testing.

Usage:
    uv run python -m tests.dashboard.fastapi_stub --port 8001
"""

import argparse
from datetime import UTC, datetime

import uvicorn
from fastapi import FastAPI

app = FastAPI(title="Hermes Stub")

TIMESTAMP = datetime.now(UTC).isoformat()
PRODUCTS = ["ETH-EUR", "XRP-USD"]


@app.get("/analytics/products")
def products() -> list[str]:
    return PRODUCTS


@app.get("/analytics/current/{product_id}")
def current(product_id: str) -> dict:
    return {
        "product_id": product_id,
        "timestamp": TIMESTAMP,
        "best_bid": 2500.50,
        "best_ask": 2500.75,
        "spread": 0.25,
        "midprice": 2500.625,
        "imbalance": 0.12,
        "volume_adjusted_midprice": 2500.60,
        "volume_adjusted_midprice_n": 2500.58,
    }


@app.get("/analytics/midprice/{product_id}")
def midprice(product_id: str) -> dict:
    return {"product_id": product_id, "timestamp": TIMESTAMP, "midprice": 2500.625}


@app.get("/analytics/spread/{product_id}")
def spread(product_id: str) -> dict:
    return {"product_id": product_id, "timestamp": TIMESTAMP, "spread": 0.25}


@app.get("/analytics/imbalance/{product_id}")
def imbalance(product_id: str) -> dict:
    return {"product_id": product_id, "timestamp": TIMESTAMP, "imbalance": 0.12}


@app.get("/analytics/vamp/{product_id}")
def vamp(product_id: str) -> dict:
    return {"product_id": product_id, "timestamp": TIMESTAMP, "vamp": 2500.60}


@app.get("/analytics/vamp_n/{product_id}")
def vamp_n(product_id: str, depth_percent: float = 1.0) -> dict:
    return {"product_id": product_id, "timestamp": TIMESTAMP, "vamp_n": 2500.58, "depth_percent": depth_percent}


@app.get("/orderbook/snapshot/{product_id}")
def orderbook_snapshot(product_id: str, depth: int = 10) -> dict:
    bids = [{"price": 2500.50 - i * 0.25, "size": 1.0 + i * 0.1} for i in range(depth)]
    asks = [{"price": 2500.75 + i * 0.25, "size": 1.0 + i * 0.1} for i in range(depth)]
    return {
        "product_id": product_id,
        "timestamp": TIMESTAMP,
        "bids": bids,
        "asks": asks,
        "best_bid": 2500.50,
        "best_ask": 2500.75,
        "spread": 0.25,
        "midprice": 2500.625,
    }


@app.get("/health")
def health() -> dict:
    return {"status": "healthy", "analytics": "running", "redis": "connected", "postgres": "connected"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8001)
    args = parser.parse_args()
    uvicorn.run(app, host="127.0.0.1", port=args.port)
