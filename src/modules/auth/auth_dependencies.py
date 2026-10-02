from typing import Annotated, TypedDict

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from prisma import Prisma

from src.core.exceptions import ForbiddenError, UnauthorizedError
from src.core.security import decode_token
from src.infra.database import get_db
from src.infra.email.email_dependencies import get_email_service
from src.infra.email.email_service import EmailServiceProtocol
from src.modules.auth.auth_service import AuthService
from src.modules.auth.password_reset_token_repository import (
    PasswordResetTokenRepository,
    PasswordResetTokenRepositoryProtocol,
)
from src.modules.users.user_repository import (
    UserRepository,
    UserRepositoryProtocol,
)

_bearer_scheme = HTTPBearer(auto_error=False)


class AuthenticatedUser(TypedDict):
    sub: str
    role: str


def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(_bearer_scheme),
    ],
) -> AuthenticatedUser:
    if credentials is None:
        raise UnauthorizedError("Authentication required")

    payload = decode_token(credentials.credentials)

    if payload.get("token_type") != "access":
        raise UnauthorizedError("Invalid token type")

    sub = payload.get("sub")
    role = payload.get("role")

    if not isinstance(sub, str) or not isinstance(role, str):
        raise UnauthorizedError("Invalid token claims")

    return {
        "sub": sub,
        "role": role,
    }


def require_admin(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> AuthenticatedUser:
    if current_user["role"] != "ADMIN":
        raise ForbiddenError("Admin role required")

    return current_user


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
