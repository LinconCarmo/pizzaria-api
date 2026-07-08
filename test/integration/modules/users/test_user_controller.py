from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from prisma import Prisma

from src.core.security import create_access_token
from src.modules.users.user_schema import UserRole
from test.factories import make_create_user_request

pytestmark = pytest.mark.integration


DEFAULT_EMAIL = "ana@example.com"
DEFAULT_PASSWORD = "strongpass123"
NON_EXISTENT_ID = UUID("00000000-0000-4000-8000-0000000000ff")


def _auth_headers(role: str) -> dict[str, str]:
    token = create_access_token(sub=str(uuid4()), role=role)
    return {"Authorization": f"Bearer {token}"}


def _owner_headers(user_id: str, role: str = UserRole.CUSTOMER.value) -> dict[str, str]:
    token = create_access_token(sub=user_id, role=role)
    return {"Authorization": f"Bearer {token}"}


ADMIN_HEADERS = _auth_headers(UserRole.ADMIN.value)


async def _create_user(client: AsyncClient, **overrides: object) -> dict[str, object]:
    payload = make_create_user_request(**overrides).model_dump(mode="json")
    response = await client.post("/api/v1/users", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


async def test_post_users_creates_user_in_db_when_payload_valid(
    client: AsyncClient,
    db: Prisma,
) -> None:
    payload = make_create_user_request().model_dump(mode="json")

    response = await client.post("/api/v1/users", json=payload)

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == DEFAULT_EMAIL
    assert "password" not in body
    assert "hashed_password" not in body

    persisted = await db.user.find_unique(where={"email": DEFAULT_EMAIL})
    assert persisted is not None
    assert persisted.hashedPassword != DEFAULT_PASSWORD


async def test_post_users_returns_409_when_email_already_exists(
    client: AsyncClient,
) -> None:
    await _create_user(client)

    response = await client.post(
        "/api/v1/users",
        json=make_create_user_request().model_dump(mode="json"),
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CONFLICT"


async def test_post_users_returns_422_when_email_invalid(client: AsyncClient) -> None:
    payload = make_create_user_request().model_dump(mode="json")
    payload["email"] = "not-an-email"

    response = await client.post("/api/v1/users", json=payload)

    assert response.status_code == 422


async def test_get_user_returns_user_when_exists(client: AsyncClient) -> None:
    created = await _create_user(client)

    response = await client.get(f"/api/v1/users/{created['id']}", headers=ADMIN_HEADERS)

    assert response.status_code == 200
    assert response.json()["email"] == DEFAULT_EMAIL


async def test_get_user_returns_404_when_id_not_found(client: AsyncClient) -> None:
    response = await client.get(f"/api/v1/users/{NON_EXISTENT_ID}", headers=ADMIN_HEADERS)

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


async def test_list_users_returns_paginated_results_when_multiple_exist(
    client: AsyncClient,
) -> None:
    await _create_user(client, email="a@example.com")
    await _create_user(client, email="b@example.com")
    await _create_user(client, email="c@example.com")

    response = await client.get("/api/v1/users?page=1&page_size=2", headers=ADMIN_HEADERS)

    assert response.status_code == 200
    body = response.json()
    assert body["meta"]["total"] == 3
    assert body["meta"]["total_pages"] == 2
    assert len(body["items"]) == 2


async def test_list_users_filters_by_role_when_role_query_provided(
    client: AsyncClient,
) -> None:
    await _create_user(client, email="customer@example.com", role=UserRole.CUSTOMER)
    await _create_user(client, email="admin@example.com", role=UserRole.ADMIN)

    response = await client.get("/api/v1/users?role=ADMIN", headers=ADMIN_HEADERS)

    assert response.status_code == 200
    body = response.json()
    assert body["meta"]["total"] == 1
    assert body["items"][0]["email"] == "admin@example.com"


async def test_patch_user_updates_only_provided_fields(
    client: AsyncClient,
    db: Prisma,
) -> None:
    created = await _create_user(client)

    response = await client.patch(
        f"/api/v1/users/{created['id']}",
        json={"name": "Ana Maria"},
        headers=ADMIN_HEADERS,
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Ana Maria"
    assert response.json()["email"] == DEFAULT_EMAIL

    persisted = await db.user.find_unique(where={"id": created["id"]})
    assert persisted is not None
    assert persisted.name == "Ana Maria"


async def test_patch_user_returns_404_when_id_not_found(client: AsyncClient) -> None:
    response = await client.patch(
        f"/api/v1/users/{NON_EXISTENT_ID}", json={"name": "X"}, headers=ADMIN_HEADERS
    )

    assert response.status_code == 404


async def test_patch_user_returns_409_when_changing_to_existing_email(
    client: AsyncClient,
) -> None:
    await _create_user(client, email="taken@example.com")
    other = await _create_user(client, email="other@example.com")

    response = await client.patch(
        f"/api/v1/users/{other['id']}",
        json={"email": "taken@example.com"},
        headers=ADMIN_HEADERS,
    )

    assert response.status_code == 409


async def test_delete_user_returns_204_and_marks_deleted_at_in_db(
    client: AsyncClient,
    db: Prisma,
) -> None:
    created = await _create_user(client)

    response = await client.delete(f"/api/v1/users/{created['id']}", headers=ADMIN_HEADERS)

    assert response.status_code == 204
    persisted = await db.user.find_unique(where={"id": created["id"]})
    assert persisted is not None
    assert persisted.deletedAt is not None


async def test_delete_user_returns_404_when_id_not_found(client: AsyncClient) -> None:
    response = await client.delete(f"/api/v1/users/{NON_EXISTENT_ID}", headers=ADMIN_HEADERS)

    assert response.status_code == 404


async def test_get_user_returns_404_when_user_soft_deleted(
    client: AsyncClient,
) -> None:
    created = await _create_user(client)
    await client.delete(f"/api/v1/users/{created['id']}", headers=ADMIN_HEADERS)

    response = await client.get(f"/api/v1/users/{created['id']}", headers=ADMIN_HEADERS)

    assert response.status_code == 404


async def test_list_users_excludes_soft_deleted_records(client: AsyncClient) -> None:
    keep = await _create_user(client, email="keep@example.com")
    drop = await _create_user(client, email="drop@example.com")
    await client.delete(f"/api/v1/users/{drop['id']}", headers=ADMIN_HEADERS)

    response = await client.get("/api/v1/users", headers=ADMIN_HEADERS)

    body = response.json()
    assert body["meta"]["total"] == 1
    assert body["items"][0]["id"] == keep["id"]


async def test_list_users_returns_401_when_no_token_provided(client: AsyncClient) -> None:
    response = await client.get("/api/v1/users")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


async def test_list_users_returns_403_when_role_is_not_admin(client: AsyncClient) -> None:
    response = await client.get("/api/v1/users", headers=_auth_headers(UserRole.CUSTOMER.value))

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


async def test_get_user_returns_403_when_role_is_not_admin(client: AsyncClient) -> None:
    created = await _create_user(client)

    response = await client.get(
        f"/api/v1/users/{created['id']}", headers=_auth_headers(UserRole.STAFF.value)
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


async def test_create_user_remains_open_without_token(client: AsyncClient) -> None:
    payload = make_create_user_request().model_dump(mode="json")

    response = await client.post("/api/v1/users", json=payload)

    assert response.status_code == 201


async def test_get_own_user_returns_200_when_owner(client: AsyncClient) -> None:
    created = await _create_user(client)
    headers = _owner_headers(str(created["id"]))

    response = await client.get(f"/api/v1/users/{created['id']}", headers=headers)

    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


async def test_get_user_returns_403_when_owner_requests_another_user(
    client: AsyncClient,
) -> None:
    owner = await _create_user(client, email="owner@example.com")
    other = await _create_user(client, email="other@example.com")

    response = await client.get(
        f"/api/v1/users/{other['id']}", headers=_owner_headers(str(owner["id"]))
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


async def test_patch_own_user_updates_when_owner_and_no_role_change(
    client: AsyncClient,
) -> None:
    created = await _create_user(client)

    response = await client.patch(
        f"/api/v1/users/{created['id']}",
        json={"name": "Novo Nome"},
        headers=_owner_headers(str(created["id"])),
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Novo Nome"


async def test_patch_own_user_returns_403_when_owner_changes_role(
    client: AsyncClient,
    db: Prisma,
) -> None:
    created = await _create_user(client)

    response = await client.patch(
        f"/api/v1/users/{created['id']}",
        json={"role": "ADMIN"},
        headers=_owner_headers(str(created["id"])),
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"

    persisted = await db.user.find_unique(where={"id": created["id"]}, include={"role": True})
    assert persisted is not None
    assert persisted.role is not None
    assert persisted.role.name == "CUSTOMER"


async def test_delete_own_user_returns_204_when_owner(
    client: AsyncClient,
    db: Prisma,
) -> None:
    created = await _create_user(client)

    response = await client.delete(
        f"/api/v1/users/{created['id']}", headers=_owner_headers(str(created["id"]))
    )

    assert response.status_code == 204
    persisted = await db.user.find_unique(where={"id": created["id"]})
    assert persisted is not None
    assert persisted.deletedAt is not None


async def test_delete_user_returns_403_when_owner_deletes_another_user(
    client: AsyncClient,
) -> None:
    owner = await _create_user(client, email="owner@example.com")
    other = await _create_user(client, email="other@example.com")

    response = await client.delete(
        f"/api/v1/users/{other['id']}", headers=_owner_headers(str(owner["id"]))
    )

    assert response.status_code == 403
