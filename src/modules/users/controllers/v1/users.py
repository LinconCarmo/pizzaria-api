from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from src.core.exceptions import ErrorResponse
from src.modules.users.dependencies import get_user_service
from src.modules.users.schema import (
    CreateUserRequest,
    UpdateUserRequest,
    UserListResponse,
    UserResponse,
    UserRole,
)
from src.modules.users.service import UserService

router = APIRouter(prefix="/users", tags=["Users"])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Create user",
    responses={
        409: {"model": ErrorResponse, "description": "Email já cadastrado"},
        422: {"model": ErrorResponse, "description": "Payload inválido"},
    },
)
async def create_user(
    data: CreateUserRequest,
    service: Annotated[UserService, Depends(get_user_service)],
) -> UserResponse:
    return await service.create(data)


@router.get(
    "/{user_id}",
    summary="Get user by id",
    responses={404: {"model": ErrorResponse, "description": "Usuário não encontrado"}},
)
async def get_user(
    user_id: UUID,
    service: Annotated[UserService, Depends(get_user_service)],
) -> UserResponse:
    return await service.get_by_id(user_id)


@router.get("", summary="List users (paginated)")
async def list_users(
    service: Annotated[UserService, Depends(get_user_service)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    role: UserRole | None = None,
) -> UserListResponse:
    return await service.list_paginated(page=page, page_size=page_size, role=role)


@router.patch(
    "/{user_id}",
    summary="Update user (partial)",
    responses={
        404: {"model": ErrorResponse, "description": "Usuário não encontrado"},
        409: {"model": ErrorResponse, "description": "Email já cadastrado"},
        422: {"model": ErrorResponse, "description": "Payload inválido"},
    },
)
async def update_user(
    user_id: UUID,
    data: UpdateUserRequest,
    service: Annotated[UserService, Depends(get_user_service)],
) -> UserResponse:
    return await service.update(user_id, data)


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft delete user",
    responses={404: {"model": ErrorResponse, "description": "Usuário não encontrado"}},
)
async def delete_user(
    user_id: UUID,
    service: Annotated[UserService, Depends(get_user_service)],
) -> None:
    await service.delete(user_id)
