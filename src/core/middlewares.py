from collections.abc import Awaitable, Callable
from time import perf_counter
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from src.core.logger import logger, request_id_var


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id = str(uuid4())
        token = request_id_var.set(request_id)

        try:
            logger.bind(
                method=request.method,
                path=request.url.path,
            ).info("request_started")

            start_time = perf_counter()
            response = await call_next(request)
            duration_ms = round((perf_counter() - start_time) * 1000, 2)

            logger.bind(
                method=request.method,
                path=request.url.path,
                status=response.status_code,
                duration_ms=duration_ms,
            ).info("request_finished")

            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            request_id_var.reset(token)
