from datetime import UTC, datetime
from typing import Any, Protocol, cast
from uuid import UUID

from prisma import Prisma
from prisma.errors import RecordNotFoundError, UniqueViolationError
from prisma.models import User

from src.core.exceptions import ConflictError, NotFoundError
from src.modules.users.schema import UserRole


class UserRepositoryProtocol(Protocol):
    async def create(
        self,
        *,
        email: str,
        name: str,
        hashed_password: str,
        role: UserRole,
    ) -> User: ...

    async def get_by_id(self, user_id: UUID) -> User | None: ...

    async def get_by_email(self, email: str) -> User | None: ...

    async def list_paginated(
        self,
        *,
        page: int,
        page_size: int,
        role: UserRole | None,
    ) -> tuple[list[User], int]: ...

    async def update(
        self,
        user_id: UUID,
        *,
        email: str | None = None,
        name: str | None = None,
        hashed_password: str | None = None,
        role: UserRole | None = None,
    ) -> User: ...

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
    ) -> User:
        try:
            return await self._db.user.create(
                data=cast(
                    Any,
                    {
                        "email": email,
                        "name": name,
                        "hashedPassword": hashed_password,
                        "role": role.value,
                    },
                ),
            )
        except UniqueViolationError as exc:
            raise ConflictError(f"User with email {email} already exists") from exc

    async def get_by_id(self, user_id: UUID) -> User | None:
        return await self._db.user.find_first(
            where=cast(Any, {"id": str(user_id), "deletedAt": None}),
        )

    async def get_by_email(self, email: str) -> User | None:
        return await self._db.user.find_first(
            where=cast(Any, {"email": email, "deletedAt": None}),
        )

    async def list_paginated(
        self,
        *,
        page: int,
        page_size: int,
        role: UserRole | None,
    ) -> tuple[list[User], int]:
        where: dict[str, Any] = {"deletedAt": None}
        if role is not None:
            where["role"] = role.value

        skip = (page - 1) * page_size
        items = await self._db.user.find_many(
            where=cast(Any, where),
            skip=skip,
            take=page_size,
            order=cast(Any, {"createdAt": "asc"}),
        )
        total = await self._db.user.count(where=cast(Any, where))
        return items, total

    async def update(
        self,
        user_id: UUID,
        *,
        email: str | None = None,
        name: str | None = None,
        hashed_password: str | None = None,
        role: UserRole | None = None,
    ) -> User:
        data: dict[str, Any] = {}
        if email is not None:
            data["email"] = email
        if name is not None:
            data["name"] = name
        if hashed_password is not None:
            data["hashedPassword"] = hashed_password
        if role is not None:
            data["role"] = role.value

        try:
            return cast(
                User,
                await self._db.user.update(
                    where={"id": str(user_id)},
                    data=cast(Any, data),
                ),
            )
        except RecordNotFoundError as exc:
            raise NotFoundError(f"User {user_id} not found") from exc
        except UniqueViolationError as exc:
            raise ConflictError("Email already in use") from exc

    async def soft_delete(self, user_id: UUID) -> None:
        try:
            await self._db.user.update(
                where={"id": str(user_id)},
                data=cast(Any, {"deletedAt": datetime.now(UTC)}),
            )
        except RecordNotFoundError as exc:
            raise NotFoundError(f"User {user_id} not found") from exc
