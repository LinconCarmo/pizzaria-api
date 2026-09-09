from unittest.mock import AsyncMock
from uuid import UUID

import pytest

from src.core.exceptions import ConflictError, NotFoundError
from src.modules.units.unit_repository import UnitRepositoryProtocol
from src.modules.units.unit_schema import (
    UnitListResponse,
    UnitResponse,
    UpdateUnitRequest,
)
from src.modules.units.unit_service import UnitService
from test.factories import (
    make_create_unit_request,
    make_unit_row,
)

UNIT_ID = UUID("00000000-0000-4000-8000-000000000002")
OTHER_UNIT_ID = UUID("00000000-0000-4000-8000-000000000042")
NON_EXISTENT_ID = UUID("00000000-0000-4000-8000-0000000000ff")


@pytest.fixture
def repo() -> AsyncMock:
    return AsyncMock(spec=UnitRepositoryProtocol)


@pytest.fixture
def service(repo: AsyncMock) -> UnitService:
    return UnitService(repo)


async def test_create_returns_response_when_valid(service: UnitService, repo: AsyncMock):
    repo.create.return_value = make_unit_row()
    data = make_create_unit_request()

    result = await service.create(data)

    repo.create.assert_awaited_once()
    kwargs = repo.create.call_args.kwargs

    assert kwargs["name"] == data.name
    assert kwargs["cnpj"] == data.cnpj
    assert kwargs["email"] == str(data.email)
    assert kwargs["phone"] == data.phone
    assert kwargs["street"] == data.street
    assert kwargs["number"] == data.number
    assert kwargs["neighborhood"] == data.neighborhood
    assert kwargs["city"] == data.city
    assert kwargs["state"] == data.state
    assert kwargs["zip"] == data.zip

    assert isinstance(result, UnitResponse)


async def test_create_propagates_conflict_when_repository_raises(
    service: UnitService, repo: AsyncMock
):
    repo.create.side_effect = ConflictError("dup")
    data = make_create_unit_request()

    with pytest.raises(ConflictError):
        await service.create(data)


async def test_get_by_id_returns_response_when_found(service: UnitService, repo: AsyncMock):
    repo.get_by_id.return_value = make_unit_row(
        id=OTHER_UNIT_ID,
        email="other@pizzaria.com",
    )

    result = await service.get_by_id(OTHER_UNIT_ID)

    assert result.id == OTHER_UNIT_ID
    assert result.email == "other@pizzaria.com"


async def test_get_by_id_raises_not_found_when_repository_returns_none(
    service: UnitService, repo: AsyncMock
):
    repo.get_by_id.return_value = None

    with pytest.raises(NotFoundError):
        await service.get_by_id(NON_EXISTENT_ID)


async def test_list_paginated_computes_total_pages_correctly(service: UnitService, repo: AsyncMock):
    repo.list_paginated.return_value = (
        [make_unit_row(id=UNIT_ID) for _ in range(20)],
        45,
    )

    result = await service.list_paginated(page=1, page_size=20)

    assert isinstance(result, UnitListResponse)
    assert result.meta.total == 45
    assert result.meta.total_pages == 3
    assert len(result.items) == 20


async def test_list_paginated_returns_zero_pages_when_empty(service: UnitService, repo: AsyncMock):
    repo.list_paginated.return_value = ([], 0)

    result = await service.list_paginated(page=1, page_size=20)

    assert result.meta.total == 0
    assert result.meta.total_pages == 0
    assert result.items == []


async def test_update_uses_exclude_unset_to_avoid_overwriting_unsent_fields(
    service: UnitService, repo: AsyncMock
):
    repo.get_by_id.return_value = make_unit_row()
    repo.update.return_value = make_unit_row(name="Unidade Nova")

    await service.update(
        UNIT_ID,
        UpdateUnitRequest(name="Unidade Nova"),
    )

    repo.update.assert_awaited_once()
    kwargs = repo.update.call_args.kwargs

    assert kwargs == {"name": "Unidade Nova"}


async def test_update_raises_not_found_when_get_by_id_returns_none(
    service: UnitService, repo: AsyncMock
):
    repo.get_by_id.return_value = None

    with pytest.raises(NotFoundError):
        await service.update(
            UNIT_ID,
            UpdateUnitRequest(name="Unidade Nova"),
        )

    repo.update.assert_not_awaited()


async def test_delete_calls_repository_soft_delete(service: UnitService, repo: AsyncMock):
    repo.get_by_id.return_value = make_unit_row()

    await service.delete(UNIT_ID)

    repo.soft_delete.assert_awaited_once_with(UNIT_ID)


async def test_delete_raises_not_found_when_get_by_id_returns_none(
    service: UnitService, repo: AsyncMock
):
    repo.get_by_id.return_value = None

    with pytest.raises(NotFoundError):
        await service.delete(UNIT_ID)

    repo.soft_delete.assert_not_awaited()


async def test_get_current_returns_first_active_unit(service: UnitService, repo: AsyncMock):
    repo.list_paginated.return_value = (
        [make_unit_row(id=UNIT_ID)],
        1,
    )

    result = await service.get_current()

    assert isinstance(result, UnitResponse)
    assert result.id == UNIT_ID
    repo.list_paginated.assert_awaited_once_with(page=1, page_size=1)


async def test_get_current_raises_not_found_when_no_unit_exists(
    service: UnitService, repo: AsyncMock
):
    repo.list_paginated.return_value = ([], 0)

    with pytest.raises(NotFoundError):
        await service.get_current()
