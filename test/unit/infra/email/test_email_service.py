import smtplib
from email.message import EmailMessage
from unittest.mock import MagicMock

import pytest

from src.core.exceptions import FeatureUnavailableError
from src.infra.email.email_service import (
    PASSWORD_RESET_SUBJECT,
    DisabledEmailService,
    SmtpEmailService,
)

HOST = "smtp.example.com"
PORT = 587
SENDER = "no-reply@pizzaria.com"
RECIPIENT = "ana@example.com"
TOKEN = "reset-token-123"
USERNAME = "smtp-user"
PASSWORD = "smtp-pass"
RESET_URL = "https://app.pizzaria.com/reset-password"


def _smtp_mock() -> tuple[MagicMock, MagicMock]:
    smtp = MagicMock(spec=smtplib.SMTP)
    smtp.__enter__.return_value = smtp
    factory = MagicMock(return_value=smtp)
    return factory, smtp


def _sent_message(smtp: MagicMock) -> EmailMessage:
    message: EmailMessage = smtp.send_message.call_args.args[0]
    return message


async def test_send_password_reset_email_sends_token_with_tls_and_login() -> None:
    factory, smtp = _smtp_mock()
    service = SmtpEmailService(
        host=HOST,
        port=PORT,
        sender=SENDER,
        username=USERNAME,
        password=PASSWORD,
        smtp_factory=factory,
    )

    await service.send_password_reset_email(email=RECIPIENT, token=TOKEN)

    factory.assert_called_once_with(HOST, PORT)
    smtp.starttls.assert_called_once_with()
    smtp.login.assert_called_once_with(USERNAME, PASSWORD)
    message = _sent_message(smtp)
    assert message["To"] == RECIPIENT
    assert message["From"] == SENDER
    assert message["Subject"] == PASSWORD_RESET_SUBJECT
    assert TOKEN in message.get_content()


async def test_send_password_reset_email_skips_tls_and_login_when_not_configured() -> None:
    factory, smtp = _smtp_mock()
    service = SmtpEmailService(
        host=HOST, port=PORT, sender=SENDER, use_tls=False, smtp_factory=factory
    )

    await service.send_password_reset_email(email=RECIPIENT, token=TOKEN)

    smtp.starttls.assert_not_called()
    smtp.login.assert_not_called()
    smtp.send_message.assert_called_once()


async def test_send_password_reset_email_builds_link_when_reset_url_configured() -> None:
    factory, smtp = _smtp_mock()
    service = SmtpEmailService(
        host=HOST, port=PORT, sender=SENDER, reset_url=RESET_URL, smtp_factory=factory
    )

    await service.send_password_reset_email(email=RECIPIENT, token=TOKEN)

    assert f"{RESET_URL}?token={TOKEN}" in _sent_message(smtp).get_content()


async def test_disabled_email_service_raises_503_when_sending() -> None:
    service = DisabledEmailService()

    with pytest.raises(FeatureUnavailableError) as exc_info:
        await service.send_password_reset_email(email=RECIPIENT, token=TOKEN)

    assert exc_info.value.status_code == 503
    assert exc_info.value.code == "FEATURE_UNAVAILABLE"
