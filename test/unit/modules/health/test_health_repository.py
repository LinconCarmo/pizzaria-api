from unittest.mock import AsyncMock

from prisma import Prisma

from src.modules.health.health_repository import HealthRepository


async def test_is_database_reachable_returns_true_when_query_succeeds() -> None:
    db = AsyncMock(spec=Prisma)
    db.query_raw.return_value = [{"1": 1}]

    assert await HealthRepository(db).is_database_reachable() is True


async def test_is_database_reachable_returns_false_when_query_fails() -> None:
    db = AsyncMock(spec=Prisma)
    db.query_raw.side_effect = ConnectionError("database down")

    assert await HealthRepository(db).is_database_reachable() is False
