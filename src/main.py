from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError

from src.core.exceptions import (
    DomainError,
    NotFoundError,
    domain_error_handler,
    generic_exception_handler,
    validation_exception_handler,
)
from src.core.middlewares import LoggingMiddleware
from src.infra.database import lifespan
from src.modules.health.controller import router as health_router

app = FastAPI(
    lifespan=lifespan
)

app.add_middleware(LoggingMiddleware)

app.add_exception_handler(
    DomainError,
    domain_error_handler,
)

app.add_exception_handler(
    RequestValidationError,
    validation_exception_handler,
)

app.add_exception_handler(
    Exception,
    generic_exception_handler,
)

app.include_router(health_router)


@app.get("/")
def root():
    return {"message": "Pizzaria API"}

