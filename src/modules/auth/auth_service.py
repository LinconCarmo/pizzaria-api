from typing import cast
from uuid import UUID

from src.core.exceptions import ForbiddenError, UnauthorizedError
from src.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)
from src.modules.auth.auth_schema import (
    LoginDto,
    LoginResponseDto,
    LoginUserResponse,
    RefreshTokenDto,
)
from src.modules.users.user_repository import UserRepositoryProtocol


class AuthService:
    def __init__(self, repository: UserRepositoryProtocol) -> None:
        self._repository = repository

    async def login(
        self,
        data: LoginDto,
    ) -> LoginResponseDto:

        user = await self._repository.get_by_email(data.email)

        if user is None:
            raise UnauthorizedError("Invalid credentials")

        hashed_password = cast(
            str,
            user["hashedPassword"],
        )

        role_data = cast(
            dict[str, object],
            user["role"],
        )

        role = cast(
            str,
            role_data["name"],
        )

        user_id = cast(
            UUID,
            user["id"],
        )

        user_name = cast(
            str,
            user["name"],
        )

        if not verify_password(
            data.password,
            hashed_password,
        ):
            raise UnauthorizedError("Invalid credentials")

        if not user["isActive"]:
            raise ForbiddenError("User is inactive")

        access_token = create_access_token(
            sub=str(user_id),
            role=role,
        )

        refresh_token = create_refresh_token(
            sub=str(user_id),
        )

        user_response = LoginUserResponse(
            id=user_id,
            name=user_name,
            role=role,
        )

        return LoginResponseDto(
            user=user_response,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=900,
        )

    async def refresh_token(
        self,
        data: RefreshTokenDto,
    ) -> LoginResponseDto:

        payload = decode_token(
            data.refresh_token,
        )

        token_type = cast(
            str,
            payload["token_type"],
        )

        if token_type != "refresh":
            raise UnauthorizedError(
                "Invalid token type",
            )

        user_id = UUID(
            cast(
                str,
                payload["sub"],
            )
        )

        user = await self._repository.get_by_id(
            user_id,
        )

        if user is None:
            raise UnauthorizedError(
                "Invalid token",
            )

        if not user["isActive"]:
            raise ForbiddenError(
                "User is inactive",
            )

        role_data = cast(
            dict[str, object],
            user["role"],
        )

        role = cast(
            str,
            role_data["name"],
        )

        user_name = cast(
            str,
            user["name"],
        )

        access_token = create_access_token(
            sub=str(user_id),
            role=role,
        )

        refresh_token = create_refresh_token(
            sub=str(user_id),
        )

        user_response = LoginUserResponse(
            id=user_id,
            name=user_name,
            role=role,
        )

        return LoginResponseDto(
            user=user_response,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=900,
        )
