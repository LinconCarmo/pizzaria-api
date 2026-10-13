from src.core.config import settings
from src.core.logger import logger

from .email_service import (
    DisabledEmailService,
    EmailServiceProtocol,
    SmtpEmailService,
)


def get_email_service() -> EmailServiceProtocol:
    if settings.smtp_host is None or settings.smtp_sender is None:
        return DisabledEmailService()

    return SmtpEmailService(
        host=settings.smtp_host,
        port=settings.smtp_port,
        sender=settings.smtp_sender,
        username=settings.smtp_username,
        password=settings.smtp_password,
        use_tls=settings.smtp_use_tls,
        reset_url=settings.password_reset_url,
    )


def warn_if_email_disabled() -> None:
    """Avisa no startup quando o envio de e-mail está desligado por falta de SMTP."""
    if not get_email_service().is_available():
        logger.bind(missing=["SMTP_HOST", "SMTP_SENDER"]).warning("email_delivery_disabled")
