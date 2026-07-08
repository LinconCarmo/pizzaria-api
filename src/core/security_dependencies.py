from collections.abc import Callable
from typing import Annotated
from uuid import UUID

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from src.core.exceptions import ForbiddenError, UnauthorizedError
from src.core.security import decode_token

_bearer_scheme = HTTPBearer(auto_error=False)


class AuthenticatedUser(BaseModel):
    user_id: UUID
    role: str


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)],
) -> AuthenticatedUser:
    if credentials is None:
        raise UnauthorizedError("Missing bearer token")

    payload = decode_token(credentials.credentials)

    if payload.get("token_type") != "access":
        raise UnauthorizedError("Invalid token type")

    sub = payload.get("sub")
    role = payload.get("role")
    if not isinstance(sub, str) or not isinstance(role, str):
        raise UnauthorizedError("Invalid token payload")

    return AuthenticatedUser(user_id=UUID(sub), role=role)


def require_role(*allowed: str) -> Callable[[AuthenticatedUser], AuthenticatedUser]:
    def _guard(
        user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    ) -> AuthenticatedUser:
        if user.role not in allowed:
            raise ForbiddenError("Insufficient permissions")
        return user

    return _guard
