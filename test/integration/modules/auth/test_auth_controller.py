from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from prisma import Prisma

from src.core.security import create_refresh_token, hash_reset_token
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


async def test_refresh_token_returns_401_when_token_is_expired(
    client: AsyncClient,
) -> None:
    created = await _create_user(
        client,
        email="ana@example.com",
        password="strongpass123",
    )

    expired_token = create_refresh_token(
        sub=str(created["id"]),
        exp_days=-1,
    )

    response = await client.post(
        "/api/v1/auth/refresh-token",
        json={"refresh_token": expired_token},
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


async def test_forgot_password_returns_204_and_creates_reset_token(
    client: AsyncClient,
    db: Prisma,
) -> None:
    created = await _create_user(
        client,
        email="ana@example.com",
        password="strongpass123",
    )

    response = await client.post(
        "/api/v1/auth/forgot-password",
        json={
            "email": "ana@example.com",
        },
    )

    assert response.status_code == 204

    token = await db.passwordresettoken.find_first(
        where={
            "userId": created["id"],
        },
    )

    assert token is not None
    assert token.userId == created["id"]
    assert token.tokenHash != ""

    delta = token.expiresAt - datetime.now(UTC)

    assert timedelta(minutes=55) < delta <= timedelta(hours=1)


async def test_forgot_password_returns_204_when_email_does_not_exist(
    client: AsyncClient,
) -> None:
    response = await client.post(
        "/api/v1/auth/forgot-password",
        json={
            "email": "missing@example.com",
        },
    )

    assert response.status_code == 204


async def test_reset_password_returns_204_when_token_is_valid(
    client: AsyncClient,
    db: Prisma,
) -> None:
    created = await _create_user(
        client,
        email="ana@example.com",
        password="strongpass123",
    )

    reset_token = "valid-reset-token"

    await db.passwordresettoken.create(
        data={
            "user": {
                "connect": {
                    "id": created["id"],
                }
            },
            "tokenHash": hash_reset_token(reset_token),
            "expiresAt": datetime.now(UTC) + timedelta(hours=1),
        },
    )

    response = await client.post(
        "/api/v1/auth/reset-password",
        json={
            "token": reset_token,
            "new_password": "newstrongpass123",
        },
    )

    assert response.status_code == 204

    async def test_reset_password_returns_400_when_token_is_invalid(
        client: AsyncClient,
    ) -> None:
        response = await client.post(
            "/api/v1/auth/reset-password",
            json={
                "token": "invalid-token",
                "new_password": "newstrongpass123",
            },
        )

        assert response.status_code == 400

        body = response.json()

        assert body["error"]["code"] == "BAD_REQUEST"

    async def test_reset_password_returns_400_when_token_is_expired(
        client: AsyncClient,
        db: Prisma,
    ) -> None:
        created = await _create_user(
            client,
            email="expired@example.com",
            password="strongpass123",
        )

        reset_token = "expired-reset-token"

        await db.passwordresettoken.create(
            data={
                "user": {
                    "connect": {
                        "id": created["id"],
                    }
                },
                "tokenHash": hash_reset_token(reset_token),
                "expiresAt": datetime.now(UTC) - timedelta(hours=1),
            },
        )

    response = await client.post(
        "/api/v1/auth/reset-password",
        json={
            "token": reset_token,
            "new_password": "newstrongpass123",
        },
    )

    assert response.status_code == 400

    body = response.json()

    assert body["error"]["code"] == "BAD_REQUEST"

    async def test_reset_password_returns_422_when_password_is_too_short(
        client: AsyncClient,
    ) -> None:
        response = await client.post(
            "/api/v1/auth/reset-password",
            json={
                "token": "some-token",
                "new_password": "123",
            },
        )

        assert response.status_code == 422

        body = response.json()

        assert body["error"]["code"] == "VALIDATION_ERROR"
