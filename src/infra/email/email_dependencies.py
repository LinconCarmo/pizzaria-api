from src.core.config import settings

from .email_service import (
    EmailServiceProtocol,
    MockEmailService,
    SmtpEmailService,
)


def get_email_service() -> EmailServiceProtocol:
    if settings.smtp_host is None or settings.smtp_sender is None:
        return MockEmailService()

    return SmtpEmailService(
        host=settings.smtp_host,
        port=settings.smtp_port,
        sender=settings.smtp_sender,
        username=settings.smtp_username,
        password=settings.smtp_password,
        use_tls=settings.smtp_use_tls,
        reset_url=settings.password_reset_url,
    )
