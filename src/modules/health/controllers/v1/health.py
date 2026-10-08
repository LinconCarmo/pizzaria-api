from typing import Annotated

from fastapi import APIRouter, Depends

from src.core.exceptions import ErrorResponse
from src.modules.health.dependencies import get_health_service
from src.modules.health.schema import HealthResponse
from src.modules.health.service import HealthService

router = APIRouter(prefix="/health", tags=["Health"])


@router.get(
    "",
    summary="Liveness check",
    description="Confirma que o processo responde. Não consulta dependências externas.",
)
async def health_check(
    service: Annotated[HealthService, Depends(get_health_service)],
) -> HealthResponse:
    return service.check()


@router.get(
    "/ready",
    summary="Readiness check",
    description="Confirma que a API consegue falar com o banco de dados.",
    responses={503: {"model": ErrorResponse, "description": "Banco de dados indisponível"}},
)
async def readiness_check(
    service: Annotated[HealthService, Depends(get_health_service)],
) -> HealthResponse:
    return await service.ready()
