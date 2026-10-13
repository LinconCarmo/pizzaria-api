from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from loguru import logger
from prisma import Prisma
from prisma.actions import RoleActions
from prisma.models import Role

from src.infra.database import lifespan, warn_if_roles_missing
from src.infra.seed import ROLES


def _role(name: str) -> MagicMock:
    role = MagicMock(spec=Role)
    role.name = name
    return role


def _db_with_roles(*names: str) -> AsyncMock:
    db = AsyncMock(spec=Prisma)
    db.role = AsyncMock(spec=RoleActions)
    db.role.find_many.return_value = [_role(name) for name in names]
    return db


def _capture_warnings() -> tuple[list[str], int]:
    messages: list[str] = []
    sink_id = logger.add(lambda m: messages.append(m.record["message"]), level="WARNING")
    return messages, sink_id


async def test_warn_if_roles_missing_logs_warning_when_seed_did_not_run() -> None:
    db = _db_with_roles("CUSTOMER")
    messages, sink_id = _capture_warnings()

    await warn_if_roles_missing(db)

    logger.remove(sink_id)
    assert messages == ["roles_not_seeded"]


async def test_warn_if_roles_missing_stays_silent_when_all_roles_exist() -> None:
    db = _db_with_roles(*(name for name, _ in ROLES))
    messages, sink_id = _capture_warnings()

    await warn_if_roles_missing(db)

    logger.remove(sink_id)
    assert messages == []


async def test_lifespan_does_not_write_to_database() -> None:
    db = _db_with_roles(*(name for name, _ in ROLES))

    with patch("src.infra.database.db", db):
        async with lifespan(FastAPI()):
            db.connect.assert_awaited_once()

    db.role.upsert.assert_not_awaited()
    db.disconnect.assert_awaited_once()


async def test_lifespan_disconnects_when_startup_check_fails() -> None:
    db = _db_with_roles()
    db.role.find_many.side_effect = RuntimeError("database error")

    with patch("src.infra.database.db", db), pytest.raises(RuntimeError):
        async with lifespan(FastAPI()):
            pass

    db.disconnect.assert_awaited_once()
