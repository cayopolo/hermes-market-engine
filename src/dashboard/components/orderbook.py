from __future__ import annotations

import dash_ag_grid as dag
from dash import dcc, html


def orderbook_panels() -> html.Div:
    return html.Div(
        className="orderbook-row",
        children=[
            html.Div(
                className="panel depth-panel",
                children=[
                    html.Div("Orderbook Depth", className="panel-header"),
                    dcc.Graph(id="depth-chart", config={"displayModeBar": False}, style={"height": "350px"}),
                ],
            ),
            html.Div(
                className="panel ladder-panel",
                children=[
                    html.Div("Order Ladder", className="panel-header"),
                    dag.AgGrid(
                        id="orderbook-ladder",
                        columnDefs=[
                            {
                                "field": "bid_size",
                                "headerName": "Bid Size",
                                "type": "rightAligned",
                                "cellStyle": {"color": "#3fb950"},
                                "valueFormatter": {"function": "params.value != null ? Number(params.value).toFixed(6) : ''"},
                            },
                            {
                                "field": "bid_price",
                                "headerName": "Bid Price",
                                "type": "rightAligned",
                                "cellStyle": {"color": "#3fb950", "fontWeight": "500"},
                                "valueFormatter": {"function": "params.value != null ? Number(params.value).toFixed(2) : ''"},
                            },
                            {
                                "field": "ask_price",
                                "headerName": "Ask Price",
                                "cellStyle": {"color": "#f85149", "fontWeight": "500"},
                                "valueFormatter": {"function": "params.value != null ? Number(params.value).toFixed(2) : ''"},
                            },
                            {
                                "field": "ask_size",
                                "headerName": "Ask Size",
                                "cellStyle": {"color": "#f85149"},
                                "valueFormatter": {"function": "params.value != null ? Number(params.value).toFixed(6) : ''"},
                            },
                        ],
                        rowData=[],
                        defaultColDef={"resizable": True, "sortable": False, "filter": False, "flex": 1},
                        getRowStyle={
                            "styleConditions": [
                                {
                                    "condition": "params.node.rowIndex === 0",
                                    "style": {"backgroundColor": "rgba(88, 166, 255, 0.1)", "fontWeight": "bold"},
                                }
                            ]
                        },
                        style={"height": "350px"},
                        className="ag-theme-alpine-dark",
                    ),
                ],
            ),
        ],
    )
