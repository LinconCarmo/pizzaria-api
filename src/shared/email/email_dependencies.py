from .email_service import (
    EmailServiceProtocol,
    MockEmailService,
)


def get_email_service() -> EmailServiceProtocol:
    return MockEmailService()
