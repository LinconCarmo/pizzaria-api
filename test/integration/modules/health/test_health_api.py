import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.integration


async def test_get_health_returns_200_when_app_running(client: AsyncClient) -> None:
    response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
