from typing import Protocol

from prisma import Prisma

from src.core.logger import logger


class HealthRepositoryProtocol(Protocol):
    async def is_database_reachable(self) -> bool: ...


class HealthRepository:
    def __init__(self, db: Prisma) -> None:
        self._db = db

    async def is_database_reachable(self) -> bool:
        try:
            await self._db.query_raw("SELECT 1")
        except Exception:
            logger.exception("database_unreachable")
            return False
        return True
