from uuid import uuid4

import pytest
from fastapi.security import HTTPAuthorizationCredentials

from src.core.exceptions import ForbiddenError, UnauthorizedError
from src.core.security import create_access_token, create_refresh_token
from src.core.security_dependencies import (
    AuthenticatedUser,
    get_current_user,
    require_role,
)


def _credentials(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


def test_get_current_user_returns_user_for_valid_access_token() -> None:
    user_id = uuid4()
    token = create_access_token(sub=str(user_id), role="ADMIN")

    user = get_current_user(_credentials(token))

    assert user.user_id == user_id
    assert user.role == "ADMIN"


def test_get_current_user_raises_when_credentials_missing() -> None:
    with pytest.raises(UnauthorizedError):
        get_current_user(None)


def test_get_current_user_raises_when_token_type_is_refresh() -> None:
    token = create_refresh_token(sub=str(uuid4()))

    with pytest.raises(UnauthorizedError):
        get_current_user(_credentials(token))


def test_get_current_user_raises_when_token_is_invalid() -> None:
    with pytest.raises(UnauthorizedError):
        get_current_user(_credentials("not-a-jwt"))


def test_get_current_user_raises_when_token_is_expired() -> None:
    token = create_access_token(sub=str(uuid4()), role="ADMIN", exp_min=-1)

    with pytest.raises(UnauthorizedError):
        get_current_user(_credentials(token))


def test_require_role_allows_matching_role() -> None:
    guard = require_role("ADMIN")
    user = AuthenticatedUser(user_id=uuid4(), role="ADMIN")

    assert guard(user) is user


def test_require_role_raises_forbidden_for_other_role() -> None:
    guard = require_role("ADMIN")
    user = AuthenticatedUser(user_id=uuid4(), role="CUSTOMER")

    with pytest.raises(ForbiddenError):
        guard(user)
