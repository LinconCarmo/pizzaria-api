from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    redis_url: str
    rabbitmq_url: str
    jwt_secret: str
    app_env: Literal["development", "production", "test"] = "development"
    log_level: str = "INFO"
    database_url_test: str = ""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
