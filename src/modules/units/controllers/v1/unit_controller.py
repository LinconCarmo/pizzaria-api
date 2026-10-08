from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from src.core.exceptions import ErrorResponse
from src.modules.auth.auth_dependencies import AuthenticatedUser, require_admin
from src.modules.units.unit_dependencies import get_unit_service
from src.modules.units.unit_schema import (
    CreateUnitRequest,
    UnitListResponse,
    UnitResponse,
    UnitSummaryResponse,
    UpdateUnitRequest,
)
from src.modules.units.unit_service import UnitService

router = APIRouter(
    prefix="/units",
    tags=["Units"],
)


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Create unit",
    responses={
        401: {
            "model": ErrorResponse,
            "description": "Autenticação necessária",
        },
        403: {
            "model": ErrorResponse,
            "description": "Permissão de administrador necessária",
        },
        409: {
            "model": ErrorResponse,
            "description": "CNPJ já cadastrado",
        },
        422: {
            "model": ErrorResponse,
            "description": "Payload inválido",
        },
    },
)
async def create_unit(
    data: CreateUnitRequest,
    service: Annotated[UnitService, Depends(get_unit_service)],
    _: Annotated[AuthenticatedUser, Depends(require_admin)],
) -> UnitResponse:
    return await service.create(data)


@router.get(
    "/current",
    summary="Get current unit",
    responses={
        404: {
            "model": ErrorResponse,
            "description": "Unidade atual não encontrada",
        },
    },
)
async def get_current_unit(
    service: Annotated[UnitService, Depends(get_unit_service)],
) -> UnitSummaryResponse:
    return await service.get_current()


@router.get(
    "/{unit_id}",
    summary="Get unit by id",
    responses={
        401: {
            "model": ErrorResponse,
            "description": "Autenticação necessária",
        },
        403: {
            "model": ErrorResponse,
            "description": "Permissão de administrador necessária",
        },
        404: {
            "model": ErrorResponse,
            "description": "Unidade não encontrada",
        },
    },
)
async def get_unit(
    unit_id: UUID,
    service: Annotated[UnitService, Depends(get_unit_service)],
    _: Annotated[AuthenticatedUser, Depends(require_admin)],
) -> UnitResponse:
    return await service.get_by_id(unit_id)


@router.get(
    "",
    summary="List units (paginated)",
    responses={
        401: {
            "model": ErrorResponse,
            "description": "Autenticação necessária",
        },
        403: {
            "model": ErrorResponse,
            "description": "Permissão de administrador necessária",
        },
    },
)
async def list_unit(
    service: Annotated[UnitService, Depends(get_unit_service)],
    _: Annotated[AuthenticatedUser, Depends(require_admin)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> UnitListResponse:
    return await service.list_paginated(page=page, page_size=page_size)


@router.patch(
    "/{unit_id}",
    summary="Update unit (partial)",
    responses={
        401: {
            "model": ErrorResponse,
            "description": "Autenticação necessária",
        },
        403: {
            "model": ErrorResponse,
            "description": "Permissão de administrador necessária",
        },
        404: {
            "model": ErrorResponse,
            "description": "Unidade não encontrada",
        },
        409: {
            "model": ErrorResponse,
            "description": "CNPJ já cadastrado",
        },
        422: {
            "model": ErrorResponse,
            "description": "Payload inválido",
        },
    },
)
async def update_unit(
    unit_id: UUID,
    data: UpdateUnitRequest,
    service: Annotated[UnitService, Depends(get_unit_service)],
    _: Annotated[AuthenticatedUser, Depends(require_admin)],
) -> UnitResponse:
    return await service.update(unit_id, data)


@router.delete(
    "/{unit_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft delete unit",
    responses={
        401: {
            "model": ErrorResponse,
            "description": "Autenticação necessária",
        },
        403: {
            "model": ErrorResponse,
            "description": "Permissão de administrador necessária",
        },
        404: {
            "model": ErrorResponse,
            "description": "Unidade não encontrada",
        },
    },
)
async def delete_unit(
    unit_id: UUID,
    service: Annotated[UnitService, Depends(get_unit_service)],
    _: Annotated[AuthenticatedUser, Depends(require_admin)],
) -> None:
    await service.delete(unit_id)
