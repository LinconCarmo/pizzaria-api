from typing import Annotated
from uuid import UUID

from fastapi import Depends
from prisma import Prisma

from src.core.exceptions import ForbiddenError
from src.core.security_dependencies import AuthenticatedUser, get_current_user, require_role
from src.infra.database import get_db
from src.modules.users.user_repository import UserRepository, UserRepositoryProtocol
from src.modules.users.user_schema import UserRole
from src.modules.users.user_service import UserService

require_admin = require_role(UserRole.ADMIN.value)


def require_admin_or_self(
    user_id: UUID,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> AuthenticatedUser:
    if current_user.role == UserRole.ADMIN.value or current_user.user_id == user_id:
        return current_user
    raise ForbiddenError("Insufficient permissions")


def get_user_repository(
    db: Annotated[Prisma, Depends(get_db)],
) -> UserRepositoryProtocol:
    return UserRepository(db)


def get_user_service(
    repository: Annotated[UserRepositoryProtocol, Depends(get_user_repository)],
) -> UserService:
    return UserService(repository)
