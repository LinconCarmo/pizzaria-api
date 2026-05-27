from datetime import UTC, datetime
from uuid import UUID

from prisma import Prisma, types
from prisma.models import User

from src.modules.users.user_schema import (
    CreateUserRequest,
    UpdateUserRequest,
    UserResponse,
    UserRole,
)

NOW = datetime(2026, 5, 20, 12, 0, 0, tzinfo=UTC)
DEFAULT_USER_ID = UUID("00000000-0000-4000-8000-000000000001")


def make_user_row(
    *,
    id: UUID = DEFAULT_USER_ID,
    email: str = "ana@example.com",
    name: str = "Ana",
    role_name: str | None = "CUSTOMER",
    is_active: bool = True,
    hashed_password: str = "hashed",
    created_at: datetime = NOW,
    updated_at: datetime = NOW,
    deleted_at: datetime | None = None,
) -> dict[str, object]:
    role: dict[str, object] | None = {"name": role_name} if role_name is not None else None
    return {
        "id": str(id),
        "email": email,
        "name": name,
        "role": role,
        "isActive": is_active,
        "hashedPassword": hashed_password,
        "createdAt": created_at,
        "updatedAt": updated_at,
        "deletedAt": deleted_at,
    }


def make_create_user_request(
    *,
    email: str = "ana@example.com",
    name: str = "Ana",
    password: str = "strongpass123",
    role: UserRole = UserRole.CUSTOMER,
) -> CreateUserRequest:
    return CreateUserRequest(email=email, name=name, password=password, role=role)


def make_update_user_request(**overrides: object) -> UpdateUserRequest:
    return UpdateUserRequest(**overrides)


def make_user_response(
    *,
    id: UUID = DEFAULT_USER_ID,
    email: str = "ana@example.com",
    name: str = "Ana",
    role: UserRole = UserRole.CUSTOMER,
    is_active: bool = True,
    created_at: datetime = NOW,
    updated_at: datetime = NOW,
) -> UserResponse:
    return UserResponse(
        id=id,
        email=email,
        name=name,
        role=role,
        is_active=is_active,
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
) -> User:
    data: types.UserCreateInput = {
        "email": email,
        "name": name,
        "hashedPassword": hashed_password,
        "role": {"connect": {"name": role}},
    }
    return await db.user.create(data=data)
