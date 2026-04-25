import dash
import dash_bootstrap_components as dbc
from dash import html

CARD_SPEC = {"title": "Welcome", "width": 12, "order": 0}


def layout() -> dbc.Card:
    return dbc.Card(
        dbc.CardBody(html.P("Select a product above to begin. Components will populate as you switch products.", className="text-muted")),
        id="placeholder-card",
    )


def register_callbacks(app: dash.Dash) -> None:
    pass  # No callbacks for static card
