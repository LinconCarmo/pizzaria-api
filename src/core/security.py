import hashlib
from datetime import UTC, datetime, timedelta

import jwt
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher

from src.core.config import settings
from src.core.exceptions import UnauthorizedError

_password_hash = PasswordHash((Argon2Hasher(),))


def hash_password(plain: str) -> str:
    return _password_hash.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _password_hash.verify(plain, hashed)


def hash_reset_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_access_token(sub: str, role: str, exp_min: int = 15) -> str:
    payload = {
        "sub": sub,
        "role": role,
        "token_type": "access",
        "exp": datetime.now(UTC) + timedelta(minutes=exp_min),
    }

    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def create_refresh_token(sub: str, exp_days: int = 7) -> str:
    payload = {
        "sub": sub,
        "token_type": "refresh",
        "exp": datetime.now(UTC) + timedelta(days=exp_days),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_token(token: str) -> dict[str, object]:
    try:
        payload: dict[str, object] = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        return payload
    except jwt.PyJWTError as exc:
        raise UnauthorizedError("Invalid or expired token") from exc
