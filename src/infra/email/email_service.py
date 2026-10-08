import asyncio
import smtplib
from collections.abc import Callable
from email.message import EmailMessage
from typing import Protocol

from src.core.exceptions import FeatureUnavailableError
from src.core.logger import logger

PASSWORD_RESET_SUBJECT = "Redefinição de senha"

EMAIL_UNAVAILABLE_MESSAGE = "Password reset by email is not available: no SMTP server is configured"


class EmailServiceProtocol(Protocol):
    def is_available(self) -> bool: ...

    async def send_password_reset_email(
        self,
        email: str,
        token: str,
    ) -> None: ...


class DisabledEmailService(EmailServiceProtocol):
    """Usado enquanto não há SMTP configurado.

    A aplicação sobe normalmente; quem depende de e-mail consulta `is_available()`
    antes de agir e responde que a funcionalidade não está disponível.
    """

    def is_available(self) -> bool:
        return False

    async def send_password_reset_email(
        self,
        email: str,
        token: str,
    ) -> None:
        raise FeatureUnavailableError(EMAIL_UNAVAILABLE_MESSAGE)


class SmtpEmailService(EmailServiceProtocol):
    def __init__(
        self,
        *,
        host: str,
        port: int,
        sender: str,
        username: str | None = None,
        password: str | None = None,
        use_tls: bool = True,
        reset_url: str | None = None,
        smtp_factory: Callable[[str, int], smtplib.SMTP] = smtplib.SMTP,
    ) -> None:
        self._host = host
        self._port = port
        self._sender = sender
        self._username = username
        self._password = password
        self._use_tls = use_tls
        self._reset_url = reset_url
        self._smtp_factory = smtp_factory

    def is_available(self) -> bool:
        return True

    async def send_password_reset_email(
        self,
        email: str,
        token: str,
    ) -> None:
        message = self._build_password_reset_message(email=email, token=token)
        await asyncio.to_thread(self._send, message)
        logger.info("password_reset_email_sent")

    def _build_password_reset_message(self, *, email: str, token: str) -> EmailMessage:
        message = EmailMessage()
        message["From"] = self._sender
        message["To"] = email
        message["Subject"] = PASSWORD_RESET_SUBJECT

        if self._reset_url:
            instructions = (
                f"Acesse o link para definir uma nova senha:\n{self._reset_url}?token={token}"
            )
        else:
            instructions = f"Use este código para definir uma nova senha:\n{token}"

        message.set_content(
            f"{instructions}\n\n"
            "O pedido expira em 1 hora. Se não foi você quem pediu, ignore este e-mail."
        )
        return message

    def _send(self, message: EmailMessage) -> None:
        with self._smtp_factory(self._host, self._port) as smtp:
            if self._use_tls:
                smtp.starttls()
            if self._username and self._password:
                smtp.login(self._username, self._password)
            smtp.send_message(message)
