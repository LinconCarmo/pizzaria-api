import pytest
from httpx import AsyncClient
from prisma import Prisma

from test.factories import make_create_user_request

pytestmark = pytest.mark.integration


async def _create_user(
    client: AsyncClient,
    **overrides: object,
) -> dict[str, object]:
    payload = make_create_user_request(**overrides).model_dump(mode="json")

    response = await client.post(
        "/api/v1/users",
        json=payload,
    )

    assert response.status_code == 201

    return response.json()


async def test_login_returns_tokens_when_credentials_are_valid(
    client: AsyncClient,
) -> None:
    await _create_user(
        client,
        email="ana@example.com",
        password="strongpass123",
    )

    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "ana@example.com",
            "password": "strongpass123",
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert "access_token" in body
    assert "refresh_token" in body
    assert body["expires_in"] == 900
    assert body["user"]["name"] == "Ana"
    assert body["user"]["role"] == "CUSTOMER"


async def test_login_returns_401_when_password_is_invalid(
    client: AsyncClient,
) -> None:
    await _create_user(client)

    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "ana@example.com",
            "password": "wrong-password",
        },
    )

    assert response.status_code == 401

    body = response.json()

    assert body["error"]["code"] == "UNAUTHORIZED"


async def test_login_returns_401_when_email_does_not_exist(
    client: AsyncClient,
) -> None:
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "missing@example.com",
            "password": "strongpass123",
        },
    )

    assert response.status_code == 401

    body = response.json()

    assert body["error"]["code"] == "UNAUTHORIZED"


async def test_login_returns_403_when_user_is_inactive(
    client: AsyncClient,
    db: Prisma,
) -> None:
    created = await _create_user(
        client,
        email="inactive@example.com",
    )

    await db.user.update(
        where={"id": created["id"]},
        data={"isActive": False},
    )

    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "inactive@example.com",
            "password": "strongpass123",
        },
    )

    assert response.status_code == 403

    body = response.json()

    assert body["error"]["code"] == "FORBIDDEN"


async def test_refresh_token_returns_tokens_when_token_is_valid(
    client: AsyncClient,
) -> None:
    await _create_user(
        client,
        email="ana@example.com",
        password="strongpass123",
    )

    login_response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "ana@example.com",
            "password": "strongpass123",
        },
    )

    assert login_response.status_code == 200

    body = login_response.json()

    refresh_token = body["refresh_token"]

    response = await client.post(
        "/api/v1/auth/refresh-token",
        json={
            "refresh_token": refresh_token,
        },
    )

    assert response.status_code == 200
    body = response.json()

    assert "access_token" in body
    assert "refresh_token" in body
    assert body["expires_in"] == 900
    assert body["user"]["name"] == "Ana"
    assert body["user"]["role"] == "CUSTOMER"


async def test_refresh_token_returns_401_when_token_is_invalid(
    client: AsyncClient,
) -> None:
    response = await client.post(
        "/api/v1/auth/refresh-token", json={"refresh_token": "invalid_token"}
    )
    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == "UNAUTHORIZED"


async def test_refresh_token_returns_401_when_access_token_is_used(client: AsyncClient) -> None:

    await _create_user(
        client,
        email="ana@example.com",
        password="strongpass123",
    )
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": "ana@example.com", "password": "strongpass123"},
    )

    assert login_response.status_code == 200
    body = login_response.json()
    access_token = body["access_token"]

    response = await client.post("/api/v1/auth/refresh-token", json={"refresh_token": access_token})

    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == "UNAUTHORIZED"


async def test_refresh_token_returns_403_when_user_is_inactive(
    client: AsyncClient,
    db: Prisma,
) -> None:
    created = await _create_user(
        client,
        email="ana@example.com",
        password="strongpass123",
    )

    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": "ana@example.com", "password": "strongpass123"},
    )

    assert login_response.status_code == 200
    body = login_response.json()
    refresh_token = body["refresh_token"]

    await db.user.update(
        where={"id": created["id"]},
        data={"isActive": False},
    )

    response = await client.post(
        "/api/v1/auth/refresh-token", json={"refresh_token": refresh_token}
    )

    assert response.status_code == 403
    body = response.json()
    assert body["error"]["code"] == "FORBIDDEN"
