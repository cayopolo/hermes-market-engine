from __future__ import annotations

from dash import html


def imbalance_panel() -> html.Div:
    return html.Div(
        className="panel imbalance-panel",
        children=[
            html.Div("Order Flow Imbalance", className="panel-header"),
            html.Div(
                className="imbalance-container",
                children=[
                    html.Div(
                        className="imbalance-gauge",
                        children=[
                            html.Div(
                                className="imbalance-track",
                                children=[
                                    html.Div(id="imbalance-fill", className="imbalance-fill"),
                                    html.Div(className="imbalance-center-mark"),
                                ],
                            ),
                            html.Div(className="imbalance-labels", children=[html.Span("-1"), html.Span("0"), html.Span("+1")]),
                        ],
                    ),
                    html.Div(id="imbalance-value", className="imbalance-value-text", children=html.Span("—")),
                ],
            ),
        ],
    )
