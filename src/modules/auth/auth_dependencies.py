from typing import Annotated

from fastapi import Depends, Request
from prisma import Prisma

from src.core.rate_limit import RateLimiterProtocol, RateLimitPolicy, get_rate_limiter
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

LOGIN_PER_IP = RateLimitPolicy(max_attempts=20, window_seconds=60)

FORGOT_PASSWORD_PER_IP = RateLimitPolicy(max_attempts=5, window_seconds=15 * 60)


def _client_ip(request: Request) -> str:
    return request.client.host if request.client is not None else "unknown"


def _limit_by_ip(
    request: Request,
    limiter: RateLimiterProtocol,
    *,
    scope: str,
    policy: RateLimitPolicy,
) -> None:
    key = f"{scope}:ip:{_client_ip(request)}"
    limiter.check(key, policy)
    limiter.record(key, policy)


async def limit_login_by_ip(
    request: Request,
    limiter: Annotated[RateLimiterProtocol, Depends(get_rate_limiter)],
) -> None:
    _limit_by_ip(request, limiter, scope="login", policy=LOGIN_PER_IP)


async def limit_forgot_password_by_ip(
    request: Request,
    limiter: Annotated[RateLimiterProtocol, Depends(get_rate_limiter)],
) -> None:
    _limit_by_ip(request, limiter, scope="forgot-password", policy=FORGOT_PASSWORD_PER_IP)


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
    rate_limiter: Annotated[
        RateLimiterProtocol,
        Depends(get_rate_limiter),
    ],
) -> AuthService:
    return AuthService(
        repository,
        password_reset_repository,
        email_service,
        rate_limiter,
    )
