from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

from prisma import Prisma, types
from prisma.errors import RecordNotFoundError, UniqueViolationError

from src.core.exceptions import ConflictError, NotFoundError
from src.modules.users.user_schema import UserRole


class UserRepositoryProtocol(Protocol):
    async def create(
        self,
        *,
        email: str,
        name: str,
        hashed_password: str,
        role: UserRole,
    ) -> dict[str, object]: ...

    async def get_by_id(self, user_id: UUID) -> dict[str, object] | None: ...

    async def get_by_email(self, email: str) -> dict[str, object] | None: ...

    async def list_paginated(
        self,
        *,
        page: int,
        page_size: int,
        role: UserRole | None,
    ) -> tuple[list[dict[str, object]], int]: ...

    async def update(
        self,
        user_id: UUID,
        *,
        email: str | None = None,
        name: str | None = None,
        hashed_password: str | None = None,
        role: UserRole | None = None,
    ) -> dict[str, object]: ...

    async def soft_delete(self, user_id: UUID) -> None: ...


class UserRepository:
    def __init__(self, db: Prisma) -> None:
        self._db = db

    async def create(
        self,
        *,
        email: str,
        name: str,
        hashed_password: str,
        role: UserRole,
    ) -> dict[str, object]:
        data: types.UserCreateInput = {
            "email": email,
            "name": name,
            "hashedPassword": hashed_password,
            "role": {"connect": {"name": role.value}},
        }
        include: types.UserInclude = {"role": True}
        try:
            created = await self._db.user.create(data=data, include=include)
        except UniqueViolationError as exc:
            raise ConflictError(f"User with email {email} already exists") from exc
        return created.model_dump()

    async def get_by_id(self, user_id: UUID) -> dict[str, object] | None:
        where: types.UserWhereInput = {"id": str(user_id), "deletedAt": None}
        include: types.UserInclude = {"role": True}
        row = await self._db.user.find_first(where=where, include=include)
        return row.model_dump() if row is not None else None

    async def get_by_email(self, email: str) -> dict[str, object] | None:
        where: types.UserWhereInput = {"email": email, "deletedAt": None}
        include: types.UserInclude = {"role": True}
        row = await self._db.user.find_first(where=where, include=include)
        return row.model_dump() if row is not None else None

    async def list_paginated(
        self,
        *,
        page: int,
        page_size: int,
        role: UserRole | None,
    ) -> tuple[list[dict[str, object]], int]:
        where: types.UserWhereInput = {"deletedAt": None}
        if role is not None:
            where["role"] = {"is": {"name": role.value}}

        skip = (page - 1) * page_size
        order: types.UserOrderByInput = {"createdAt": "asc"}
        include: types.UserInclude = {"role": True}
        items = await self._db.user.find_many(
            where=where,
            skip=skip,
            take=page_size,
            order=order,
            include=include,
        )
        total = await self._db.user.count(where=where)
        return [item.model_dump() for item in items], total

    async def update(
        self,
        user_id: UUID,
        *,
        email: str | None = None,
        name: str | None = None,
        hashed_password: str | None = None,
        role: UserRole | None = None,
    ) -> dict[str, object]:
        data: types.UserUpdateInput = {}
        if email is not None:
            data["email"] = email
        if name is not None:
            data["name"] = name
        if hashed_password is not None:
            data["hashedPassword"] = hashed_password
        if role is not None:
            data["role"] = {"connect": {"name": role.value}}

        include: types.UserInclude = {"role": True}
        try:
            row = await self._db.user.update(
                where={"id": str(user_id)},
                data=data,
                include=include,
            )
        except UniqueViolationError as exc:
            raise ConflictError("Email already in use") from exc
        if row is None:
            raise NotFoundError(f"User {user_id} not found")
        return row.model_dump()

    async def soft_delete(self, user_id: UUID) -> None:
        data: types.UserUpdateInput = {"deletedAt": datetime.now(UTC)}
        try:
            await self._db.user.update(
                where={"id": str(user_id)},
                data=data,
            )
        except RecordNotFoundError as exc:
            raise NotFoundError(f"User {user_id} not found") from exc
