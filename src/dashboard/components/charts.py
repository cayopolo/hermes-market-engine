from __future__ import annotations

from dash import dcc, html


def charts_row() -> html.Div:
    graph_config = {"displayModeBar": False, "responsive": True}
    graph_style = {"height": "220px"}

    return html.Div(
        className="charts-row",
        children=[
            html.Div(
                className="panel chart-panel",
                children=[
                    html.Div("Midprice / VAMP", className="panel-header"),
                    dcc.Graph(id="chart-midprice", config=graph_config, style=graph_style),
                ],
            ),
            html.Div(
                className="panel chart-panel",
                children=[
                    html.Div("Spread", className="panel-header"),
                    dcc.Graph(id="chart-spread", config=graph_config, style=graph_style),
                ],
            ),
            html.Div(
                className="panel chart-panel",
                children=[
                    html.Div("Imbalance", className="panel-header"),
                    dcc.Graph(id="chart-imbalance", config=graph_config, style=graph_style),
                ],
            ),
        ],
    )
