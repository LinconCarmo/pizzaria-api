import pytest
from loguru import logger

from src.core.config import settings
from src.infra.email.email_dependencies import get_email_service, warn_if_email_disabled
from src.infra.email.email_service import DisabledEmailService, SmtpEmailService

SMTP_HOST = "smtp.example.com"
SMTP_SENDER = "no-reply@pizzaria.com"


def _capture_warnings() -> tuple[list[str], int]:
    messages: list[str] = []
    sink_id = logger.add(lambda m: messages.append(m.record["message"]), level="WARNING")
    return messages, sink_id


def test_get_email_service_returns_disabled_when_smtp_not_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "smtp_host", None)

    service = get_email_service()

    assert isinstance(service, DisabledEmailService)
    assert service.is_available() is False


def test_get_email_service_returns_smtp_when_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "smtp_host", SMTP_HOST)
    monkeypatch.setattr(settings, "smtp_sender", SMTP_SENDER)

    service = get_email_service()

    assert isinstance(service, SmtpEmailService)
    assert service.is_available() is True


def test_warn_if_email_disabled_logs_warning_when_smtp_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "smtp_host", None)
    messages, sink_id = _capture_warnings()

    warn_if_email_disabled()

    logger.remove(sink_id)
    assert messages == ["email_delivery_disabled"]


def test_warn_if_email_disabled_stays_silent_when_smtp_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "smtp_host", SMTP_HOST)
    monkeypatch.setattr(settings, "smtp_sender", SMTP_SENDER)
    messages, sink_id = _capture_warnings()

    warn_if_email_disabled()

    logger.remove(sink_id)
    assert messages == []
