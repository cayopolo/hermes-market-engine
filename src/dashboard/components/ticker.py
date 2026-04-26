from __future__ import annotations

from dash import html


def ticker_panel() -> html.Div:
    return html.Div(
        className="panel ticker-panel",
        children=[html.Div("Price Ticker", className="panel-header"), html.Div(id="ticker-content", className="ticker-grid")],
    )
