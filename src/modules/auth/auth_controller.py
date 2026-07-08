from typing import Annotated

from fastapi import APIRouter, Depends, status

from .auth_dependencies import get_auth_service
from .auth_schema import LoginDto, LoginResponseDto, RefreshTokenDto
from .auth_service import AuthService

router = APIRouter(
    prefix="/auth",
    tags=["Auth"],
)


@router.post(
    "/login",
    response_model=LoginResponseDto,
    status_code=status.HTTP_200_OK,
)
async def login(
    data: LoginDto,
    service: Annotated[
        AuthService,
        Depends(get_auth_service),
    ],
) -> LoginResponseDto:
    return await service.login(data)


@router.post(
    "/refresh-token",
    response_model=LoginResponseDto,
    status_code=status.HTTP_200_OK,
)
async def refresh_token(
    data: RefreshTokenDto,
    service: Annotated[
        AuthService,
        Depends(get_auth_service),
    ],
) -> LoginResponseDto:
    return await service.refresh_token(data)
