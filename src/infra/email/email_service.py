from typing import Protocol

from src.core.logger import logger


class EmailServiceProtocol(Protocol):
    async def send_password_reset_email(
        self,
        email: str,
        token: str,
    ) -> None: ...


class MockEmailService(EmailServiceProtocol):
    async def send_password_reset_email(
        self,
        email: str,
        token: str,
    ) -> None:
        logger.bind(
            email=email,
            token=token,
        ).info("password_reset_email_sent")
