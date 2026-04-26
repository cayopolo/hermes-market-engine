from __future__ import annotations

import plotly.graph_objects as go
from dash import Input, Output, callback

_DARK_BG = "#1c2128"
_GRID = "#30363d"


def _base_layout(yaxis_title: str = "") -> dict:
    return {
        "template": "plotly_dark",
        "paper_bgcolor": _DARK_BG,
        "plot_bgcolor": _DARK_BG,
        "margin": {"l": 55, "r": 10, "t": 8, "b": 36},
        "xaxis": {"gridcolor": _GRID, "zeroline": False, "showticklabels": True, "tickfont": {"size": 10}},
        "yaxis": {"title": yaxis_title, "gridcolor": _GRID, "zeroline": False, "tickfont": {"size": 10}},
        "legend": {"orientation": "h", "y": 1.08, "x": 0.5, "xanchor": "center", "font": {"size": 10}},
        "hovermode": "x unified",
    }


def _empty_figure() -> go.Figure:
    fig = go.Figure()
    fig.update_layout(**_base_layout())
    return fig


@callback(
    Output("chart-midprice", "figure"),
    Output("chart-spread", "figure"),
    Output("chart-imbalance", "figure"),
    Input("timeseries-store", "data"),
    Input("product-selector", "value"),
    prevent_initial_call=True,
)
def update_charts(ts_data: dict | None, product_id: str | None) -> tuple:
    if not product_id or not isinstance(ts_data, dict):
        return _empty_figure(), _empty_figure(), _empty_figure()

    points = ts_data.get(product_id, [])
    if not points:
        return _empty_figure(), _empty_figure(), _empty_figure()

    timestamps = [p["timestamp"] for p in points]

    # --- midprice + vamp ---
    midprices = [p.get("midprice") for p in points]
    vamps = [p.get("vamp") for p in points]

    fig_mid = go.Figure()
    fig_mid.add_trace(
        go.Scatter(
            x=timestamps,
            y=midprices,
            name="Midprice",
            line={"color": "#58a6ff", "width": 1.5},
            hovertemplate="%{y:.2f}<extra>Mid</extra>",
        )
    )
    if any(v is not None for v in vamps):
        fig_mid.add_trace(
            go.Scatter(
                x=timestamps,
                y=vamps,
                name="VAMP",
                line={"color": "#d29922", "width": 1.5, "dash": "dot"},
                hovertemplate="%{y:.2f}<extra>VAMP</extra>",
            )
        )
    fig_mid.update_layout(**_base_layout("Price"))

    # --- spread ---
    spreads = [p.get("spread") for p in points]

    fig_spread = go.Figure()
    fig_spread.add_trace(
        go.Scatter(
            x=timestamps,
            y=spreads,
            name="Spread",
            fill="tozeroy",
            fillcolor="rgba(163, 113, 247, 0.15)",
            line={"color": "#a371f7", "width": 1.5},
            hovertemplate="%{y:.4f}<extra>Spread</extra>",
        )
    )
    fig_spread.update_layout(**_base_layout("Spread"))

    # --- imbalance with above/below zero fill ---
    raw_imb = [p.get("imbalance") for p in points]
    imbalances = [v if v is not None else 0.0 for v in raw_imb]
    pos = [max(0.0, v) for v in imbalances]
    neg = [min(0.0, v) for v in imbalances]

    fig_imb = go.Figure()
    fig_imb.add_trace(
        go.Scatter(
            x=timestamps,
            y=pos,
            fill="tozeroy",
            fillcolor="rgba(63, 185, 80, 0.25)",
            line={"color": "#3fb950", "width": 1},
            showlegend=False,
            hoverinfo="skip",
        )
    )
    fig_imb.add_trace(
        go.Scatter(
            x=timestamps,
            y=neg,
            fill="tozeroy",
            fillcolor="rgba(248, 81, 73, 0.25)",
            line={"color": "#f85149", "width": 1},
            showlegend=False,
            hoverinfo="skip",
        )
    )
    # single invisible trace for hover
    fig_imb.add_trace(
        go.Scatter(
            x=timestamps,
            y=imbalances,
            name="Imbalance",
            line={"color": "rgba(0,0,0,0)", "width": 0},
            hovertemplate="%{y:.4f}<extra>Imbalance</extra>",
        )
    )
    fig_imb.add_hline(y=0, line_color=_GRID, line_width=1)
    layout = _base_layout("Imbalance")
    layout["yaxis"]["range"] = [-1.05, 1.05]
    fig_imb.update_layout(**layout)

    return fig_mid, fig_spread, fig_imb
