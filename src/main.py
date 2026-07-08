from typing import cast

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.types import ExceptionHandler

from src.core.exceptions import (
    DomainError,
    domain_error_handler,
    generic_exception_handler,
    validation_exception_handler,
)
from src.core.middlewares import LoggingMiddleware
from src.infra.database import lifespan
from src.modules.auth.auth_controller import router as auth_router
from src.modules.health.router import router as health_router
from src.modules.users.user_router import router as users_router

app = FastAPI(lifespan=lifespan)

app.add_middleware(LoggingMiddleware)

app.add_exception_handler(
    DomainError,
    cast(ExceptionHandler, domain_error_handler),
)

app.add_exception_handler(
    RequestValidationError,
    cast(ExceptionHandler, validation_exception_handler),
)

app.add_exception_handler(
    Exception,
    generic_exception_handler,
)

app.include_router(health_router)
app.include_router(users_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
