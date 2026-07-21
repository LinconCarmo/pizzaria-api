from typing import Protocol


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
        print(
            f"""
            ===== MOCK EMAIL =====
            To: {email}

            Password reset link:
            https://app/reset-password?token={token}

            ======================
            """
        )
