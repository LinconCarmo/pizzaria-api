from unittest.mock import AsyncMock

from prisma import Prisma
from prisma.actions import RoleActions, UnitActions

from src.infra.seed import DEFAULT_UNIT, ROLES, seed_roles, seed_unit


def _db() -> AsyncMock:
    db = AsyncMock(spec=Prisma)
    db.role = AsyncMock(spec=RoleActions)
    db.unit = AsyncMock(spec=UnitActions)
    return db


async def test_seed_roles_upserts_each_default_role():
    db = _db()

    await seed_roles(db)

    assert db.role.upsert.await_count == len(ROLES)
    seeded_names = {call.kwargs["where"]["name"] for call in db.role.upsert.await_args_list}
    assert seeded_names == {"CUSTOMER", "STAFF", "ADMIN"}


async def test_seed_roles_is_idempotent_with_empty_update():
    db = _db()

    await seed_roles(db)

    for call in db.role.upsert.await_args_list:
        assert call.kwargs["data"]["update"] == {}
        assert set(call.kwargs["data"]["create"]) == {"name", "description"}


async def test_seed_unit_upserts_default_unit():
    db = _db()

    await seed_unit(db)

    db.unit.upsert.assert_awaited_once()
    call = db.unit.upsert.await_args
    assert call.kwargs["where"] == {"cnpj": DEFAULT_UNIT["cnpj"]}
    assert call.kwargs["data"]["create"] == DEFAULT_UNIT


async def test_seed_unit_is_idempotent_with_empty_update():
    db = _db()

    await seed_unit(db)

    assert db.unit.upsert.await_args.kwargs["data"]["update"] == {}
