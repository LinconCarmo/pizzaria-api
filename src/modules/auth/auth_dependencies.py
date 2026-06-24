from typing import Annotated

from fastapi import Depends
from prisma import Prisma

from src.infra.database import get_db
from src.modules.auth.auth_service import AuthService
from src.modules.users.user_repository import (
    UserRepository,
    UserRepositoryProtocol,
)


def get_auth_repository(
    db: Annotated[Prisma, Depends(get_db)],
) -> UserRepositoryProtocol:
    return UserRepository(db)


def get_auth_service(
    repository: Annotated[
        UserRepositoryProtocol,
        Depends(get_auth_repository),
    ],
) -> AuthService:
    return AuthService(repository)
