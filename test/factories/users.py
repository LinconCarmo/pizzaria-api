from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any, cast

from prisma import Prisma

from src.modules.users.schema import (
    CreateUserRequest,
    UpdateUserRequest,
    UserResponse,
    UserRole,
)

NOW = datetime(2026, 5, 20, 12, 0, 0, tzinfo=UTC)


def make_user_row(
    *,
    id: int = 1,
    email: str = "ana@example.com",
    name: str = "Ana",
    role: str = "CUSTOMER",
    hashed_password: str = "hashed",
    created_at: datetime = NOW,
    updated_at: datetime = NOW,
    deleted_at: datetime | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=id,
        email=email,
        name=name,
        role=role,
        hashedPassword=hashed_password,
        createdAt=created_at,
        updatedAt=updated_at,
        deletedAt=deleted_at,
    )


def make_create_user_request(
    *,
    email: str = "ana@example.com",
    name: str = "Ana",
    password: str = "strongpass123",
    role: UserRole = UserRole.CUSTOMER,
) -> CreateUserRequest:
    return CreateUserRequest(email=email, name=name, password=password, role=role)


def make_update_user_request(**overrides: Any) -> UpdateUserRequest:
    return UpdateUserRequest(**overrides)


def make_user_response(
    *,
    id: int = 1,
    email: str = "ana@example.com",
    name: str = "Ana",
    role: UserRole = UserRole.CUSTOMER,
    created_at: datetime = NOW,
    updated_at: datetime = NOW,
) -> UserResponse:
    return UserResponse(
        id=id,
        email=email,
        name=name,
        role=role,
        created_at=created_at,
        updated_at=updated_at,
    )


async def seed_user(
    db: Prisma,
    *,
    email: str = "user@example.com",
    name: str = "Default User",
    hashed_password: str = "hashed",
    role: str = "CUSTOMER",
    **overrides: Any,
) -> Any:
    data: dict[str, Any] = {
        "email": email,
        "name": name,
        "hashedPassword": hashed_password,
        "role": role,
        **overrides,
    }
    return await db.user.create(data=cast(Any, data))
