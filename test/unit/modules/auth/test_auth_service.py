from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock
from uuid import UUID

import pytest

from src.core.exceptions import (
    BadRequestError,
    FeatureUnavailableError,
    ForbiddenError,
    InternalError,
    TooManyRequestsError,
    UnauthorizedError,
)
from src.core.rate_limit import InMemoryRateLimiter
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
    RefreshTokenDto,
    ResetPasswordDto,
)
from src.modules.auth.auth_service import (
    FORGOT_PASSWORD_PER_EMAIL,
    LOGIN_FAILURES_PER_EMAIL,
    AuthService,
)
from src.modules.auth.password_reset_token_repository import (
    PasswordResetTokenRepositoryProtocol,
)
from src.modules.users.user_repository import UserRepositoryProtocol
from test.factories import make_password_reset_token_row, make_user_row

USER_ID = UUID("00000000-0000-4000-8000-000000000001")
EMAIL = "ana@example.com"
PASSWORD = "strongpass123"
WRONG_PASSWORD = "wrong-password"
NEW_PASSWORD = "n0v@s3nh@forte"
RESET_TOKEN = "plain-reset-token"
ROLE = "CUSTOMER"


@pytest.fixture(scope="module")
def hashed_password() -> str:
    return hash_password(PASSWORD)


@pytest.fixture
def users() -> AsyncMock:
    return AsyncMock(spec=UserRepositoryProtocol)


@pytest.fixture
def reset_tokens() -> AsyncMock:
    return AsyncMock(spec=PasswordResetTokenRepositoryProtocol)


@pytest.fixture
def email_service() -> AsyncMock:
    mock = AsyncMock(spec=EmailServiceProtocol)
    mock.is_available.return_value = True
    return mock


@pytest.fixture
def rate_limiter() -> InMemoryRateLimiter:
    return InMemoryRateLimiter()


@pytest.fixture
def service(
    users: AsyncMock,
    reset_tokens: AsyncMock,
    email_service: AsyncMock,
    rate_limiter: InMemoryRateLimiter,
) -> AuthService:
    return AuthService(users, reset_tokens, email_service, rate_limiter)


def _login(password: str = PASSWORD) -> LoginDto:
    return LoginDto(email=EMAIL, password=password)


# ---------------------------------------------------------------------------
# login
# ---------------------------------------------------------------------------


async def test_login_returns_tokens_when_credentials_valid(
    service: AuthService, users: AsyncMock, hashed_password: str
) -> None:
    users.get_by_email.return_value = make_user_row(id=USER_ID, hashed_password=hashed_password)

    result = await service.login(_login())

    assert result.user.id == USER_ID
    assert result.user.role == ROLE
    assert decode_token(result.access_token)["sub"] == str(USER_ID)
    assert decode_token(result.refresh_token)["token_type"] == "refresh"


async def test_login_raises_401_when_email_unknown(service: AuthService, users: AsyncMock) -> None:
    users.get_by_email.return_value = None

    with pytest.raises(UnauthorizedError):
        await service.login(_login())


async def test_login_raises_401_when_password_wrong(
    service: AuthService, users: AsyncMock, hashed_password: str
) -> None:
    users.get_by_email.return_value = make_user_row(hashed_password=hashed_password)

    with pytest.raises(UnauthorizedError):
        await service.login(_login(WRONG_PASSWORD))


async def test_login_raises_403_when_user_inactive(
    service: AuthService, users: AsyncMock, hashed_password: str
) -> None:
    users.get_by_email.return_value = make_user_row(
        hashed_password=hashed_password, is_active=False
    )

    with pytest.raises(ForbiddenError):
        await service.login(_login())


async def test_login_raises_500_when_role_relation_missing(
    service: AuthService, users: AsyncMock, hashed_password: str
) -> None:
    users.get_by_email.return_value = make_user_row(hashed_password=hashed_password, role_name=None)

    with pytest.raises(InternalError):
        await service.login(_login())


async def test_login_raises_429_after_max_failures_for_email(
    service: AuthService, users: AsyncMock, hashed_password: str
) -> None:
    users.get_by_email.return_value = make_user_row(hashed_password=hashed_password)
    for _ in range(LOGIN_FAILURES_PER_EMAIL.max_attempts):
        with pytest.raises(UnauthorizedError):
            await service.login(_login(WRONG_PASSWORD))

    with pytest.raises(TooManyRequestsError):
        await service.login(_login())


async def test_login_resets_failures_when_login_succeeds(
    service: AuthService,
    users: AsyncMock,
    hashed_password: str,
    rate_limiter: InMemoryRateLimiter,
) -> None:
    users.get_by_email.return_value = make_user_row(hashed_password=hashed_password)
    for _ in range(LOGIN_FAILURES_PER_EMAIL.max_attempts - 1):
        with pytest.raises(UnauthorizedError):
            await service.login(_login(WRONG_PASSWORD))

    await service.login(_login())

    rate_limiter.check(f"login:email:{EMAIL}", LOGIN_FAILURES_PER_EMAIL)


# ---------------------------------------------------------------------------
# refresh_token
# ---------------------------------------------------------------------------


async def test_refresh_token_returns_new_tokens_when_valid(
    service: AuthService, users: AsyncMock
) -> None:
    users.get_by_id.return_value = make_user_row(id=USER_ID)
    data = RefreshTokenDto(refresh_token=create_refresh_token(sub=str(USER_ID)))

    result = await service.refresh_token(data)

    users.get_by_id.assert_awaited_once_with(USER_ID)
    assert result.user.id == USER_ID


async def test_refresh_token_raises_401_when_token_is_access(service: AuthService) -> None:
    data = RefreshTokenDto(refresh_token=create_access_token(sub=str(USER_ID), role=ROLE))

    with pytest.raises(UnauthorizedError):
        await service.refresh_token(data)


async def test_refresh_token_raises_401_when_sub_not_uuid(service: AuthService) -> None:
    data = RefreshTokenDto(refresh_token=create_refresh_token(sub="not-a-uuid"))

    with pytest.raises(UnauthorizedError):
        await service.refresh_token(data)


async def test_refresh_token_raises_401_when_user_missing(
    service: AuthService, users: AsyncMock
) -> None:
    users.get_by_id.return_value = None
    data = RefreshTokenDto(refresh_token=create_refresh_token(sub=str(USER_ID)))

    with pytest.raises(UnauthorizedError):
        await service.refresh_token(data)


async def test_refresh_token_raises_403_when_user_inactive(
    service: AuthService, users: AsyncMock
) -> None:
    users.get_by_id.return_value = make_user_row(is_active=False)
    data = RefreshTokenDto(refresh_token=create_refresh_token(sub=str(USER_ID)))

    with pytest.raises(ForbiddenError):
        await service.refresh_token(data)


# ---------------------------------------------------------------------------
# forgot_password
# ---------------------------------------------------------------------------


async def test_forgot_password_replaces_token_and_sends_email_when_user_exists(
    service: AuthService, users: AsyncMock, reset_tokens: AsyncMock, email_service: AsyncMock
) -> None:
    users.get_by_email.return_value = make_user_row(id=USER_ID)

    await service.forgot_password(ForgotPasswordDto(email=EMAIL))

    reset_tokens.delete_by_user_id.assert_awaited_once_with(USER_ID)
    created = reset_tokens.create.call_args.kwargs
    sent = email_service.send_password_reset_email.call_args.kwargs
    assert created["user_id"] == USER_ID
    assert created["token_hash"] == hash_reset_token(sent["token"])
    assert sent["email"] == EMAIL


async def test_forgot_password_does_nothing_when_email_unknown(
    service: AuthService, users: AsyncMock, reset_tokens: AsyncMock, email_service: AsyncMock
) -> None:
    users.get_by_email.return_value = None

    await service.forgot_password(ForgotPasswordDto(email=EMAIL))

    reset_tokens.create.assert_not_awaited()
    email_service.send_password_reset_email.assert_not_awaited()


async def test_forgot_password_raises_503_before_lookup_when_email_unavailable(
    service: AuthService, users: AsyncMock, reset_tokens: AsyncMock, email_service: AsyncMock
) -> None:
    email_service.is_available.return_value = False

    with pytest.raises(FeatureUnavailableError):
        await service.forgot_password(ForgotPasswordDto(email=EMAIL))

    users.get_by_email.assert_not_awaited()
    reset_tokens.create.assert_not_awaited()


async def test_forgot_password_raises_429_after_max_requests_for_email(
    service: AuthService, users: AsyncMock
) -> None:
    users.get_by_email.return_value = None
    for _ in range(FORGOT_PASSWORD_PER_EMAIL.max_attempts):
        await service.forgot_password(ForgotPasswordDto(email=EMAIL))

    with pytest.raises(TooManyRequestsError):
        await service.forgot_password(ForgotPasswordDto(email=EMAIL))


# ---------------------------------------------------------------------------
# reset_password
# ---------------------------------------------------------------------------


def _reset(token: str = RESET_TOKEN) -> ResetPasswordDto:
    return ResetPasswordDto(token=token, new_password=NEW_PASSWORD)


async def test_reset_password_updates_password_when_token_valid(
    service: AuthService, users: AsyncMock, reset_tokens: AsyncMock
) -> None:
    token_row = make_password_reset_token_row(user_id=USER_ID)
    reset_tokens.get_by_token_hash.return_value = token_row
    users.get_by_id.return_value = make_user_row(id=USER_ID)

    await service.reset_password(_reset())

    reset_tokens.get_by_token_hash.assert_awaited_once_with(
        token_hash=hash_reset_token(RESET_TOKEN)
    )
    kwargs = reset_tokens.reset_password.call_args.kwargs
    assert kwargs["user_id"] == USER_ID
    assert kwargs["token_id"] == UUID(str(token_row["id"]))
    assert verify_password(NEW_PASSWORD, kwargs["hashed_password"])


async def test_reset_password_raises_400_when_token_unknown(
    service: AuthService, reset_tokens: AsyncMock
) -> None:
    reset_tokens.get_by_token_hash.return_value = None

    with pytest.raises(BadRequestError):
        await service.reset_password(_reset())


async def test_reset_password_raises_400_when_token_already_used(
    service: AuthService, reset_tokens: AsyncMock
) -> None:
    reset_tokens.get_by_token_hash.return_value = make_password_reset_token_row(
        used_at=datetime.now(UTC)
    )

    with pytest.raises(BadRequestError):
        await service.reset_password(_reset())


async def test_reset_password_raises_400_when_token_expired(
    service: AuthService, reset_tokens: AsyncMock
) -> None:
    reset_tokens.get_by_token_hash.return_value = make_password_reset_token_row(
        expires_at=datetime.now(UTC) - timedelta(minutes=1)
    )

    with pytest.raises(BadRequestError):
        await service.reset_password(_reset())


async def test_reset_password_raises_400_when_user_missing(
    service: AuthService, users: AsyncMock, reset_tokens: AsyncMock
) -> None:
    reset_tokens.get_by_token_hash.return_value = make_password_reset_token_row()
    users.get_by_id.return_value = None

    with pytest.raises(BadRequestError):
        await service.reset_password(_reset())


async def test_reset_password_raises_403_when_user_inactive(
    service: AuthService, users: AsyncMock, reset_tokens: AsyncMock
) -> None:
    reset_tokens.get_by_token_hash.return_value = make_password_reset_token_row()
    users.get_by_id.return_value = make_user_row(is_active=False)

    with pytest.raises(ForbiddenError):
        await service.reset_password(_reset())

    reset_tokens.reset_password.assert_not_awaited()
