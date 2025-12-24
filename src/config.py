from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Database
    db_user: str = Field(default="postgres", alias="DB_USER")
    db_name: str = Field(default="hermes_market_engine", alias="DB_NAME")
    db_password: str = Field(default="postgres", alias="DB_PASSWORD")
    db_host: str = Field(default="localhost")
    db_port: int = Field(default=5432)

    # Coinbase WebSocket
    coinbase_ws_url: str = "wss://advanced-trade-ws.coinbase.com"
    product_ids: list[str] = Field(default=["ETH-EUR", "XRP-USD"])
    channel: str = Field(default="level2")

    # Redis Pub/Sub (Hot Path)
    redis_url: str = "redis://localhost:6379"
    redis_channel: str = "hermes:market_data"

    # Cold Path (Database Batching)
    db_batch_interval_seconds: float = Field(default=10.0, alias="DB_BATCH_INTERVAL_SECONDS")
    db_batch_size: int = Field(default=1000, alias="DB_BATCH_SIZE")
    db_pool_min_size: int = Field(default=2, alias="DB_POOL_MIN_SIZE")
    db_pool_max_size: int = Field(default=10, alias="DB_POOL_MAX_SIZE")
    db_max_retry_attempts: int = Field(default=3, alias="DB_MAX_RETRY_ATTEMPTS")

    # API Server
    api_host: str = Field(default="127.0.0.1")  # 127.0.0.1 for localhost only
    api_port: int = Field(default=8000)

    # Logging
    log_level: str = Field(default="INFO")

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
