import click

from src.config import settings
from src.logging_config import get_logger, setup_logging

logger = get_logger(__name__)


@click.command()
@click.option("--host", default=None, help="Dashboard host (overrides config)")
@click.option("--port", default=None, type=int, help="Dashboard port (overrides config)")
@click.option("--log-level", type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"], case_sensitive=False))
@click.option("--debug", is_flag=True, default=False)
def cli(host: str | None, port: int | None, log_level: str | None, *, debug: bool) -> None:
    """Hermes Dashboard — Plotly Dash UI for the market engine."""
    setup_logging(level=log_level or settings.log_level)
    from src.dashboard.app import create_app

    app = create_app()
    app.run(host=host or settings.dashboard_host, port=port or settings.dashboard_port, debug=debug)


if __name__ == "__main__":
    cli()
