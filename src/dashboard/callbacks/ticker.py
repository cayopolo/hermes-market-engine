from __future__ import annotations

from dash import Input, Output, State, callback, html, no_update


@callback(
    Output("ticker-content", "children"),
    Input("current-store", "data"),
    State("timeseries-store", "data"),
    State("product-selector", "value"),
    prevent_initial_call=True,
)
def update_ticker(current: dict | None, ts_data: dict | None, product_id: str | None) -> list | object:
    if not current or not current.get("analytics"):
        return no_update

    a = current["analytics"]
    product_ts = ts_data.get(product_id, []) if isinstance(ts_data, dict) and product_id else []
    prev = product_ts[-2] if len(product_ts) >= 2 else {}

    return [
        _card("Midprice", a.get("midprice"), prev.get("midprice"), css="metric-card-primary"),
        _card("Best Bid", a.get("best_bid"), prev.get("best_bid"), css="metric-card-bid"),
        _card("Best Ask", a.get("best_ask"), prev.get("best_ask"), css="metric-card-ask"),
        _card("Spread", a.get("spread"), prev.get("spread"), decimals=4),
        _card("VAMP", a.get("volume_adjusted_midprice"), prev.get("vamp")),
        _card("VAMP(n)", a.get("volume_adjusted_midprice_n"), prev.get("vamp_n")),
        html.Div(className="metric-card"),
    ]


@callback(
    Output("imbalance-fill", "style"), Output("imbalance-value", "children"), Input("current-store", "data"), prevent_initial_call=True
)
def update_imbalance(current: dict | None) -> tuple:
    if not current or not current.get("analytics"):
        return no_update, no_update

    imbalance = current["analytics"].get("imbalance")
    if imbalance is None:
        return no_update, "—"

    v = max(-1.0, min(1.0, imbalance))
    left = 50.0 if v >= 0 else 50.0 + v * 50.0
    width = abs(v) * 50.0
    color = "var(--accent-green)" if v >= 0 else "var(--accent-red)"

    style = {"left": f"{left}%", "width": f"{width}%", "backgroundColor": color}
    sign = "+" if v > 0 else ""
    return style, f"{sign}{v:.4f}"


def _card(label: str, value: float | None, prev: float | None, *, css: str = "", decimals: int = 2) -> html.Div:
    formatted = f"{value:,.{decimals}f}" if value is not None else "—"
    return html.Div(
        className=f"metric-card {css}".strip(),
        children=[html.Div(label, className="metric-label"), html.Div(formatted, className="metric-value"), _delta(value, prev, decimals)],
    )


def _delta(current: float | None, previous: float | None, decimals: int = 2) -> html.Div:
    if current is None or previous is None:
        return html.Div(className="metric-delta")
    diff = current - previous
    if abs(diff) < 1e-10:
        return html.Div(className="metric-delta")
    arrow = "▲" if diff > 0 else "▼"
    css = "metric-delta delta-up" if diff > 0 else "metric-delta delta-down"
    return html.Div(f"{arrow} {abs(diff):.{decimals}f}", className=css)
