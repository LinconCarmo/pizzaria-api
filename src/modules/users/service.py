from typing import Any

from src.core.exceptions import NotFoundError
from src.core.security import hash_password
from src.modules.users.repository import UserRepositoryProtocol
from src.modules.users.schema import (
    CreateUserRequest,
    PaginationMeta,
    UpdateUserRequest,
    UserListResponse,
    UserResponse,
    UserRole,
)


class UserService:
    def __init__(self, repository: UserRepositoryProtocol) -> None:
        self._repository = repository

    async def create(self, data: CreateUserRequest) -> UserResponse:
        raw = await self._repository.create(
            email=data.email,
            name=data.name,
            hashed_password=hash_password(data.password),
            role=data.role,
        )
        return self._to_response(raw)

    async def get_by_id(self, user_id: int) -> UserResponse:
        raw = await self._repository.get_by_id(user_id)
        if raw is None:
            raise NotFoundError(f"User {user_id} not found")
        return self._to_response(raw)

    async def list_paginated(
        self,
        page: int,
        page_size: int,
        role: UserRole | None,
    ) -> UserListResponse:
        items_raw, total = await self._repository.list_paginated(
            page=page,
            page_size=page_size,
            role=role,
        )
        total_pages = (total + page_size - 1) // page_size if total else 0
        return UserListResponse(
            items=[self._to_response(item) for item in items_raw],
            meta=PaginationMeta(
                page=page,
                page_size=page_size,
                total=total,
                total_pages=total_pages,
            ),
        )

    async def update(self, user_id: int, data: UpdateUserRequest) -> UserResponse:
        payload = data.model_dump(exclude_unset=True)
        if "password" in payload:
            payload["hashedPassword"] = hash_password(payload.pop("password"))
        if "role" in payload and payload["role"] is not None:
            payload["role"] = payload["role"].value

        raw = await self._repository.update(user_id, payload)
        return self._to_response(raw)

    async def delete(self, user_id: int) -> None:
        await self._repository.soft_delete(user_id)

    def _to_response(self, raw: Any) -> UserResponse:
        return UserResponse(
            id=raw.id,
            email=raw.email,
            name=raw.name,
            role=UserRole(raw.role),
            created_at=raw.createdAt,
            updated_at=raw.updatedAt,
        )
