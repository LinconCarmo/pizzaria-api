from typing import Annotated

from fastapi import Depends
from prisma import Prisma

from src.infra.database import get_db
from src.modules.health.health_repository import HealthRepository, HealthRepositoryProtocol
from src.modules.health.service import HealthService


def get_health_repository(
    db: Annotated[Prisma, Depends(get_db)],
) -> HealthRepositoryProtocol:
    return HealthRepository(db)


def get_health_service(
    repository: Annotated[HealthRepositoryProtocol, Depends(get_health_repository)],
) -> HealthService:
    return HealthService(repository)
