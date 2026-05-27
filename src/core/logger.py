import sys
from collections.abc import Mapping
from contextvars import ContextVar
from typing import (
    TYPE_CHECKING,
    Any,  # noqa: TID251 -- `_redact` percorre valores de log de tipo arbitrário
)

from loguru import logger as _logger

from src.core.config import settings

if TYPE_CHECKING:
    from loguru import Record

logger = _logger

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)

SENSITIVE_KEYS: frozenset[str] = frozenset(
    {
        "password",
        "passwd",
        "token",
        "access_token",
        "refresh_token",
        "authorization",
        "api_key",
        "secret",
        "cpf",
        "cnpj",
        "rg",
        "card",
        "card_number",
        "cvv",
        "ccv",
        "pan",
        "email",
        "phone",
        "telefone",
        "address",
        "endereco",
    }
)

REDACTED = "***"


def _redact(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            k: (REDACTED if isinstance(k, str) and k.lower() in SENSITIVE_KEYS else _redact(v))
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [_redact(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_redact(item) for item in value)
    return value


def _patcher(record: "Record") -> None:
    extra = record.get("extra")
    if isinstance(extra, dict):
        redacted = {
            k: (REDACTED if isinstance(k, str) and k.lower() in SENSITIVE_KEYS else _redact(v))
            for k, v in extra.items()
        }
        record["extra"] = redacted
        extra = redacted

        request_id = request_id_var.get()
        if request_id is not None and "request_id" not in extra:
            extra["request_id"] = request_id


logger.remove()

logger.configure(patcher=_patcher)

logger.add(
    sys.stdout,
    level=settings.log_level.upper(),
    format=("{time:YYYY-MM-DD HH:mm:ss} | {level} | {message} | {extra}"),
    colorize=settings.app_env == "development",
    serialize=settings.app_env == "production",
)

__all__ = ["SENSITIVE_KEYS", "logger", "request_id_var"]
