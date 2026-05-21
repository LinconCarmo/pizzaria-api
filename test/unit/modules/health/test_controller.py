from fastapi.testclient import TestClient

from src.main import app


def test_get_health_returns_200_with_status_ok():
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
