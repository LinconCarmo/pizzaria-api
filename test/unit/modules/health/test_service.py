from unittest.mock import AsyncMock

import pytest

from src.core.exceptions import ServiceUnavailableError
from src.modules.health.health_repository import HealthRepositoryProtocol
from src.modules.health.schema import HealthResponse
from src.modules.health.service import HealthService


@pytest.fixture
def repo() -> AsyncMock:
    return AsyncMock(spec=HealthRepositoryProtocol)


@pytest.fixture
def service(repo: AsyncMock) -> HealthService:
    return HealthService(repo)


def test_check_returns_status_ok_response(service: HealthService, repo: AsyncMock) -> None:
    result = service.check()

    assert isinstance(result, HealthResponse)
    assert result.status == "ok"
    repo.is_database_reachable.assert_not_awaited()


async def test_ready_returns_ok_when_database_reachable(
    service: HealthService, repo: AsyncMock
) -> None:
    repo.is_database_reachable.return_value = True

    result = await service.ready()

    assert result.status == "ok"


async def test_ready_raises_503_when_database_unreachable(
    service: HealthService, repo: AsyncMock
) -> None:
    repo.is_database_reachable.return_value = False

    with pytest.raises(ServiceUnavailableError):
        await service.ready()
