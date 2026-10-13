from collections.abc import Iterator
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.modules.health.dependencies import get_health_repository
from src.modules.health.health_repository import HealthRepositoryProtocol


@pytest.fixture
def repo() -> Iterator[AsyncMock]:
    mock = AsyncMock(spec=HealthRepositoryProtocol)
    app.dependency_overrides[get_health_repository] = lambda: mock
    yield mock
    app.dependency_overrides.clear()


def test_get_health_returns_200_with_status_ok(repo: AsyncMock) -> None:
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_get_health_ready_returns_200_when_database_reachable(repo: AsyncMock) -> None:
    repo.is_database_reachable.return_value = True
    client = TestClient(app)

    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_get_health_ready_returns_503_when_database_unreachable(repo: AsyncMock) -> None:
    repo.is_database_reachable.return_value = False
    client = TestClient(app)

    response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "SERVICE_UNAVAILABLE"
