from uuid import UUID

import pytest
from httpx import AsyncClient
from prisma import Prisma

from src.core.security import create_access_token
from test.factories import make_create_unit_request

pytestmark = pytest.mark.integration


DEFAULT_CNPJ = "12345678000195"
NON_EXISTENT_ID = UUID("00000000-0000-4000-8000-0000000000ff")
ADMIN_USER_ID = "00000000-0000-4000-8000-000000000001"


def _admin_headers() -> dict[str, str]:
    token = create_access_token(
        sub=ADMIN_USER_ID,
        role="ADMIN",
    )
    return {"Authorization": f"Bearer {token}"}


async def _create_unit(
    client: AsyncClient,
    **overrides: object,
) -> dict[str, object]:
    payload = make_create_unit_request(**overrides).model_dump(mode="json")

    response = await client.post(
        "/api/v1/units",
        json=payload,
        headers=_admin_headers(),
    )

    assert response.status_code == 201, response.text
    return response.json()


async def test_post_units_creates_unit_in_db_when_payload_valid(
    client: AsyncClient,
    db: Prisma,
) -> None:
    payload = make_create_unit_request(
        cnpj="11222333000181",
    ).model_dump(mode="json")

    response = await client.post(
        "/api/v1/units",
        json=payload,
        headers=_admin_headers(),
    )

    assert response.status_code == 201

    body = response.json()

    assert body["cnpj"] == "11222333000181"
    assert body["name"] == "Unidade Principal"

    persisted = await db.unit.find_unique(
        where={"cnpj": "11222333000181"},
    )

    assert persisted is not None
    assert persisted.name == "Unidade Principal"


async def test_post_units_returns_409_when_cnpj_already_exists(
    client: AsyncClient,
) -> None:
    await _create_unit(
        client,
        cnpj="11222333000181",
    )

    response = await client.post(
        "/api/v1/units",
        json=make_create_unit_request(
            cnpj="11222333000181",
        ).model_dump(mode="json"),
        headers=_admin_headers(),
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CONFLICT"


async def test_post_units_returns_422_when_cnpj_invalid(
    client: AsyncClient,
) -> None:
    payload = make_create_unit_request(
        cnpj="11222333000181",
    ).model_dump(mode="json")

    payload["cnpj"] = "12345678000019"

    response = await client.post(
        "/api/v1/units",
        json=payload,
        headers=_admin_headers(),
    )

    assert response.status_code == 422


async def test_post_units_returns_401_when_authentication_missing(
    client: AsyncClient,
) -> None:
    payload = make_create_unit_request(
        cnpj="11222333000181",
    ).model_dump(mode="json")

    response = await client.post(
        "/api/v1/units",
        json=payload,
    )

    assert response.status_code == 401


async def test_get_current_unit_returns_default_unit(
    client: AsyncClient,
) -> None:
    response = await client.get("/api/v1/units/current")

    assert response.status_code == 200

    body = response.json()

    assert body["name"] == "Unidade Principal"
    assert body["cnpj"] == DEFAULT_CNPJ


async def test_get_unit_returns_unit_when_exists(
    client: AsyncClient,
) -> None:
    created = await _create_unit(
        client,
        cnpj="11222333000181",
    )

    response = await client.get(
        f"/api/v1/units/{created['id']}",
        headers=_admin_headers(),
    )

    assert response.status_code == 200
    assert response.json()["cnpj"] == "11222333000181"


async def test_get_unit_returns_404_when_id_not_found(
    client: AsyncClient,
) -> None:
    response = await client.get(
        f"/api/v1/units/{NON_EXISTENT_ID}",
        headers=_admin_headers(),
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


async def test_list_units_returns_paginated_results_when_multiple_exist(
    client: AsyncClient,
) -> None:
    await _create_unit(
        client,
        cnpj="11222333000181",
    )
    await _create_unit(
        client,
        cnpj="33444555000181",
    )
    await _create_unit(
        client,
        cnpj="44555666000181",
    )

    response = await client.get(
        "/api/v1/units?page=1&page_size=2",
        headers=_admin_headers(),
    )

    assert response.status_code == 200

    body = response.json()

    assert body["meta"]["total"] == 4
    assert body["meta"]["total_pages"] == 2
    assert len(body["items"]) == 2


async def test_patch_unit_updates_only_provided_fields(
    client: AsyncClient,
    db: Prisma,
) -> None:
    created = await _create_unit(
        client,
        cnpj="11222333000181",
    )

    response = await client.patch(
        f"/api/v1/units/{created['id']}",
        json={"name": "Unidade Nova"},
        headers=_admin_headers(),
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Unidade Nova"
    assert response.json()["cnpj"] == "11222333000181"

    persisted = await db.unit.find_unique(
        where={"id": created["id"]},
    )

    assert persisted is not None
    assert persisted.name == "Unidade Nova"
    assert persisted.cnpj == "11222333000181"


async def test_patch_unit_returns_404_when_id_not_found(
    client: AsyncClient,
) -> None:
    response = await client.patch(
        f"/api/v1/units/{NON_EXISTENT_ID}",
        json={"name": "X"},
        headers=_admin_headers(),
    )

    assert response.status_code == 404


async def test_patch_unit_returns_409_when_changing_to_existing_cnpj(
    client: AsyncClient,
) -> None:
    await _create_unit(
        client,
        cnpj="11222333000181",
    )

    other = await _create_unit(
        client,
        cnpj="33444555000181",
    )

    response = await client.patch(
        f"/api/v1/units/{other['id']}",
        json={"cnpj": "11222333000181"},
        headers=_admin_headers(),
    )

    assert response.status_code == 409


async def test_delete_unit_returns_204_and_marks_deleted_at_in_db(
    client: AsyncClient,
    db: Prisma,
) -> None:
    created = await _create_unit(
        client,
        cnpj="11222333000181",
    )

    response = await client.delete(
        f"/api/v1/units/{created['id']}",
        headers=_admin_headers(),
    )

    assert response.status_code == 204

    persisted = await db.unit.find_unique(
        where={"id": created["id"]},
    )

    assert persisted is not None
    assert persisted.deletedAt is not None


async def test_delete_unit_returns_404_when_id_not_found(
    client: AsyncClient,
) -> None:
    response = await client.delete(
        f"/api/v1/units/{NON_EXISTENT_ID}",
        headers=_admin_headers(),
    )

    assert response.status_code == 404


async def test_get_unit_returns_404_when_unit_soft_deleted(
    client: AsyncClient,
) -> None:
    created = await _create_unit(
        client,
        cnpj="11222333000181",
    )

    await client.delete(
        f"/api/v1/units/{created['id']}",
        headers=_admin_headers(),
    )

    response = await client.get(
        f"/api/v1/units/{created['id']}",
        headers=_admin_headers(),
    )

    assert response.status_code == 404


async def test_list_units_excludes_soft_deleted_records(
    client: AsyncClient,
) -> None:
    keep = await _create_unit(
        client,
        cnpj="11222333000181",
    )

    drop = await _create_unit(
        client,
        cnpj="33444555000181",
    )

    await client.delete(
        f"/api/v1/units/{drop['id']}",
        headers=_admin_headers(),
    )

    response = await client.get(
        "/api/v1/units",
        headers=_admin_headers(),
    )

    body = response.json()

    assert body["meta"]["total"] == 2
    assert any(item["id"] == keep["id"] for item in body["items"])
    assert all(item["id"] != drop["id"] for item in body["items"])
