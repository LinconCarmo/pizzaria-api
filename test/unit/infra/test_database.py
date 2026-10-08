from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from prisma import Prisma

from src.infra.database import lifespan


async def test_lifespan_disconnects_when_seed_fails() -> None:
    db = AsyncMock(spec=Prisma)
    seed = AsyncMock(side_effect=RuntimeError("seed failed"))

    with (
        patch("src.infra.database.db", db),
        patch("src.infra.database.seed_roles", seed),
        pytest.raises(RuntimeError),
    ):
        async with lifespan(FastAPI()):
            pass

    db.disconnect.assert_awaited_once()


async def test_lifespan_connects_seeds_and_disconnects() -> None:
    db = AsyncMock(spec=Prisma)
    seed = AsyncMock()

    with patch("src.infra.database.db", db), patch("src.infra.database.seed_roles", seed):
        async with lifespan(FastAPI()):
            db.connect.assert_awaited_once()
            seed.assert_awaited_once_with(db)

    db.disconnect.assert_awaited_once()
