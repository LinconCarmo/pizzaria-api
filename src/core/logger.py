import sys

from loguru import logger as _logger

from src.core.config import settings

logger = _logger

logger.remove()

logger.add(
    sys.stdout,
    level=settings.log_level.upper(),
    format=("{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"),
    colorize=settings.app_env == "development",
    serialize=settings.app_env == "production",
)

__all__ = ["logger"]
