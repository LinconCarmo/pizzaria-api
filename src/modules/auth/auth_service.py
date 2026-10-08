from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import UUID, uuid4

from src.core.exceptions import BadRequestError, ForbiddenError, UnauthorizedError
from src.core.logger import logger
from src.core.rate_limit import RateLimiterProtocol, RateLimitPolicy
from src.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    hash_reset_token,
    verify_password,
)
from src.infra.email.email_service import EmailServiceProtocol
from src.modules.auth.auth_schema import (
    ForgotPasswordDto,
    LoginDto,
    LoginResponseDto,
    LoginUserResponse,
    RefreshTokenDto,
    ResetPasswordDto,
)
from src.modules.auth.password_reset_token_repository import (
    PasswordResetTokenRepositoryProtocol,
)
from src.modules.users.user_repository import UserRepositoryProtocol

_INVALID_TOKEN_MESSAGE = "Invalid token"

_INACTIVE_USER_MESSAGE = "User is inactive"

_INVALID_CREDENTIALS_MESSAGE = "Invalid credentials"

LOGIN_FAILURES_PER_EMAIL = RateLimitPolicy(max_attempts=5, window_seconds=15 * 60)

FORGOT_PASSWORD_PER_EMAIL = RateLimitPolicy(max_attempts=3, window_seconds=60 * 60)


class AuthService:
    def __init__(
        self,
        repository: UserRepositoryProtocol,
        password_reset_repository: PasswordResetTokenRepositoryProtocol,
        email_service: EmailServiceProtocol,
        rate_limiter: RateLimiterProtocol,
    ) -> None:
        self._repository = repository
        self._password_reset_repository = password_reset_repository
        self._email_service = email_service
        self._rate_limiter = rate_limiter

    async def login(
        self,
        data: LoginDto,
    ) -> LoginResponseDto:
        rate_limit_key = f"login:email:{data.email.lower()}"
        self._rate_limiter.check(rate_limit_key, LOGIN_FAILURES_PER_EMAIL)

        user = await self._repository.get_by_email(data.email)

        if user is None:
            raise self._login_failed(rate_limit_key)

        hashed_password = cast(
            str,
            user["hashedPassword"],
        )

        role_data = cast(
            dict[str, object],
            user["role"],
        )

        role = cast(
            str,
            role_data["name"],
        )

        user_id = cast(
            UUID,
            user["id"],
        )

        user_name = cast(
            str,
            user["name"],
        )

        if not verify_password(
            data.password,
            hashed_password,
        ):
            raise self._login_failed(rate_limit_key)

        if not user["isActive"]:
            raise ForbiddenError(_INACTIVE_USER_MESSAGE)

        self._rate_limiter.reset(rate_limit_key)

        return self._issue_tokens(
            user_id=user_id,
            name=user_name,
            role=role,
        )

    async def refresh_token(
        self,
        data: RefreshTokenDto,
    ) -> LoginResponseDto:
        payload = decode_token(
            data.refresh_token,
        )

        if payload.get("token_type") != "refresh":
            raise UnauthorizedError("Invalid token type")

        sub = payload.get("sub")

        if not isinstance(sub, str):
            raise UnauthorizedError(_INVALID_TOKEN_MESSAGE)

        try:
            user_id = UUID(sub)
        except ValueError as exc:
            raise UnauthorizedError(_INVALID_TOKEN_MESSAGE) from exc

        user = await self._repository.get_by_id(
            user_id,
        )

        if user is None:
            raise UnauthorizedError(_INVALID_TOKEN_MESSAGE)

        if not user["isActive"]:
            raise ForbiddenError(
                "User is inactive",
            )

        role_data = cast(
            dict[str, object],
            user["role"],
        )

        role = cast(
            str,
            role_data["name"],
        )

        user_name = cast(
            str,
            user["name"],
        )

        return self._issue_tokens(
            user_id=user_id,
            name=user_name,
            role=role,
        )

    async def forgot_password(
        self,
        data: ForgotPasswordDto,
    ) -> None:
        rate_limit_key = f"forgot-password:email:{data.email.lower()}"
        self._rate_limiter.check(rate_limit_key, FORGOT_PASSWORD_PER_EMAIL)
        self._rate_limiter.record(rate_limit_key, FORGOT_PASSWORD_PER_EMAIL)

        user = await self._repository.get_by_email(data.email)

        if user is None:
            hash_password(str(uuid4()))
            return

        user_id = cast(UUID, user["id"])

        logger.bind(user_id=user_id).info(
            "password_reset_requested",
        )

        token = str(uuid4())
        token_hash = hash_reset_token(token)

        expires_at = datetime.now(UTC) + timedelta(hours=1)

        await self._password_reset_repository.delete_by_user_id(
            user_id,
        )

        await self._password_reset_repository.create(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )

        await self._email_service.send_password_reset_email(
            email=data.email,
            token=token,
        )

    def _login_failed(self, rate_limit_key: str) -> UnauthorizedError:
        self._rate_limiter.record(rate_limit_key, LOGIN_FAILURES_PER_EMAIL)
        return UnauthorizedError(_INVALID_CREDENTIALS_MESSAGE)

    def _issue_tokens(
        self,
        *,
        user_id: UUID,
        name: str,
        role: str,
    ) -> LoginResponseDto:
        return LoginResponseDto(
            user=LoginUserResponse(
                id=user_id,
                name=name,
                role=role,
            ),
            access_token=create_access_token(
                sub=str(user_id),
                role=role,
            ),
            refresh_token=create_refresh_token(
                sub=str(user_id),
            ),
            expires_in=900,
        )

    async def reset_password(
        self,
        data: ResetPasswordDto,
    ) -> None:

        token_hash = hash_reset_token(data.token)

        reset_token = await self._password_reset_repository.get_by_token_hash(token_hash=token_hash)

        if reset_token is None:
            raise BadRequestError(_INVALID_TOKEN_MESSAGE)

        if reset_token["usedAt"] is not None:
            raise BadRequestError(_INVALID_TOKEN_MESSAGE)

        now = datetime.now(UTC)
        expires_at = cast(
            datetime,
            reset_token["expiresAt"],
        )

        if expires_at < now:
            raise BadRequestError(_INVALID_TOKEN_MESSAGE)

        reset_user_id = cast(UUID, reset_token["userId"])

        user = await self._repository.get_by_id(
            reset_user_id,
        )

        if user is None:
            raise BadRequestError(_INVALID_TOKEN_MESSAGE)

        if not user["isActive"]:
            raise ForbiddenError(_INACTIVE_USER_MESSAGE)

        hashed_password = hash_password(data.new_password)

        user_id = cast(
            UUID,
            user["id"],
        )

        token_id = cast(UUID, reset_token["id"])

        await self._password_reset_repository.reset_password(
            user_id=user_id,
            token_id=token_id,
            hashed_password=hashed_password,
        )
