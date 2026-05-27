from typing import Annotated

from fastapi import Depends
from prisma import Prisma

from src.infra.database import get_db
from src.modules.users.user_repository import UserRepository, UserRepositoryProtocol
from src.modules.users.user_service import UserService


def get_user_repository(
    db: Annotated[Prisma, Depends(get_db)],
) -> UserRepositoryProtocol:
    return UserRepository(db)


def get_user_service(
    repository: Annotated[UserRepositoryProtocol, Depends(get_user_repository)],
) -> UserService:
    return UserService(repository)
