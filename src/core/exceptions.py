from typing import (
    Any,  # noqa: TID251 -- `details` carrega payload de erro arbitrário (JSON-serializável)
)

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from src.core.logger import logger


class ErrorDetail(BaseModel):
    code: str = Field(..., examples=["NOT_FOUND"])
    message: str = Field(..., examples=["Resource not found"])
    details: Any | None = Field(default=None)


class ErrorResponse(BaseModel):
    error: ErrorDetail


class DomainError(Exception):
    def __init__(
        self,
        message: str,
        code: str = "DOMAIN_ERROR",
        status_code: int = 400,
        details: Any | None = None,
    ) -> None:
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details


class NotFoundError(DomainError):
    def __init__(self, message: str = "Resource not found") -> None:
        super().__init__(
            message=message,
            code="NOT_FOUND",
            status_code=404,
        )


class ConflictError(DomainError):
    def __init__(self, message: str = "Conflict detected") -> None:
        super().__init__(
            message=message,
            code="CONFLICT",
            status_code=409,
        )


class BusinessValidationError(DomainError):
    def __init__(
        self,
        message: str = "Validation error",
        details: Any | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=422,
            details=details,
        )


class UnauthorizedError(DomainError):
    def __init__(self, message: str = "Unauthorized") -> None:
        super().__init__(
            message=message,
            code="UNAUTHORIZED",
            status_code=401,
        )


class InternalError(DomainError):
    """Invariante de servidor violada (bug/integridade), não erro do cliente."""

    def __init__(self, message: str = "Internal error") -> None:
        super().__init__(
            message=message,
            code="INTERNAL_ERROR",
            status_code=500,
        )


def error_response(error: DomainError) -> JSONResponse:
    return JSONResponse(
        status_code=error.status_code,
        content={
            "error": {
                "code": error.code,
                "message": error.message,
                "details": error.details,
            }
        },
    )


async def domain_error_handler(
    request: Request,
    exc: DomainError,
) -> JSONResponse:
    return error_response(exc)


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Validation failed",
                "details": exc.errors(),
            }
        },
    )


async def generic_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    logger.opt(exception=exc).error("unhandled_exception")
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "Internal server error",
                "details": None,
            }
        },
    )
