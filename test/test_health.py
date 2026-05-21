from fastapi.testclient import TestClient

from src.main import app


def test_health_live():
    with TestClient(app) as client:
        response = client.get("/health/live")

        assert response.status_code == 200

        data = response.json()

        assert data["status"] == "alive"


def test_health():
    with TestClient(app) as client:
        response = client.get("/health")

        assert response.status_code == 200

        data = response.json()

        assert data["status"] == "ok"
        assert data["checks"]["db"] == "ok"
        assert data["checks"]["redis"] == "ok"
