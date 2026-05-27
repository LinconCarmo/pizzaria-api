from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    redis_url: str
    rabbitmq_url: str
    jwt_secret: str
    app_env: Literal["development", "production", "test"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    database_url_test: str = ""
    host: str = "127.0.0.1"
    port: int = 8000

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator("log_level", mode="before")
    @classmethod
    def normalize_log_level(cls, v: object) -> object:
        if isinstance(v, str):
            return v.upper()
        return v


settings = Settings()  # type: ignore[call-arg]
