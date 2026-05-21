from src.core.config import settings


def test_settings():
    assert settings.database_url is not None
    assert settings.jwt_secret is not None
