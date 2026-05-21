from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from src.core.logger import logger


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
    logger.exception("Unhandled exception", exc_info=exc)
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
