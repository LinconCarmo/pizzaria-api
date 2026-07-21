from typing import Annotated

from fastapi import Depends
from prisma import Prisma

from src.infra.database import get_db
from src.modules.auth.auth_service import AuthService
from src.modules.auth.password_reset_token_repository import (
    PasswordResetTokenRepository,
    PasswordResetTokenRepositoryProtocol,
)
from src.modules.users.user_repository import (
    UserRepository,
    UserRepositoryProtocol,
)
from src.shared.email.email_dependencies import get_email_service
from src.shared.email.email_service import EmailServiceProtocol


def get_auth_repository(
    db: Annotated[Prisma, Depends(get_db)],
) -> UserRepositoryProtocol:
    return UserRepository(db)


def get_password_reset_token_repository(
    db: Annotated[Prisma, Depends(get_db)],
) -> PasswordResetTokenRepositoryProtocol:
    return PasswordResetTokenRepository(db)


def get_auth_service(
    repository: Annotated[
        UserRepositoryProtocol,
        Depends(get_auth_repository),
    ],
    password_reset_repository: Annotated[
        PasswordResetTokenRepositoryProtocol,
        Depends(get_password_reset_token_repository),
    ],
    email_service: Annotated[
        EmailServiceProtocol,
        Depends(get_email_service),
    ],
) -> AuthService:
    return AuthService(
        repository,
        password_reset_repository,
        email_service,
    )
