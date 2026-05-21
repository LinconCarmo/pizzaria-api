from src.modules.health.schema import HealthResponse
from src.modules.health.service import HealthService


def test_check_returns_status_ok_response():
    service = HealthService()

    result = service.check()

    assert isinstance(result, HealthResponse)
    assert result.status == "ok"
