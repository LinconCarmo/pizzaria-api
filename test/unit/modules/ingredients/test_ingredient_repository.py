from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from prisma import Prisma
from prisma.actions import IngredientActions
from prisma.enums import IngredientUnit as PrismaIngredientUnit
from prisma.errors import UniqueViolationError
from prisma.models import Ingredient

from src.core.exceptions import ConflictError
from src.modules.ingredients.ingredient_repository import IngredientRepository
from src.modules.ingredients.ingredient_schema import IngredientUnit
from test.factories import (
    DEFAULT_INGREDIENT_UNIT_ID,
    make_ingredient_row,
)

UNIT_ID = DEFAULT_INGREDIENT_UNIT_ID
NON_EXISTENT_INGREDIENT_ID = UUID("00000000-0000-4000-8000-000000000099")
PRISMA_ERROR_DATA = {"user_facing_error": {"message": "prisma error"}}


def _row() -> MagicMock:
    row = MagicMock(spec=Ingredient)
    row.model_dump.return_value = make_ingredient_row()
    return row


@pytest.fixture
def ingredients() -> AsyncMock:
    return AsyncMock(spec=IngredientActions)


@pytest.fixture
def repository(ingredients: AsyncMock) -> IngredientRepository:
    db = AsyncMock(spec=Prisma)
    db.ingredient = ingredients
    return IngredientRepository(db)


async def _create_ingredient(repository: IngredientRepository) -> dict[str, object]:
    return await repository.create(
        name="Mussarela",
        unit=IngredientUnit.KG,
        unit_id=UNIT_ID,
        cost_per_unit=Decimal("35.50"),
        stock_min=Decimal("2.000"),
        stock_quantity=Decimal("10.000"),
    )


async def test_create_persists_fields_and_converts_unit_enum(
    repository: IngredientRepository, ingredients: AsyncMock
) -> None:
    ingredients.create.return_value = _row()

    result = await _create_ingredient(repository)

    assert ingredients.create.call_args.kwargs["data"] == {
        "name": "Mussarela",
        "unit": PrismaIngredientUnit.KG,
        "unitId": str(UNIT_ID),
        "costPerUnit": Decimal("35.50"),
        "stockMin": Decimal("2.000"),
        "stockQuantity": Decimal("10.000"),
    }
    assert result["name"] == "Mussarela"


async def test_create_raises_conflict_when_name_exists_in_unit(
    repository: IngredientRepository, ingredients: AsyncMock
) -> None:
    ingredients.create.side_effect = UniqueViolationError(PRISMA_ERROR_DATA)

    with pytest.raises(ConflictError):
        await _create_ingredient(repository)


async def test_get_by_id_returns_none_when_ingredient_missing(
    repository: IngredientRepository, ingredients: AsyncMock
) -> None:
    ingredients.find_first.return_value = None

    result = await repository.get_by_id(NON_EXISTENT_INGREDIENT_ID)

    assert result is None
    assert ingredients.find_first.call_args.kwargs["where"] == {
        "id": str(NON_EXISTENT_INGREDIENT_ID),
        "deletedAt": None,
    }


async def test_get_by_name_filters_active_ingredient_by_unit_by_default(
    repository: IngredientRepository, ingredients: AsyncMock
) -> None:
    ingredients.find_first.return_value = _row()

    result = await repository.get_by_name("Mussarela", UNIT_ID)

    assert ingredients.find_first.call_args.kwargs["where"] == {
        "name": "Mussarela",
        "unitId": str(UNIT_ID),
        "isActive": True,
        "deletedAt": None,
    }
    assert result is not None
    assert result["name"] == "Mussarela"


async def test_get_by_name_uses_requested_active_state(
    repository: IngredientRepository, ingredients: AsyncMock
) -> None:
    ingredients.find_first.return_value = None

    result = await repository.get_by_name("Mussarela", UNIT_ID, is_active=False)

    assert ingredients.find_first.call_args.kwargs["where"]["isActive"] is False
    assert result is None
