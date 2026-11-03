from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from src.modules.ingredients.ingredient_schema import (
    CreateIngredientRequest,
    IngredientUnit,
)

NOW = datetime(2026, 10, 23, 12, 0, tzinfo=UTC)
DEFAULT_INGREDIENT_ID = UUID("00000000-0000-4000-8000-000000000001")
DEFAULT_INGREDIENT_UNIT_ID = UUID("00000000-0000-4000-8000-000000000002")


def make_ingredient_row(
    *,
    id: UUID = DEFAULT_INGREDIENT_ID,
    name: str = "Mussarela",
    unit: IngredientUnit = IngredientUnit.KG,
    unit_id: UUID = DEFAULT_INGREDIENT_UNIT_ID,
    cost_per_unit: Decimal = Decimal("35.50"),
    stock_quantity: Decimal = Decimal("10.000"),
    stock_min: Decimal = Decimal("2.000"),
    is_active: bool = True,
    created_at: datetime = NOW,
    updated_at: datetime = NOW,
    deleted_at: datetime | None = None,
) -> dict[str, object]:
    return {
        "id": str(id),
        "name": name,
        "unit": unit.value,
        "unitId": str(unit_id),
        "costPerUnit": cost_per_unit,
        "stockQuantity": stock_quantity,
        "stockMin": stock_min,
        "isActive": is_active,
        "createdAt": created_at,
        "updatedAt": updated_at,
        "deletedAt": deleted_at,
    }


def make_create_ingredient_request(
    *,
    name: str = "Mussarela",
    unit: IngredientUnit = IngredientUnit.KG,
    cost_per_unit: Decimal = Decimal("35.50"),
    stock_min: Decimal = Decimal("2.000"),
    stock_quantity: Decimal = Decimal("10.000"),
) -> CreateIngredientRequest:
    return CreateIngredientRequest(
        name=name,
        unit=unit,
        cost_per_unit=cost_per_unit,
        stock_min=stock_min,
        stock_quantity=stock_quantity,
    )
