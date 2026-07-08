from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from src.core.exceptions import ErrorResponse, ForbiddenError
from src.core.security_dependencies import AuthenticatedUser
from src.modules.users.user_dependencies import (
    get_user_service,
    require_admin,
    require_admin_or_self,
)
from src.modules.users.user_schema import (
    CreateUserRequest,
    UpdateUserRequest,
    UserListResponse,
    UserResponse,
    UserRole,
)
from src.modules.users.user_service import UserService

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
    dependencies=[Depends(require_admin_or_self)],
    responses={
        401: {"model": ErrorResponse, "description": "Token ausente ou inválido"},
        403: {"model": ErrorResponse, "description": "Requer ADMIN ou o próprio usuário"},
        404: {"model": ErrorResponse, "description": "Usuário não encontrado"},
    },
)
async def get_user(
    user_id: UUID,
    service: Annotated[UserService, Depends(get_user_service)],
) -> UserResponse:
    return await service.get_by_id(user_id)


@router.get(
    "",
    summary="List users (paginated)",
    dependencies=[Depends(require_admin)],
    responses={
        401: {"model": ErrorResponse, "description": "Token ausente ou inválido"},
        403: {"model": ErrorResponse, "description": "Requer role ADMIN"},
    },
)
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
        401: {"model": ErrorResponse, "description": "Token ausente ou inválido"},
        403: {"model": ErrorResponse, "description": "Requer ADMIN ou o próprio usuário"},
        404: {"model": ErrorResponse, "description": "Usuário não encontrado"},
        409: {"model": ErrorResponse, "description": "Email já cadastrado"},
        422: {"model": ErrorResponse, "description": "Payload inválido"},
    },
)
async def update_user(
    user_id: UUID,
    data: UpdateUserRequest,
    service: Annotated[UserService, Depends(get_user_service)],
    current_user: Annotated[AuthenticatedUser, Depends(require_admin_or_self)],
) -> UserResponse:
    if current_user.role != UserRole.ADMIN.value and data.role is not None:
        raise ForbiddenError("Only admins can change roles")
    return await service.update(user_id, data)


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft delete user",
    dependencies=[Depends(require_admin_or_self)],
    responses={
        401: {"model": ErrorResponse, "description": "Token ausente ou inválido"},
        403: {"model": ErrorResponse, "description": "Requer ADMIN ou o próprio usuário"},
        404: {"model": ErrorResponse, "description": "Usuário não encontrado"},
    },
)
async def delete_user(
    user_id: UUID,
    service: Annotated[UserService, Depends(get_user_service)],
) -> None:
    await service.delete(user_id)
