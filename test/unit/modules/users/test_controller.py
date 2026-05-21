from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from src.core.exceptions import ConflictError, NotFoundError
from src.main import app
from src.modules.users.dependencies import get_user_service
from src.modules.users.schema import PaginationMeta, UserListResponse
from src.modules.users.service import UserService
from test.factories import make_user_response


def _override_service(mock: AsyncMock) -> None:
    app.dependency_overrides[get_user_service] = lambda: mock


def _clear_overrides() -> None:
    app.dependency_overrides.clear()


def test_post_users_returns_201_with_user_response():
    service = AsyncMock(spec=UserService)
    service.create.return_value = make_user_response()
    _override_service(service)
    try:
        client = TestClient(app)
        response = client.post(
            "/users",
            json={
                "email": "ana@example.com",
                "name": "Ana",
                "password": "strongpass123",
            },
        )

        assert response.status_code == 201
        body = response.json()
        assert body["id"] == 1
        assert body["email"] == "ana@example.com"
        assert "password" not in body
    finally:
        _clear_overrides()


def test_post_users_returns_409_when_service_raises_conflict():
    service = AsyncMock(spec=UserService)
    service.create.side_effect = ConflictError("duplicate")
    _override_service(service)
    try:
        client = TestClient(app)
        response = client.post(
            "/users",
            json={
                "email": "ana@example.com",
                "name": "Ana",
                "password": "strongpass123",
            },
        )

        assert response.status_code == 409
        assert response.json()["error"]["code"] == "CONFLICT"
    finally:
        _clear_overrides()


def test_post_users_returns_422_when_email_invalid():
    service = AsyncMock(spec=UserService)
    _override_service(service)
    try:
        client = TestClient(app)
        response = client.post(
            "/users",
            json={"email": "not-email", "name": "A", "password": "strongpass123"},
        )

        assert response.status_code == 422
        service.create.assert_not_called()
    finally:
        _clear_overrides()


def test_get_user_returns_200_with_response():
    service = AsyncMock(spec=UserService)
    service.get_by_id.return_value = make_user_response(id=42, email="x@y.com")
    _override_service(service)
    try:
        client = TestClient(app)
        response = client.get("/users/42")

        assert response.status_code == 200
        assert response.json()["id"] == 42
    finally:
        _clear_overrides()


def test_get_user_returns_404_when_service_raises_not_found():
    service = AsyncMock(spec=UserService)
    service.get_by_id.side_effect = NotFoundError("missing")
    _override_service(service)
    try:
        client = TestClient(app)
        response = client.get("/users/999")

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "NOT_FOUND"
    finally:
        _clear_overrides()


def test_list_users_returns_200_with_pagination_meta():
    service = AsyncMock(spec=UserService)
    service.list_paginated.return_value = UserListResponse(
        items=[make_user_response()],
        meta=PaginationMeta(page=1, page_size=20, total=1, total_pages=1),
    )
    _override_service(service)
    try:
        client = TestClient(app)
        response = client.get("/users?page=1&page_size=20")

        assert response.status_code == 200
        body = response.json()
        assert body["meta"]["total"] == 1
        assert len(body["items"]) == 1
    finally:
        _clear_overrides()


def test_patch_user_returns_200():
    service = AsyncMock(spec=UserService)
    service.update.return_value = make_user_response()
    _override_service(service)
    try:
        client = TestClient(app)
        response = client.patch("/users/1", json={"name": "Ana Maria"})

        assert response.status_code == 200
    finally:
        _clear_overrides()


def test_delete_user_returns_204_with_empty_body():
    service = AsyncMock(spec=UserService)
    service.delete.return_value = None
    _override_service(service)
    try:
        client = TestClient(app)
        response = client.delete("/users/1")

        assert response.status_code == 204
        assert response.content == b""
    finally:
        _clear_overrides()


def test_delete_user_returns_404_when_not_found():
    service = AsyncMock(spec=UserService)
    service.delete.side_effect = NotFoundError("missing")
    _override_service(service)
    try:
        client = TestClient(app)
        response = client.delete("/users/999")

        assert response.status_code == 404
    finally:
        _clear_overrides()
