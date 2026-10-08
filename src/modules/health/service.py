from src.core.exceptions import ServiceUnavailableError
from src.modules.health.health_repository import HealthRepositoryProtocol
from src.modules.health.schema import HealthResponse


class HealthService:
    def __init__(self, repository: HealthRepositoryProtocol) -> None:
        self._repository = repository

    def check(self) -> HealthResponse:
        return HealthResponse(status="ok")

    async def ready(self) -> HealthResponse:
        if not await self._repository.is_database_reachable():
            raise ServiceUnavailableError("Database unreachable")
        return HealthResponse(status="ok")
