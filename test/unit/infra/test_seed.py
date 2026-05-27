from unittest.mock import AsyncMock

from prisma import Prisma

from src.infra.seed import ROLES, seed_roles


async def test_seed_roles_upserts_each_default_role():
    db = AsyncMock(spec=Prisma)
    db.role.upsert = AsyncMock()

    await seed_roles(db)

    assert db.role.upsert.await_count == len(ROLES)
    seeded_names = {call.kwargs["where"]["name"] for call in db.role.upsert.await_args_list}
    assert seeded_names == {"CUSTOMER", "STAFF", "ADMIN"}


async def test_seed_roles_is_idempotent_with_empty_update():
    db = AsyncMock(spec=Prisma)
    db.role.upsert = AsyncMock()

    await seed_roles(db)

    for call in db.role.upsert.await_args_list:
        assert call.kwargs["data"]["update"] == {}
        assert set(call.kwargs["data"]["create"]) == {"name", "description"}
