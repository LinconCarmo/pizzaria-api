from typing import Literal, Self

from pydantic import field_validator, model_validator
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

    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_sender: str | None = None
    smtp_use_tls: bool = True
    password_reset_url: str | None = None

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator("log_level", mode="before")
    @classmethod
    def normalize_log_level(cls, v: object) -> object:
        if isinstance(v, str):
            return v.upper()
        return v

    @model_validator(mode="after")
    def require_smtp_in_production(self) -> Self:
        if self.app_env == "production" and (self.smtp_host is None or self.smtp_sender is None):
            raise ValueError("SMTP_HOST and SMTP_SENDER are required when APP_ENV=production")
        return self


settings = Settings()  # type: ignore[call-arg]
