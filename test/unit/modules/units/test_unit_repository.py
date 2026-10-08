from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from prisma import Prisma
from prisma.actions import UnitActions
from prisma.errors import UniqueViolationError
from prisma.models import Unit

from src.core.exceptions import ConflictError, NotFoundError
from src.modules.units.unit_repository import UnitRepository
from test.factories import make_unit_row

UNIT_ID = UUID("00000000-0000-4000-8000-000000000002")
CNPJ = "12345678000195"
PRISMA_ERROR_DATA = {"user_facing_error": {"message": "prisma error"}}
CREATE_FIELDS: dict[str, str] = {
    "name": "Unidade Principal",
    "cnpj": CNPJ,
    "email": "contato@pizzaria.com",
    "phone": "41999999999",
    "street": "Rua Principal",
    "number": "100",
    "neighborhood": "Centro",
    "city": "Curitiba",
    "state": "PR",
    "zip": "80000000",
}


def _row(**overrides: object) -> MagicMock:
    row = MagicMock(spec=Unit)
    row.model_dump.return_value = make_unit_row(**overrides)
    return row


@pytest.fixture
def units() -> AsyncMock:
    return AsyncMock(spec=UnitActions)


@pytest.fixture
def repository(units: AsyncMock) -> UnitRepository:
    db = AsyncMock(spec=Prisma)
    db.unit = units
    return UnitRepository(db)


async def test_create_persists_fields_and_returns_row(
    repository: UnitRepository, units: AsyncMock
) -> None:
    units.create.return_value = _row(cnpj=CNPJ)

    result = await repository.create(**CREATE_FIELDS)

    assert units.create.call_args.kwargs["data"] == CREATE_FIELDS
    assert result["cnpj"] == CNPJ


async def test_create_raises_conflict_when_cnpj_taken(
    repository: UnitRepository, units: AsyncMock
) -> None:
    units.create.side_effect = UniqueViolationError(PRISMA_ERROR_DATA)

    with pytest.raises(ConflictError):
        await repository.create(**CREATE_FIELDS)


async def test_get_by_id_returns_none_when_missing(
    repository: UnitRepository, units: AsyncMock
) -> None:
    units.find_first.return_value = None

    assert await repository.get_by_id(UNIT_ID) is None

    assert units.find_first.call_args.kwargs["where"] == {"id": str(UNIT_ID), "deletedAt": None}


async def test_get_by_id_returns_row_when_found(
    repository: UnitRepository, units: AsyncMock
) -> None:
    units.find_first.return_value = _row(id=UNIT_ID)

    result = await repository.get_by_id(UNIT_ID)

    assert result is not None
    assert result["id"] == str(UNIT_ID)


async def test_list_paginated_hides_inactive_by_default(
    repository: UnitRepository, units: AsyncMock
) -> None:
    units.find_many.return_value = [_row()]
    units.count.return_value = 1

    items, total = await repository.list_paginated(page=2, page_size=10)

    kwargs = units.find_many.call_args.kwargs
    assert kwargs["where"] == {"deletedAt": None, "isActive": True}
    assert kwargs["skip"] == 10
    assert (len(items), total) == (1, 1)


async def test_list_paginated_includes_inactive_when_requested(
    repository: UnitRepository, units: AsyncMock
) -> None:
    units.find_many.return_value = []
    units.count.return_value = 0

    await repository.list_paginated(page=1, page_size=10, include_inactive=True)

    assert units.find_many.call_args.kwargs["where"] == {"deletedAt": None}


async def test_update_sends_only_provided_fields(
    repository: UnitRepository, units: AsyncMock
) -> None:
    units.find_first.return_value = _row()
    units.update.return_value = _row(name="Nova")

    result = await repository.update(UNIT_ID, name="Nova", is_active=False)

    assert units.update.call_args.kwargs["data"] == {"name": "Nova", "isActive": False}
    assert result["name"] == "Nova"


async def test_update_raises_not_found_when_unit_missing(
    repository: UnitRepository, units: AsyncMock
) -> None:
    units.find_first.return_value = None

    with pytest.raises(NotFoundError):
        await repository.update(UNIT_ID, name="Nova")

    units.update.assert_not_awaited()


async def test_update_raises_not_found_when_prisma_returns_none(
    repository: UnitRepository, units: AsyncMock
) -> None:
    units.find_first.return_value = _row()
    units.update.return_value = None

    with pytest.raises(NotFoundError):
        await repository.update(UNIT_ID, name="Nova")


async def test_update_raises_conflict_when_cnpj_taken(
    repository: UnitRepository, units: AsyncMock
) -> None:
    units.find_first.return_value = _row()
    units.update.side_effect = UniqueViolationError(PRISMA_ERROR_DATA)

    with pytest.raises(ConflictError):
        await repository.update(UNIT_ID, cnpj=CNPJ)


async def test_soft_delete_sets_deleted_at(repository: UnitRepository, units: AsyncMock) -> None:
    units.find_first.return_value = _row()

    await repository.soft_delete(UNIT_ID)

    assert units.update.call_args.kwargs["data"]["deletedAt"] is not None


async def test_soft_delete_raises_not_found_when_unit_missing(
    repository: UnitRepository, units: AsyncMock
) -> None:
    units.find_first.return_value = None

    with pytest.raises(NotFoundError):
        await repository.soft_delete(UNIT_ID)

    units.update.assert_not_awaited()
