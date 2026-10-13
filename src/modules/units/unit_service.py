from uuid import UUID

from src.core.exceptions import BadRequestError, NotFoundError
from src.modules.units.unit_repository import UnitRepositoryProtocol
from src.modules.units.unit_schema import (
    CreateUnitRequest,
    UnitListResponse,
    UnitResponse,
    UnitSummaryResponse,
    UpdateUnitRequest,
)
from src.shared.types import PaginationMeta


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
        include_inactive: bool = False,
    ) -> UnitListResponse:
        items_raw, total = await self._repository.list_paginated(
            page=page,
            page_size=page_size,
            include_inactive=include_inactive,
        )

        return UnitListResponse(
            items=[self._to_response(item) for item in items_raw],
            meta=PaginationMeta.build(page=page, page_size=page_size, total=total),
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

        if not updates:
            raise BadRequestError("At least one field must be provided for update")

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

    def _to_summary_response(
        self,
        raw: dict[str, object],
    ) -> UnitSummaryResponse:
        return UnitSummaryResponse.model_validate(
            {
                "name": raw["name"],
                "phone": raw["phone"],
                "street": raw["street"],
                "number": raw["number"],
                "neighborhood": raw["neighborhood"],
                "city": raw["city"],
                "state": raw["state"],
                "zip": raw["zip"],
            }
        )

    async def get_current(self) -> UnitSummaryResponse:
        """Return the first non-deleted unit as the current unit for the MVP."""
        items_raw, _ = await self._repository.list_paginated(
            page=1,
            page_size=1,
            include_inactive=False,
        )

        if not items_raw:
            raise NotFoundError("Current unit not found")

        return self._to_summary_response(items_raw[0])
