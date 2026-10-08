from datetime import UTC, datetime, timedelta

import pytest
from fastapi.security import HTTPAuthorizationCredentials
from jose import jwt

from src.core.config import settings
from src.core.exceptions import ForbiddenError, UnauthorizedError
from src.core.security import create_access_token, create_refresh_token
from src.modules.auth.auth_dependencies import get_current_user, require_admin

USER_ID = "00000000-0000-4000-8000-000000000001"


def _credentials(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


def test_get_current_user_returns_claims_when_token_valid() -> None:
    token = create_access_token(sub=USER_ID, role="ADMIN")

    user = get_current_user(_credentials(token))

    assert user == {"sub": USER_ID, "role": "ADMIN"}


def test_get_current_user_raises_401_when_credentials_missing() -> None:
    with pytest.raises(UnauthorizedError):
        get_current_user(None)


def test_get_current_user_raises_401_when_token_is_refresh() -> None:
    token = create_refresh_token(sub=USER_ID)

    with pytest.raises(UnauthorizedError):
        get_current_user(_credentials(token))


def test_get_current_user_raises_401_when_claims_malformed() -> None:
    token = jwt.encode(
        {
            "sub": USER_ID,
            "token_type": "access",
            "exp": datetime.now(UTC) + timedelta(minutes=15),
        },
        settings.jwt_secret,
        algorithm="HS256",
    )

    with pytest.raises(UnauthorizedError):
        get_current_user(_credentials(token))


def test_require_admin_returns_user_when_role_is_admin() -> None:
    user = {"sub": USER_ID, "role": "ADMIN"}

    assert require_admin(user) == user


def test_require_admin_raises_403_when_role_is_not_admin() -> None:
    with pytest.raises(ForbiddenError):
        require_admin({"sub": USER_ID, "role": "STAFF"})
