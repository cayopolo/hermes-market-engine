from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Database
    db_user: str = Field(default="postgres", alias="DB_USER")
    db_name: str = Field(default="hermes_db", alias="DB_NAME")
    db_password: str = Field(default="", alias="DB_PASSWORD")
    db_host: str = Field(default="localhost")
    db_port: int = Field(default=5432)

    # Coinbase WebSocket
    coinbase_ws_url: str = "wss://advanced-trade-ws.coinbase.com"
    product_id: str = Field(default="XRP-USD")
    channel: str = Field(default="level2")

    # Logging
    Log_level: str = Field(default="INFO")

    model_config = SettingsConfigDict(env_file=".env")
