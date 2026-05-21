from src.modules.health.schema import HealthResponse


class HealthService:
    def check(self) -> HealthResponse:
        return HealthResponse(status="ok")
