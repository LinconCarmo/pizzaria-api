from uuid import UUID

from src.core.exceptions import NotFoundError
from src.modules.units.unit_repository import UnitRepositoryProtocol
from src.modules.units.unit_schema import (
    CreateUnitRequest,
    PaginationMeta,
    UnitListResponse,
    UnitResponse,
    UpdateUnitRequest,
)


class UnitService:
    def __init__(self, repository: UnitRepositoryProtocol) -> None:
        self._repository = repository

    async def create(self, data: CreateUnitRequest) -> UnitResponse:
        raw = await self._repository.create(
            name=data.name,
            cnpj=data.cnpj,
            email=data.email,
            phone=data.phone,
            street=data.street,
            number=data.number,
            neighborhood=data.neighborhood,
            city=data.city,
            state=data.state,
            zip=data.zip,
        )
        return self._to_response(raw)

    async def get_by_id(self, unit_id: UUID) -> UnitResponse:
        raw = await self._repository.get_by_id(unit_id)

        if raw is None:
            raise NotFoundError(f"Unit {unit_id} not found")

        return self._to_response(raw)

    async def list_paginated(
        self,
        page: int,
        page_size: int,
    ) -> UnitListResponse:
        items_raw, total = await self._repository.list_paginated(
            page=page,
            page_size=page_size,
        )

        total_pages = (total + page_size - 1) // page_size if total else 0

        return UnitListResponse(
            items=[self._to_response(item) for item in items_raw],
            meta=PaginationMeta(
                page=page,
                page_size=page_size,
                total=total,
                total_pages=total_pages,
            ),
        )

    async def update(
        self,
        unit_id: UUID,
        data: UpdateUnitRequest,
    ) -> UnitResponse:
        existing = await self._repository.get_by_id(unit_id)

        if existing is None:
            raise NotFoundError(f"Unit {unit_id} not found")

        updates = data.model_dump(exclude_unset=True)

        raw = await self._repository.update(
            unit_id,
            **updates,
        )

        return self._to_response(raw)

    async def delete(self, unit_id: UUID) -> None:
        existing = await self._repository.get_by_id(unit_id)

        if existing is None:
            raise NotFoundError(f"Unit {unit_id} not found")

        await self._repository.soft_delete(unit_id)

    def _to_response(self, raw: dict[str, object]) -> UnitResponse:
        return UnitResponse.model_validate(
            {
                "id": raw["id"],
                "name": raw["name"],
                "cnpj": raw["cnpj"],
                "email": raw["email"],
                "phone": raw["phone"],
                "street": raw["street"],
                "number": raw["number"],
                "neighborhood": raw["neighborhood"],
                "city": raw["city"],
                "state": raw["state"],
                "zip": raw["zip"],
                "is_active": raw["isActive"],
                "created_at": raw["createdAt"],
                "updated_at": raw["updatedAt"],
            }
        )

    async def get_current(self) -> UnitResponse:
        items_raw, _ = await self._repository.list_paginated(
            page=1,
            page_size=1,
        )

        if not items_raw:
            raise NotFoundError("Current unit not found")

        return self._to_response(items_raw[0])
