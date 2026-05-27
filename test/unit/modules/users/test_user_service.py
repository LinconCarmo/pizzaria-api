from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest

from src.core.exceptions import ConflictError, InternalError, NotFoundError
from src.modules.users.user_repository import UserRepositoryProtocol
from src.modules.users.user_schema import (
    UpdateUserRequest,
    UserListResponse,
    UserResponse,
    UserRole,
)
from src.modules.users.user_service import UserService
from test.factories import make_create_user_request, make_user_row

USER_ID = UUID("00000000-0000-4000-8000-000000000001")
OTHER_USER_ID = UUID("00000000-0000-4000-8000-000000000042")
NON_EXISTENT_ID = UUID("00000000-0000-4000-8000-0000000000ff")


@pytest.fixture
def repo() -> AsyncMock:
    return AsyncMock(spec=UserRepositoryProtocol)


@pytest.fixture
def service(repo: AsyncMock) -> UserService:
    return UserService(repo)


async def test_create_hashes_password_and_calls_repository_when_valid(
    service: UserService, repo: AsyncMock
):
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


async def test_create_propagates_conflict_when_repository_raises(
    service: UserService, repo: AsyncMock
):
    repo.create.side_effect = ConflictError("dup")
    data = make_create_user_request()

    with pytest.raises(ConflictError):
        await service.create(data)


async def test_get_by_id_returns_response_when_found(service: UserService, repo: AsyncMock):
    repo.get_by_id.return_value = make_user_row(id=OTHER_USER_ID, email="x@y.com")

    result = await service.get_by_id(OTHER_USER_ID)

    assert result.id == OTHER_USER_ID
    assert result.email == "x@y.com"


async def test_get_by_id_raises_not_found_when_repository_returns_none(
    service: UserService, repo: AsyncMock
):
    repo.get_by_id.return_value = None

    with pytest.raises(NotFoundError):
        await service.get_by_id(NON_EXISTENT_ID)


async def test_to_response_raises_internal_error_when_role_relation_missing(
    service: UserService, repo: AsyncMock
):
    repo.get_by_id.return_value = make_user_row(role_name=None)

    with pytest.raises(InternalError) as exc_info:
        await service.get_by_id(USER_ID)

    assert exc_info.value.status_code == 500
    assert exc_info.value.code == "INTERNAL_ERROR"
    assert exc_info.value.message == "Internal error"


async def test_list_paginated_computes_total_pages_correctly(service: UserService, repo: AsyncMock):
    repo.list_paginated.return_value = ([make_user_row(id=uuid4()) for _ in range(20)], 45)

    result = await service.list_paginated(page=1, page_size=20, role=None)

    assert isinstance(result, UserListResponse)
    assert result.meta.total == 45
    assert result.meta.total_pages == 3
    assert len(result.items) == 20


async def test_list_paginated_returns_zero_pages_when_empty(service: UserService, repo: AsyncMock):
    repo.list_paginated.return_value = ([], 0)

    result = await service.list_paginated(page=1, page_size=20, role=None)

    assert result.meta.total == 0
    assert result.meta.total_pages == 0
    assert result.items == []


async def test_update_uses_exclude_unset_to_avoid_overwriting_unsent_fields(
    service: UserService, repo: AsyncMock
):
    repo.get_by_id.return_value = make_user_row()
    repo.update.return_value = make_user_row(name="Ana Maria")

    await service.update(USER_ID, UpdateUserRequest(name="Ana Maria"))

    repo.update.assert_awaited_once()
    kwargs = repo.update.call_args.kwargs
    assert kwargs == {"name": "Ana Maria"}


async def test_update_hashes_password_when_password_in_payload(
    service: UserService, repo: AsyncMock
):
    repo.get_by_id.return_value = make_user_row()
    repo.update.return_value = make_user_row()

    await service.update(USER_ID, UpdateUserRequest(password="brandnewpw"))

    kwargs = repo.update.call_args.kwargs
    assert "password" not in kwargs
    assert "hashed_password" in kwargs
    assert kwargs["hashed_password"] != "brandnewpw"


async def test_update_raises_not_found_when_get_by_id_returns_none(
    service: UserService, repo: AsyncMock
):
    repo.get_by_id.return_value = None

    with pytest.raises(NotFoundError):
        await service.update(USER_ID, UpdateUserRequest(name="X"))

    repo.update.assert_not_awaited()


async def test_delete_calls_repository_soft_delete(service: UserService, repo: AsyncMock):
    repo.get_by_id.return_value = make_user_row()

    await service.delete(USER_ID)

    repo.soft_delete.assert_awaited_once_with(USER_ID)


async def test_delete_raises_not_found_when_get_by_id_returns_none(
    service: UserService, repo: AsyncMock
):
    repo.get_by_id.return_value = None

    with pytest.raises(NotFoundError):
        await service.delete(USER_ID)

    repo.soft_delete.assert_not_awaited()
