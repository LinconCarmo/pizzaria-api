from datetime import UTC, datetime
from typing import Protocol, cast
from uuid import UUID

from prisma import Prisma, types
from prisma.errors import RecordNotFoundError, UniqueViolationError

from src.core.exceptions import ConflictError, NotFoundError


class UnitRepositoryProtocol(Protocol):
    async def create(
        self,
        *,
        name: str,
        cnpj: str,
        email: str,
        phone: str,
        street: str,
        number: str,
        neighborhood: str,
        city: str,
        state: str,
        zip: str,
    ) -> dict[str, object]: ...

    async def get_by_id(self, unit_id: UUID) -> dict[str, object] | None: ...

    async def list_paginated(
        self,
        *,
        page: int,
        page_size: int,
    ) -> tuple[list[dict[str, object]], int]: ...

    async def update(
        self,
        unit_id: UUID,
        *,
        name: str | None = None,
        cnpj: str | None = None,
        email: str | None = None,
        phone: str | None = None,
        street: str | None = None,
        number: str | None = None,
        neighborhood: str | None = None,
        city: str | None = None,
        state: str | None = None,
        zip: str | None = None,
        is_active: bool | None = None,
    ) -> dict[str, object]: ...

    async def soft_delete(self, unit_id: UUID) -> None: ...


class UnitRepository:
    def __init__(self, db: Prisma) -> None:
        self._db = db

    async def create(
        self,
        *,
        name: str,
        cnpj: str,
        email: str,
        phone: str,
        street: str,
        number: str,
        neighborhood: str,
        city: str,
        state: str,
        zip: str,
    ) -> dict[str, object]:

        data: types.UnitCreateInput = {
            "name": name,
            "cnpj": cnpj,
            "email": email,
            "phone": phone,
            "street": street,
            "number": number,
            "neighborhood": neighborhood,
            "city": city,
            "state": state,
            "zip": zip,
        }

        try:
            created = await self._db.unit.create(data=data)
        except UniqueViolationError as exc:
            raise ConflictError(f"Unit with CNPJ {cnpj} already exists") from exc
        return cast(dict[str, object], created.model_dump())

    async def get_by_id(self, unit_id: UUID) -> dict[str, object] | None:
        where: types.UnitWhereInput = {"id": str(unit_id), "deletedAt": None}
        row = await self._db.unit.find_first(where=where)
        if row is None:
            return None
        return cast(dict[str, object], row.model_dump())

    async def list_paginated(
        self,
        *,
        page: int,
        page_size: int,
    ) -> tuple[list[dict[str, object]], int]:

        where: types.UnitWhereInput = {"deletedAt": None}

        skip = (page - 1) * page_size
        order: types.UnitOrderByInput = {"createdAt": "asc"}

        items = await self._db.unit.find_many(
            where=where,
            skip=skip,
            take=page_size,
            order=order,
        )

        total = await self._db.unit.count(where=where)
        return [item.model_dump() for item in items], total

    async def update(
        self,
        unit_id: UUID,
        *,
        name: str | None = None,
        cnpj: str | None = None,
        email: str | None = None,
        phone: str | None = None,
        street: str | None = None,
        number: str | None = None,
        neighborhood: str | None = None,
        city: str | None = None,
        state: str | None = None,
        zip: str | None = None,
        is_active: bool | None = None,
    ) -> dict[str, object]:
        data: types.UnitUpdateInput = {}
        if name is not None:
            data["name"] = name
        if cnpj is not None:
            data["cnpj"] = cnpj
        if email is not None:
            data["email"] = email
        if phone is not None:
            data["phone"] = phone
        if street is not None:
            data["street"] = street
        if number is not None:
            data["number"] = number
        if neighborhood is not None:
            data["neighborhood"] = neighborhood
        if city is not None:
            data["city"] = city
        if state is not None:
            data["state"] = state
        if zip is not None:
            data["zip"] = zip
        if is_active is not None:
            data["isActive"] = is_active

        try:
            row = await self._db.unit.update(where={"id": str(unit_id)}, data=data)
        except UniqueViolationError as exc:
            raise ConflictError(f"Unit with CNPJ {cnpj} already exists") from exc
        if row is None:
            raise NotFoundError(f"Unit {unit_id} not found")
        return cast(dict[str, object], row.model_dump())

    async def soft_delete(self, unit_id: UUID) -> None:
        data: types.UnitUpdateInput = {"deletedAt": datetime.now(UTC)}
        try:
            await self._db.unit.update(
                where={"id": str(unit_id)},
                data=data,
            )
        except RecordNotFoundError as exc:
            raise NotFoundError(f"Unit {unit_id} not found") from exc
