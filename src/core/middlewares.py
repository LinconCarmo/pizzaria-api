from time import perf_counter
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware

from src.core.logger import logger


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        request_id = str(uuid4())

        logger.info(
            f"Request started | "
            f"request_id={request_id} "
            f"method={request.method} "
            f"path={request.url.path}"
        )

        start_time = perf_counter()

        response = await call_next(request)

        duration = (perf_counter() - start_time) * 1000

        logger.info(
            f"Request finished | "
            f"request_id={request_id} "
            f"method={request.method} "
            f"path={request.url.path} "
            f"status={response.status_code} "
            f"duration_ms={duration:.2f}"
        )

        response.headers["X-Request-ID"] = request_id

        return response