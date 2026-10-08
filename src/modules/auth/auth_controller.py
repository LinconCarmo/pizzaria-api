from typing import Annotated

from fastapi import APIRouter, Depends, status

from src.core.exceptions import ErrorResponse

from .auth_dependencies import (
    get_auth_service,
    limit_forgot_password_by_ip,
    limit_login_by_ip,
)
from .auth_schema import (
    ForgotPasswordDto,
    LoginDto,
    LoginResponseDto,
    RefreshTokenDto,
    ResetPasswordDto,
)
from .auth_service import AuthService

router = APIRouter(
    prefix="/auth",
    tags=["Auth"],
)

_TOO_MANY_REQUESTS = {
    "model": ErrorResponse,
    "description": "Limite de tentativas excedido; ver header Retry-After",
}


@router.post(
    "/login",
    status_code=status.HTTP_200_OK,
    summary="Log in",
    dependencies=[Depends(limit_login_by_ip)],
    responses={
        401: {"model": ErrorResponse, "description": "Credenciais inválidas"},
        403: {"model": ErrorResponse, "description": "Usuário inativo"},
        429: _TOO_MANY_REQUESTS,
    },
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
    status_code=status.HTTP_200_OK,
    summary="Refresh access token",
    responses={
        401: {"model": ErrorResponse, "description": "Refresh token inválido ou expirado"},
        403: {"model": ErrorResponse, "description": "Usuário inativo"},
    },
)
async def refresh_token(
    data: RefreshTokenDto,
    service: Annotated[
        AuthService,
        Depends(get_auth_service),
    ],
) -> LoginResponseDto:
    return await service.refresh_token(data)


@router.post(
    "/forgot-password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Request password reset",
    description="Responde 204 mesmo quando o e-mail não existe, para não revelar contas.",
    dependencies=[Depends(limit_forgot_password_by_ip)],
    responses={429: _TOO_MANY_REQUESTS},
)
async def forgot_password(
    data: ForgotPasswordDto,
    service: Annotated[
        AuthService,
        Depends(get_auth_service),
    ],
) -> None:
    await service.forgot_password(data)


@router.post(
    "/reset-password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Reset password",
    responses={
        400: {"model": ErrorResponse, "description": "Token inválido, usado ou expirado"},
        403: {"model": ErrorResponse, "description": "Usuário inativo"},
    },
)
async def reset_password(
    data: ResetPasswordDto,
    service: Annotated[
        AuthService,
        Depends(get_auth_service),
    ],
) -> None:
    await service.reset_password(data)
