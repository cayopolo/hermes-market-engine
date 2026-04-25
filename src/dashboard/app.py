import dash
import dash_bootstrap_components as dbc

from src.dashboard import registry
from src.dashboard.layout import build_root_layout
from src.logging_config import get_logger

logger = get_logger(__name__)


def create_app() -> dash.Dash:
    app = dash.Dash(__name__, external_stylesheets=[dbc.themes.DARKLY], suppress_callback_exceptions=True, title="Hermes Dashboard")

    component_pairs = registry.discover_components(app)
    app.layout = build_root_layout(component_pairs)

    # Register product dropdown callback
    _register_global_callbacks(app)

    logger.info("Dash app created with %d components", len(component_pairs))
    return app


def _register_global_callbacks(app: dash.Dash) -> None:
    from dash import Input, Output

    from src.dashboard.api_client import api

    @app.callback(
        Output("product-dropdown", "options"),
        Output("product-dropdown", "value"),
        Output("selected-product", "data"),
        Input("products-interval", "n_intervals"),
        Input("product-dropdown", "value"),
    )
    def refresh_products(_: int, selected: str | None) -> tuple[list[dict], str | None, str | None]:
        products = api.get("/analytics/products") or []
        options = [{"label": p, "value": p} for p in products]
        chosen = selected if selected in products else (products[0] if products else None)
        return options, chosen, chosen
