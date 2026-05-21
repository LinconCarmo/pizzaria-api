from typing import Annotated

from fastapi import APIRouter, Depends

from src.modules.health.dependencies import get_health_service
from src.modules.health.schema import HealthResponse
from src.modules.health.service import HealthService

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("", summary="Healthcheck")
def health_check(
    service: Annotated[HealthService, Depends(get_health_service)],
) -> HealthResponse:
    return service.check()
