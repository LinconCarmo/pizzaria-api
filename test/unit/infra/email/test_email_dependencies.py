import pytest

from src.core.config import settings
from src.infra.email.email_dependencies import get_email_service
from src.infra.email.email_service import MockEmailService, SmtpEmailService

SMTP_HOST = "smtp.example.com"
SMTP_SENDER = "no-reply@pizzaria.com"


def test_get_email_service_returns_mock_when_smtp_not_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "smtp_host", None)

    service = get_email_service()

    assert isinstance(service, MockEmailService)


def test_get_email_service_returns_smtp_when_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "smtp_host", SMTP_HOST)
    monkeypatch.setattr(settings, "smtp_sender", SMTP_SENDER)

    service = get_email_service()

    assert isinstance(service, SmtpEmailService)
