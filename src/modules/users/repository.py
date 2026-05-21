from datetime import UTC, datetime
from typing import Any, Protocol, cast

from prisma import Prisma
from prisma.errors import RecordNotFoundError, UniqueViolationError

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
    ) -> Any: ...

    async def get_by_id(self, user_id: int) -> Any | None: ...

    async def get_by_email(self, email: str) -> Any | None: ...

    async def list_paginated(
        self,
        *,
        page: int,
        page_size: int,
        role: UserRole | None,
    ) -> tuple[list[Any], int]: ...

    async def update(self, user_id: int, data: dict[str, Any]) -> Any: ...

    async def soft_delete(self, user_id: int) -> None: ...


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
    ) -> Any:
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

    async def get_by_id(self, user_id: int) -> Any | None:
        return await self._db.user.find_first(
            where=cast(Any, {"id": user_id, "deletedAt": None}),
        )

    async def get_by_email(self, email: str) -> Any | None:
        return await self._db.user.find_first(
            where=cast(Any, {"email": email, "deletedAt": None}),
        )

    async def list_paginated(
        self,
        *,
        page: int,
        page_size: int,
        role: UserRole | None,
    ) -> tuple[list[Any], int]:
        where: dict[str, Any] = {"deletedAt": None}
        if role is not None:
            where["role"] = role.value

        skip = (page - 1) * page_size
        items = await self._db.user.find_many(
            where=cast(Any, where),
            skip=skip,
            take=page_size,
            order=cast(Any, {"id": "asc"}),
        )
        total = await self._db.user.count(where=cast(Any, where))
        return items, total

    async def update(self, user_id: int, data: dict[str, Any]) -> Any:
        existing = await self.get_by_id(user_id)
        if existing is None:
            raise NotFoundError(f"User {user_id} not found")

        try:
            return await self._db.user.update(
                where={"id": user_id},
                data=cast(Any, data),
            )
        except UniqueViolationError as exc:
            raise ConflictError("Email already in use") from exc
        except RecordNotFoundError as exc:
            raise NotFoundError(f"User {user_id} not found") from exc

    async def soft_delete(self, user_id: int) -> None:
        existing = await self.get_by_id(user_id)
        if existing is None:
            raise NotFoundError(f"User {user_id} not found")

        try:
            await self._db.user.update(
                where={"id": user_id},
                data=cast(Any, {"deletedAt": datetime.now(UTC)}),
            )
        except RecordNotFoundError as exc:
            raise NotFoundError(f"User {user_id} not found") from exc
