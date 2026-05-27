from uuid import UUID

import pytest
from httpx import AsyncClient
from prisma import Prisma

from src.modules.users.user_schema import UserRole
from test.factories import make_create_user_request

pytestmark = pytest.mark.integration


DEFAULT_EMAIL = "ana@example.com"
DEFAULT_PASSWORD = "strongpass123"
NON_EXISTENT_ID = UUID("00000000-0000-4000-8000-0000000000ff")


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

    response = await client.get(f"/api/v1/users/{created['id']}")

    assert response.status_code == 200
    assert response.json()["email"] == DEFAULT_EMAIL


async def test_get_user_returns_404_when_id_not_found(client: AsyncClient) -> None:
    response = await client.get(f"/api/v1/users/{NON_EXISTENT_ID}")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


async def test_list_users_returns_paginated_results_when_multiple_exist(
    client: AsyncClient,
) -> None:
    await _create_user(client, email="a@example.com")
    await _create_user(client, email="b@example.com")
    await _create_user(client, email="c@example.com")

    response = await client.get("/api/v1/users?page=1&page_size=2")

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

    response = await client.get("/api/v1/users?role=ADMIN")

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
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Ana Maria"
    assert response.json()["email"] == DEFAULT_EMAIL

    persisted = await db.user.find_unique(where={"id": created["id"]})
    assert persisted is not None
    assert persisted.name == "Ana Maria"


async def test_patch_user_returns_404_when_id_not_found(client: AsyncClient) -> None:
    response = await client.patch(f"/api/v1/users/{NON_EXISTENT_ID}", json={"name": "X"})

    assert response.status_code == 404


async def test_patch_user_returns_409_when_changing_to_existing_email(
    client: AsyncClient,
) -> None:
    await _create_user(client, email="taken@example.com")
    other = await _create_user(client, email="other@example.com")

    response = await client.patch(
        f"/api/v1/users/{other['id']}",
        json={"email": "taken@example.com"},
    )

    assert response.status_code == 409


async def test_delete_user_returns_204_and_marks_deleted_at_in_db(
    client: AsyncClient,
    db: Prisma,
) -> None:
    created = await _create_user(client)

    response = await client.delete(f"/api/v1/users/{created['id']}")

    assert response.status_code == 204
    persisted = await db.user.find_unique(where={"id": created["id"]})
    assert persisted is not None
    assert persisted.deletedAt is not None


async def test_delete_user_returns_404_when_id_not_found(client: AsyncClient) -> None:
    response = await client.delete(f"/api/v1/users/{NON_EXISTENT_ID}")

    assert response.status_code == 404


async def test_get_user_returns_404_when_user_soft_deleted(
    client: AsyncClient,
) -> None:
    created = await _create_user(client)
    await client.delete(f"/api/v1/users/{created['id']}")

    response = await client.get(f"/api/v1/users/{created['id']}")

    assert response.status_code == 404


async def test_list_users_excludes_soft_deleted_records(client: AsyncClient) -> None:
    keep = await _create_user(client, email="keep@example.com")
    drop = await _create_user(client, email="drop@example.com")
    await client.delete(f"/api/v1/users/{drop['id']}")

    response = await client.get("/api/v1/users")

    body = response.json()
    assert body["meta"]["total"] == 1
    assert body["items"][0]["id"] == keep["id"]
