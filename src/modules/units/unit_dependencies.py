from typing import Annotated

from fastapi import Depends
from prisma import Prisma

from src.infra.database import get_db
from src.modules.units.unit_repository import UnitRepository, UnitRepositoryProtocol
from src.modules.units.unit_service import UnitService


def get_unit_repository(
    db: Annotated[Prisma, Depends(get_db)],
) -> UnitRepositoryProtocol:
    return UnitRepository(db)


def get_unit_service(
    repository: Annotated[UnitRepositoryProtocol, Depends(get_unit_repository)],
) -> UnitService:
    return UnitService(repository)
