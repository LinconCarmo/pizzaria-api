from decimal import Decimal
from typing import Protocol, cast
from uuid import UUID

from prisma import Prisma, types
from prisma.enums import IngredientUnit as PrismaIngredientUnit
from prisma.errors import UniqueViolationError

from src.core.exceptions import ConflictError
from src.modules.ingredients.ingredient_schema import IngredientUnit


class IngredientRepositoryProtocol(Protocol):
    async def create(
        self,
        *,
        name: str,
        unit: IngredientUnit,
        unit_id: UUID,
        cost_per_unit: Decimal,
        stock_min: Decimal,
        stock_quantity: Decimal,
    ) -> dict[str, object]: ...

    async def get_by_id(self, ingredient_id: UUID) -> dict[str, object] | None: ...

    async def get_by_name(
        self, ingredient_name: str, unit_id: UUID, is_active: bool = True
    ) -> dict[str, object] | None: ...


class IngredientRepository:
    def __init__(self, db: Prisma) -> None:
        self._db = db

    async def create(
        self,
        *,
        name: str,
        unit: IngredientUnit,
        unit_id: UUID,
        cost_per_unit: Decimal,
        stock_min: Decimal,
        stock_quantity: Decimal,
    ) -> dict[str, object]:

        data: types.IngredientCreateInput = {
            "name": name,
            "unit": PrismaIngredientUnit(unit.value),
            "unitId": str(unit_id),
            "costPerUnit": cost_per_unit,
            "stockMin": stock_min,
            "stockQuantity": stock_quantity,
        }

        try:
            created = await self._db.ingredient.create(data=data)
        except UniqueViolationError as exc:
            raise ConflictError(f"Ingredient{name} already exists in {unit_id}") from exc
        return cast(dict[str, object], created.model_dump())

    async def get_by_id(self, ingredient_id: UUID) -> dict[str, object] | None:
        where: types.IngredientWhereInput = {"id": str(ingredient_id), "deletedAt": None}
        row = await self._db.ingredient.find_first(where=where)
        if row is None:
            return None
        return cast(dict[str, object], row.model_dump())

    async def get_by_name(
        self, ingredient_name: str, unit_id: UUID, is_active: bool = True
    ) -> dict[str, object] | None:

        where: types.IngredientWhereInput = {
            "name": ingredient_name,
            "unitId": str(unit_id),
            "isActive": is_active,
            "deletedAt": None,
        }
        row = await self._db.ingredient.find_first(where=where)
        if row is None:
            return None
        return cast(dict[str, object], row.model_dump())
