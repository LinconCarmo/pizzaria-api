import pytest
from pydantic import ValidationError

from src.core.config import Settings


def test_settings_loads_required_fields(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "mysql://test")
    monkeypatch.setenv("REDIS_URL", "redis://test")
    monkeypatch.setenv("RABBITMQ_URL", "amqp://test")
    monkeypatch.setenv("JWT_SECRET", "supersecret")

    s = Settings()

    assert s.database_url == "mysql://test"
    assert s.redis_url == "redis://test"
    assert s.rabbitmq_url == "amqp://test"
    assert s.jwt_secret == "supersecret"


def test_settings_defaults(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "mysql://test")
    monkeypatch.setenv("REDIS_URL", "redis://test")
    monkeypatch.setenv("RABBITMQ_URL", "amqp://test")
    monkeypatch.setenv("JWT_SECRET", "secret")
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("LOG_LEVEL", raising=False)
    monkeypatch.delenv("DATABASE_URL_TEST", raising=False)

    # bypass .env file to test the class-level defaults
    s = Settings(_env_file=None)  # type: ignore[call-arg]

    assert s.app_env == "development"
    assert s.log_level == "INFO"
    assert s.database_url_test == ""


def test_settings_accepts_valid_app_env_values(monkeypatch):
    for env in ("development", "production", "test"):
        monkeypatch.setenv("DATABASE_URL", "mysql://test")
        monkeypatch.setenv("REDIS_URL", "redis://test")
        monkeypatch.setenv("RABBITMQ_URL", "amqp://test")
        monkeypatch.setenv("JWT_SECRET", "secret")
        monkeypatch.setenv("APP_ENV", env)

        s = Settings()

        assert s.app_env == env


def test_settings_rejects_invalid_app_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "mysql://test")
    monkeypatch.setenv("REDIS_URL", "redis://test")
    monkeypatch.setenv("RABBITMQ_URL", "amqp://test")
    monkeypatch.setenv("JWT_SECRET", "secret")
    monkeypatch.setenv("APP_ENV", "staging")

    with pytest.raises(ValidationError):
        Settings()


def test_settings_accepts_database_url_test(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "mysql://prod")
    monkeypatch.setenv("REDIS_URL", "redis://test")
    monkeypatch.setenv("RABBITMQ_URL", "amqp://test")
    monkeypatch.setenv("JWT_SECRET", "secret")
    monkeypatch.setenv("DATABASE_URL_TEST", "mysql://test_db")

    s = Settings()

    assert s.database_url_test == "mysql://test_db"
