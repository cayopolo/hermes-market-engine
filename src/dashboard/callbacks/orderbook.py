from __future__ import annotations

from itertools import accumulate

import plotly.graph_objects as go
from dash import Input, Output, callback, no_update

_DARK_BG = "#1c2128"
_GRID = "#30363d"


@callback(Output("depth-chart", "figure"), Output("orderbook-ladder", "rowData"), Input("current-store", "data"), prevent_initial_call=True)
def update_orderbook(current: dict | None) -> tuple:
    if not current or not current.get("orderbook"):
        return no_update, no_update

    ob = current["orderbook"]
    return _depth_figure(ob), _ladder_rows(ob)


def _depth_figure(ob: dict) -> go.Figure:
    bids = ob.get("bids", [])
    asks = ob.get("asks", [])
    midprice = ob.get("midprice")

    fig = go.Figure()

    if bids:
        fig.add_trace(
            go.Scatter(
                x=[b["price"] for b in bids],
                y=list(accumulate(b["size"] for b in bids)),
                fill="tozeroy",
                fillcolor="rgba(63, 185, 80, 0.2)",
                line={"color": "#3fb950", "width": 1.5},
                name="Bids",
                hovertemplate="Price: %{x:.2f}<br>Cum Vol: %{y:.4f}<extra></extra>",
            )
        )

    if asks:
        fig.add_trace(
            go.Scatter(
                x=[a["price"] for a in asks],
                y=list(accumulate(a["size"] for a in asks)),
                fill="tozeroy",
                fillcolor="rgba(248, 81, 73, 0.2)",
                line={"color": "#f85149", "width": 1.5},
                name="Asks",
                hovertemplate="Price: %{x:.2f}<br>Cum Vol: %{y:.4f}<extra></extra>",
            )
        )

    if midprice is not None:
        fig.add_vline(
            x=midprice,
            line_dash="dash",
            line_color="#58a6ff",
            line_width=1,
            annotation_text="Mid",
            annotation_font_color="#58a6ff",
            annotation_font_size=10,
        )

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor=_DARK_BG,
        plot_bgcolor=_DARK_BG,
        margin={"l": 50, "r": 20, "t": 10, "b": 40},
        xaxis={"title": "Price", "gridcolor": _GRID, "zeroline": False},
        yaxis={"title": "Cumulative Volume", "gridcolor": _GRID, "zeroline": False},
        legend={"orientation": "h", "y": 1.02, "x": 0.5, "xanchor": "center"},
        hovermode="x unified",
    )
    return fig


def _ladder_rows(ob: dict) -> list[dict]:
    bids = ob.get("bids", [])
    asks = ob.get("asks", [])
    rows: list[dict] = []
    for i in range(max(len(bids), len(asks), 1)):
        row: dict = {}
        if i < len(bids):
            row["bid_size"] = bids[i]["size"]
            row["bid_price"] = bids[i]["price"]
        if i < len(asks):
            row["ask_price"] = asks[i]["price"]
            row["ask_size"] = asks[i]["size"]
        rows.append(row)
    return rows
