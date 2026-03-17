from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables and .env files."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "dgbit-api"
    api_prefix: str = "/api"
    environment: str = "development"
    log_level: str = "INFO"

    # Messaging / worker configuration
    nng_command_address: str = "ipc:///tmp/dgbit_commands.ipc"
    nng_event_address: str = "ipc:///tmp/dgbit_events.ipc"

    # Data defaults
    default_symbol: str = "BTCUSDT"
    default_interval: str = "1"
    bybit_api_key: str = ""
    bybit_api_secret: str = ""


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
