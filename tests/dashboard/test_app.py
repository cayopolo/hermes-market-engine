from unittest.mock import patch


def test_theme_constants() -> None:
    from src.dashboard.theme import ASK_COLOR, BID_COLOR, PLOTLY_TEMPLATE

    assert BID_COLOR.startswith("#")
    assert ASK_COLOR.startswith("#")
    assert PLOTLY_TEMPLATE == "plotly_dark"


def test_api_client_handles_connection_error() -> None:
    import httpx

    from src.dashboard.api_client import ApiClient

    client = ApiClient()
    client._base = "http://127.0.0.1:19999"
    client._client = httpx.Client(base_url="http://127.0.0.1:19999", timeout=0.5)
    result = client.get("/analytics/products")
    assert result is None


def test_db_client_stubs_return_empty() -> None:
    from src.dashboard.db_client import fetch_midprice_history, fetch_spread_history

    assert fetch_midprice_history("ETH-EUR", "2025-01-01", "2025-01-02", "1m") == []
    assert fetch_spread_history("ETH-EUR", "2025-01-01", "2025-01-02", "1m") == []


def test_create_app_smoke() -> None:
    with patch("src.dashboard.api_client.api.get", return_value=["ETH-EUR", "XRP-USD"]):
        from src.dashboard.app import create_app

        app = create_app()
        assert app is not None
        assert app.title == "Hermes Dashboard"


def test_placeholder_component() -> None:
    import dash

    from src.dashboard.components.placeholder import CARD_SPEC, layout, register_callbacks

    assert CARD_SPEC["width"] > 0
    card = layout()
    assert card is not None
    app = dash.Dash(__name__, suppress_callback_exceptions=True)
    register_callbacks(app)  # should not raise
