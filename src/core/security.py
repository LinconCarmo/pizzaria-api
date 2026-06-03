from datetime import UTC, datetime, timedelta
from typing import cast

from jose import JWTError, jwt
from passlib.context import CryptContext

from src.core.config import settings
from src.core.exceptions import UnauthorizedError

_pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_password(plain: str) -> str:
    return cast(str, _pwd_context.hash(plain))


def verify_password(plain: str, hashed: str) -> bool:
    return cast(bool, _pwd_context.verify(plain, hashed))


def create_access_token(sub: str, role: str, exp_min: int = 15) -> str:

    payload = {"sub": sub, "role": role, "exp": datetime.now(UTC) + timedelta(minutes=exp_min)}

    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def create_refresh_token(sub: str, exp_days: int = 7) -> str:
    payload = {"sub": sub, "exp": datetime.now(UTC) + timedelta(days=exp_days)}
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_token(token: str) -> dict[str, object]:
    try:
        payload = cast(
            dict[str, object], jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        )
        return payload
    except JWTError as exc:
        raise UnauthorizedError("Invalid or expired token") from exc
