from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from prisma import Prisma
from prisma.actions import UserActions
from prisma.errors import RecordNotFoundError, UniqueViolationError
from prisma.models import User

from src.core.exceptions import ConflictError, NotFoundError
from src.modules.users.user_repository import UserRepository
from src.modules.users.user_schema import UserRole
from test.factories import make_user_row

USER_ID = UUID("00000000-0000-4000-8000-000000000001")
EMAIL = "ana@example.com"
HASHED = "hashed"
PRISMA_ERROR_DATA = {"user_facing_error": {"message": "prisma error"}}


def _row(**overrides: object) -> MagicMock:
    row = MagicMock(spec=User)
    row.model_dump.return_value = make_user_row(**overrides)
    return row


@pytest.fixture
def users() -> AsyncMock:
    return AsyncMock(spec=UserActions)


@pytest.fixture
def repository(users: AsyncMock) -> UserRepository:
    db = AsyncMock(spec=Prisma)
    db.user = users
    return UserRepository(db)


async def test_create_connects_role_and_returns_row(
    repository: UserRepository, users: AsyncMock
) -> None:
    users.create.return_value = _row(email=EMAIL)

    result = await repository.create(
        email=EMAIL, name="Ana", hashed_password=HASHED, role=UserRole.STAFF
    )

    data = users.create.call_args.kwargs["data"]
    assert data["role"] == {"connect": {"name": "STAFF"}}
    assert data["hashedPassword"] == HASHED
    assert result["email"] == EMAIL


async def test_create_raises_conflict_when_email_taken(
    repository: UserRepository, users: AsyncMock
) -> None:
    users.create.side_effect = UniqueViolationError(PRISMA_ERROR_DATA)

    with pytest.raises(ConflictError):
        await repository.create(
            email=EMAIL, name="Ana", hashed_password=HASHED, role=UserRole.ADMIN
        )


async def test_get_by_id_filters_soft_deleted(repository: UserRepository, users: AsyncMock) -> None:
    users.find_first.return_value = _row()

    result = await repository.get_by_id(USER_ID)

    assert users.find_first.call_args.kwargs["where"] == {"id": str(USER_ID), "deletedAt": None}
    assert result is not None


async def test_get_by_id_returns_none_when_missing(
    repository: UserRepository, users: AsyncMock
) -> None:
    users.find_first.return_value = None

    assert await repository.get_by_id(USER_ID) is None


async def test_get_by_email_returns_none_when_missing(
    repository: UserRepository, users: AsyncMock
) -> None:
    users.find_first.return_value = None

    assert await repository.get_by_email(EMAIL) is None

    assert users.find_first.call_args.kwargs["where"] == {"email": EMAIL, "deletedAt": None}


async def test_list_paginated_applies_skip_take_and_role_filter(
    repository: UserRepository, users: AsyncMock
) -> None:
    users.find_many.return_value = [_row(), _row()]
    users.count.return_value = 12

    items, total = await repository.list_paginated(page=3, page_size=5, role=UserRole.ADMIN)

    kwargs = users.find_many.call_args.kwargs
    assert kwargs["skip"] == 10
    assert kwargs["take"] == 5
    assert kwargs["where"]["role"] == {"is": {"name": "ADMIN"}}
    assert (len(items), total) == (2, 12)


async def test_list_paginated_without_role_filters_only_soft_deleted(
    repository: UserRepository, users: AsyncMock
) -> None:
    users.find_many.return_value = []
    users.count.return_value = 0

    await repository.list_paginated(page=1, page_size=20, role=None)

    assert users.find_many.call_args.kwargs["where"] == {"deletedAt": None}


async def test_update_sends_only_provided_fields(
    repository: UserRepository, users: AsyncMock
) -> None:
    users.update.return_value = _row()

    await repository.update(USER_ID, name="Ana Maria", role=UserRole.STAFF)

    assert users.update.call_args.kwargs["data"] == {
        "name": "Ana Maria",
        "role": {"connect": {"name": "STAFF"}},
    }


async def test_update_raises_not_found_when_prisma_returns_none(
    repository: UserRepository, users: AsyncMock
) -> None:
    users.update.return_value = None

    with pytest.raises(NotFoundError):
        await repository.update(USER_ID, name="Ana")


async def test_update_raises_conflict_when_email_taken(
    repository: UserRepository, users: AsyncMock
) -> None:
    users.update.side_effect = UniqueViolationError(PRISMA_ERROR_DATA)

    with pytest.raises(ConflictError):
        await repository.update(USER_ID, email=EMAIL)


async def test_soft_delete_sets_deleted_at(repository: UserRepository, users: AsyncMock) -> None:
    await repository.soft_delete(USER_ID)

    kwargs = users.update.call_args.kwargs
    assert kwargs["where"] == {"id": str(USER_ID)}
    assert kwargs["data"]["deletedAt"] is not None


async def test_soft_delete_raises_not_found_when_prisma_raises(
    repository: UserRepository, users: AsyncMock
) -> None:
    users.update.side_effect = RecordNotFoundError(PRISMA_ERROR_DATA)

    with pytest.raises(NotFoundError):
        await repository.soft_delete(USER_ID)
