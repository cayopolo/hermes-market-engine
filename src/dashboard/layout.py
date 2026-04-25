from typing import Any

import dash_bootstrap_components as dbc
from dash import dcc, html


def build_header() -> dbc.Navbar:
    return dbc.Navbar(
        dbc.Container(
            [
                dbc.NavbarBrand("⬡ Hermes", class_name="fw-bold text-light fs-4"),
                dbc.Nav(
                    [
                        dbc.NavItem(
                            dcc.Dropdown(
                                id="product-dropdown",
                                placeholder="Loading products…",
                                clearable=False,
                                style={"width": "160px", "color": "#000"},
                            )
                        )
                    ],
                    class_name="ms-auto",
                ),
            ],
            fluid=True,
        ),
        color="dark",
        dark=True,
        class_name="mb-3",
    )


def build_root_layout(component_pairs: list[tuple[dict, Any]]) -> html.Div:
    """
    component_pairs: list of (CARD_SPEC, layout_element) sorted by order.
    """
    rows: list = []
    current_row: list = []
    current_width = 0

    for spec, card in component_pairs:
        w = spec.get("width", 6)
        if current_width + w > 12:
            rows.append(dbc.Row(current_row, class_name="mb-3"))
            current_row = []
            current_width = 0
        current_row.append(dbc.Col(card, width=w))
        current_width += w

    if current_row:
        rows.append(dbc.Row(current_row, class_name="mb-3"))

    return html.Div(
        [
            dcc.Store(id="selected-product", data=None),
            build_header(),
            dbc.Container(rows, fluid=True),
            # Global interval for product list refresh
            dcc.Interval(id="products-interval", interval=5_000, n_intervals=0),
        ]
    )
