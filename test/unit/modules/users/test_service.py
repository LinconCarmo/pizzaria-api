from unittest.mock import AsyncMock

import pytest

from src.core.exceptions import ConflictError, NotFoundError
from src.modules.users.repository import UserRepositoryProtocol
from src.modules.users.schema import (
    UpdateUserRequest,
    UserListResponse,
    UserResponse,
    UserRole,
)
from src.modules.users.service import UserService
from test.factories import make_create_user_request, make_user_row


def _make_service() -> tuple[UserService, AsyncMock]:
    repo = AsyncMock(spec=UserRepositoryProtocol)
    service = UserService(repo)
    return service, repo


@pytest.mark.asyncio
async def test_create_hashes_password_and_calls_repository_when_valid():
    service, repo = _make_service()
    repo.create.return_value = make_user_row()
    data = make_create_user_request()

    result = await service.create(data)

    repo.create.assert_awaited_once()
    kwargs = repo.create.call_args.kwargs
    assert kwargs["email"] == "ana@example.com"
    assert kwargs["name"] == "Ana"
    assert kwargs["role"] == UserRole.CUSTOMER
    assert kwargs["hashed_password"] != "strongpass123"
    assert isinstance(result, UserResponse)


@pytest.mark.asyncio
async def test_create_propagates_conflict_when_repository_raises():
    service, repo = _make_service()
    repo.create.side_effect = ConflictError("dup")
    data = make_create_user_request()

    with pytest.raises(ConflictError):
        await service.create(data)


@pytest.mark.asyncio
async def test_get_by_id_returns_response_when_found():
    service, repo = _make_service()
    repo.get_by_id.return_value = make_user_row(id=42, email="x@y.com")

    result = await service.get_by_id(42)

    assert result.id == 42
    assert result.email == "x@y.com"


@pytest.mark.asyncio
async def test_get_by_id_raises_not_found_when_repository_returns_none():
    service, repo = _make_service()
    repo.get_by_id.return_value = None

    with pytest.raises(NotFoundError):
        await service.get_by_id(99)


@pytest.mark.asyncio
async def test_list_paginated_computes_total_pages_correctly():
    service, repo = _make_service()
    repo.list_paginated.return_value = ([make_user_row(id=i) for i in range(1, 21)], 45)

    result = await service.list_paginated(page=1, page_size=20, role=None)

    assert isinstance(result, UserListResponse)
    assert result.meta.total == 45
    assert result.meta.total_pages == 3
    assert len(result.items) == 20


@pytest.mark.asyncio
async def test_list_paginated_returns_zero_pages_when_empty():
    service, repo = _make_service()
    repo.list_paginated.return_value = ([], 0)

    result = await service.list_paginated(page=1, page_size=20, role=None)

    assert result.meta.total == 0
    assert result.meta.total_pages == 0
    assert result.items == []


@pytest.mark.asyncio
async def test_update_uses_exclude_unset_to_avoid_overwriting_unsent_fields():
    service, repo = _make_service()
    repo.update.return_value = make_user_row(name="Ana Maria")

    await service.update(1, UpdateUserRequest(name="Ana Maria"))

    repo.update.assert_awaited_once()
    _, payload = repo.update.call_args.args
    assert payload == {"name": "Ana Maria"}


@pytest.mark.asyncio
async def test_update_hashes_password_when_password_in_payload():
    service, repo = _make_service()
    repo.update.return_value = make_user_row()

    await service.update(1, UpdateUserRequest(password="brandnewpw"))

    _, payload = repo.update.call_args.args
    assert "password" not in payload
    assert "hashedPassword" in payload
    assert payload["hashedPassword"] != "brandnewpw"


@pytest.mark.asyncio
async def test_update_propagates_not_found_when_repository_raises():
    service, repo = _make_service()
    repo.update.side_effect = NotFoundError("x")

    with pytest.raises(NotFoundError):
        await service.update(1, UpdateUserRequest(name="X"))


@pytest.mark.asyncio
async def test_delete_calls_repository_soft_delete():
    service, repo = _make_service()

    await service.delete(7)

    repo.soft_delete.assert_awaited_once_with(7)


@pytest.mark.asyncio
async def test_delete_propagates_not_found_when_repository_raises():
    service, repo = _make_service()
    repo.soft_delete.side_effect = NotFoundError("x")

    with pytest.raises(NotFoundError):
        await service.delete(7)
