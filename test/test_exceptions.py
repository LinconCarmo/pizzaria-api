from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.core.exceptions import (
    DomainError,
    NotFoundError,
    domain_error_handler,
)

app = FastAPI()

app.add_exception_handler(
    DomainError,
    domain_error_handler,
)


@app.get("/test-error")
async def raise_not_found():
    raise NotFoundError("User not found")


client = TestClient(app)


def test_not_found_handler():
    response = client.get("/test-error")

    assert response.status_code == 404

    data = response.json()

    assert data["error"]["code"] == "NOT_FOUND"
    assert data["error"]["message"] == "User not found"
