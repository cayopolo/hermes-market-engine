from __future__ import annotations

from datetime import UTC, datetime

from dash import Input, Output, State, callback, no_update

from src.dashboard.api_client import fetch_analytics, fetch_orderbook

MAX_TIMESERIES_POINTS = 300


@callback(
    Output("current-store", "data"),
    Output("timeseries-store", "data"),
    Output("last-updated", "children"),
    Output("api-status", "data"),
    Input("poll-interval", "n_intervals"),
    State("product-selector", "value"),
    State("timeseries-store", "data"),
    prevent_initial_call=True,
)
def poll_api(_n_intervals: int, product_id: str | None, ts_data: dict | None) -> tuple:
    if not product_id:
        return no_update, no_update, no_update, no_update

    analytics = fetch_analytics(product_id)
    orderbook = fetch_orderbook(product_id, depth=20)

    if analytics is None and orderbook is None:
        return no_update, no_update, "API unreachable — retrying...", "error"

    now = datetime.now(UTC).isoformat()
    current = {"analytics": analytics, "orderbook": orderbook, "fetched_at": now}

    if not isinstance(ts_data, dict):
        ts_data = {}

    if analytics:
        product_ts = list(ts_data.get(product_id, []))
        product_ts.append(
            {
                "timestamp": analytics.get("timestamp", now),
                "midprice": analytics.get("midprice"),
                "best_bid": analytics.get("best_bid"),
                "best_ask": analytics.get("best_ask"),
                "spread": analytics.get("spread"),
                "imbalance": analytics.get("imbalance"),
                "vamp": analytics.get("volume_adjusted_midprice"),
                "vamp_n": analytics.get("volume_adjusted_midprice_n"),
            }
        )
        if len(product_ts) > MAX_TIMESERIES_POINTS:
            product_ts = product_ts[-MAX_TIMESERIES_POINTS:]
        ts_data = {**ts_data, product_id: product_ts}

    status = f"Last updated: {now[:19]}Z"
    return current, ts_data, status, "ok"
