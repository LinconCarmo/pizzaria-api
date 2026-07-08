from unittest.mock import AsyncMock
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from src.core.exceptions import ConflictError, NotFoundError
from src.core.security import create_access_token
from src.main import app
from src.modules.users.user_dependencies import get_user_service
from src.modules.users.user_schema import PaginationMeta, UserListResponse, UserRole
from src.modules.users.user_service import UserService
from test.factories import make_user_response

USER_ID = UUID("00000000-0000-4000-8000-000000000001")
OTHER_USER_ID = UUID("00000000-0000-4000-8000-000000000042")
NON_EXISTENT_ID = UUID("00000000-0000-4000-8000-0000000000ff")

ADMIN_HEADERS = {
    "Authorization": f"Bearer {create_access_token(sub=str(uuid4()), role=UserRole.ADMIN.value)}"
}


def _owner_headers(user_id: UUID, role: str = UserRole.CUSTOMER.value) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(sub=str(user_id), role=role)}"}


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
            "/api/v1/users",
            json={
                "email": "ana@example.com",
                "name": "Ana",
                "password": "strongpass123",
            },
        )

        assert response.status_code == 201
        body = response.json()
        assert body["id"] == str(USER_ID)
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
            "/api/v1/users",
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
            "/api/v1/users",
            json={"email": "not-email", "name": "A", "password": "strongpass123"},
        )

        assert response.status_code == 422
        service.create.assert_not_called()
    finally:
        _clear_overrides()


def test_get_user_returns_200_with_response():
    service = AsyncMock(spec=UserService)
    service.get_by_id.return_value = make_user_response(id=OTHER_USER_ID, email="x@y.com")
    _override_service(service)

    try:
        client = TestClient(app)
        response = client.get(f"/api/v1/users/{OTHER_USER_ID}", headers=ADMIN_HEADERS)

        assert response.status_code == 200
        assert response.json()["id"] == str(OTHER_USER_ID)
    finally:
        _clear_overrides()


def test_get_user_returns_404_when_service_raises_not_found():
    service = AsyncMock(spec=UserService)
    service.get_by_id.side_effect = NotFoundError("missing")
    _override_service(service)

    try:
        client = TestClient(app)
        response = client.get(f"/api/v1/users/{NON_EXISTENT_ID}", headers=ADMIN_HEADERS)

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
        response = client.get("/api/v1/users?page=1&page_size=20", headers=ADMIN_HEADERS)

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
        response = client.patch(
            f"/api/v1/users/{USER_ID}", json={"name": "Ana Maria"}, headers=ADMIN_HEADERS
        )

        assert response.status_code == 200
    finally:
        _clear_overrides()


def test_delete_user_returns_204_with_empty_body():
    service = AsyncMock(spec=UserService)
    service.delete.return_value = None
    _override_service(service)

    try:
        client = TestClient(app)
        response = client.delete(f"/api/v1/users/{USER_ID}", headers=ADMIN_HEADERS)

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
        response = client.delete(f"/api/v1/users/{NON_EXISTENT_ID}", headers=ADMIN_HEADERS)

        assert response.status_code == 404
    finally:
        _clear_overrides()


def test_get_user_returns_200_when_owner():
    service = AsyncMock(spec=UserService)
    service.get_by_id.return_value = make_user_response(id=OTHER_USER_ID)
    _override_service(service)

    try:
        client = TestClient(app)
        response = client.get(
            f"/api/v1/users/{OTHER_USER_ID}", headers=_owner_headers(OTHER_USER_ID)
        )

        assert response.status_code == 200
    finally:
        _clear_overrides()


def test_get_user_returns_403_when_non_admin_and_not_owner():
    service = AsyncMock(spec=UserService)
    _override_service(service)

    try:
        client = TestClient(app)
        response = client.get(f"/api/v1/users/{OTHER_USER_ID}", headers=_owner_headers(USER_ID))

        assert response.status_code == 403
        assert response.json()["error"]["code"] == "FORBIDDEN"
        service.get_by_id.assert_not_called()
    finally:
        _clear_overrides()


def test_patch_user_returns_200_when_owner_and_no_role_change():
    service = AsyncMock(spec=UserService)
    service.update.return_value = make_user_response(id=USER_ID)
    _override_service(service)

    try:
        client = TestClient(app)
        response = client.patch(
            f"/api/v1/users/{USER_ID}",
            json={"name": "Novo Nome"},
            headers=_owner_headers(USER_ID),
        )

        assert response.status_code == 200
    finally:
        _clear_overrides()


def test_patch_user_returns_403_when_owner_tries_to_change_role():
    service = AsyncMock(spec=UserService)
    _override_service(service)

    try:
        client = TestClient(app)
        response = client.patch(
            f"/api/v1/users/{USER_ID}",
            json={"role": "ADMIN"},
            headers=_owner_headers(USER_ID),
        )

        assert response.status_code == 403
        assert response.json()["error"]["code"] == "FORBIDDEN"
        service.update.assert_not_called()
    finally:
        _clear_overrides()


def test_patch_user_returns_200_when_admin_changes_role():
    service = AsyncMock(spec=UserService)
    service.update.return_value = make_user_response(id=USER_ID, role=UserRole.ADMIN)
    _override_service(service)

    try:
        client = TestClient(app)
        response = client.patch(
            f"/api/v1/users/{USER_ID}",
            json={"role": "ADMIN"},
            headers=ADMIN_HEADERS,
        )

        assert response.status_code == 200
        service.update.assert_awaited_once()
    finally:
        _clear_overrides()


def test_patch_user_returns_403_when_non_admin_and_not_owner():
    service = AsyncMock(spec=UserService)
    _override_service(service)

    try:
        client = TestClient(app)
        response = client.patch(
            f"/api/v1/users/{OTHER_USER_ID}",
            json={"name": "X"},
            headers=_owner_headers(USER_ID),
        )

        assert response.status_code == 403
        service.update.assert_not_called()
    finally:
        _clear_overrides()


def test_delete_user_returns_204_when_owner():
    service = AsyncMock(spec=UserService)
    service.delete.return_value = None
    _override_service(service)

    try:
        client = TestClient(app)
        response = client.delete(f"/api/v1/users/{USER_ID}", headers=_owner_headers(USER_ID))

        assert response.status_code == 204
    finally:
        _clear_overrides()


def test_delete_user_returns_403_when_non_admin_and_not_owner():
    service = AsyncMock(spec=UserService)
    _override_service(service)

    try:
        client = TestClient(app)
        response = client.delete(f"/api/v1/users/{OTHER_USER_ID}", headers=_owner_headers(USER_ID))

        assert response.status_code == 403
        service.delete.assert_not_called()
    finally:
        _clear_overrides()
