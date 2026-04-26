from __future__ import annotations

from dash import Dash, Input, Output, State, callback, dcc, html, no_update

import src.dashboard.callbacks.charts
import src.dashboard.callbacks.data_store
import src.dashboard.callbacks.orderbook
import src.dashboard.callbacks.ticker  # noqa: F401
from src.dashboard.api_client import fetch_products
from src.dashboard.components.charts import charts_row
from src.dashboard.components.imbalance import imbalance_panel
from src.dashboard.components.orderbook import orderbook_panels
from src.dashboard.components.ticker import ticker_panel


def create_app() -> Dash:
    app = Dash(__name__, title="Hermes Trading Dashboard", update_title=None)

    app.layout = html.Div(
        [
            # -- stores --
            dcc.Store(id="current-store", storage_type="memory"),
            dcc.Store(id="timeseries-store", storage_type="memory", data={}),
            dcc.Store(id="api-status", storage_type="memory", data="ok"),
            dcc.Interval(id="poll-interval", interval=2000, n_intervals=0),
            dcc.Interval(id="products-interval", interval=5000, n_intervals=0),
            # -- header --
            html.Div(
                className="header",
                children=[
                    html.H1("Hermes Trading Dashboard"),
                    html.Div(
                        className="product-selector",
                        children=[dcc.Dropdown(id="product-selector", placeholder="Select product...", clearable=False)],
                    ),
                ],
            ),
            # -- api error banner --
            html.Div(id="api-error-banner", className="api-error-banner", style={"display": "none"}),
            # -- main content --
            html.Div(
                className="main-content",
                children=[
                    html.Div(className="row row-top", children=[ticker_panel(), imbalance_panel()]),
                    orderbook_panels(),
                    charts_row(),
                ],
            ),
            # -- status bar --
            html.Div(id="last-updated", className="status-bar", children="Waiting for data..."),
        ]
    )

    return app


@callback(
    Output("product-selector", "options"),
    Output("product-selector", "value"),
    Input("products-interval", "n_intervals"),
    State("product-selector", "value"),
)
def refresh_products(_n: int, current_value: str | None) -> tuple:
    products = fetch_products()
    if not products:
        return no_update, no_update
    options = [{"label": p, "value": p} for p in products]
    value = current_value if current_value in products else products[0]
    return options, value


@callback(Output("poll-interval", "disabled"), Input("product-selector", "value"))
def toggle_poll_interval(value: str | None) -> bool:
    return value is None


@callback(Output("api-error-banner", "style"), Output("api-error-banner", "children"), Input("api-status", "data"))
def update_error_banner(status: str | None) -> tuple:
    if status == "error":
        return {"display": "block"}, "API unreachable — retrying every 2s"
    return {"display": "none"}, ""


app = create_app()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8050)  # noqa: S104
