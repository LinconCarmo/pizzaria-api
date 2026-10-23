from decimal import Decimal

import pytest
from pydantic import ValidationError

from src.modules.ingredients.ingredient_schema import (
    CreateIngredientRequest,
    IngredientUnit,
    UpdateIngredientRequest,
)
from test.factories import make_create_ingredient_request


def test_create_ingredient_request_accepts_valid_data() -> None:
    result = make_create_ingredient_request()

    assert result.name == "Mussarela"
    assert result.unit is IngredientUnit.KG


def test_create_ingredient_request_normalizes_name() -> None:
    result = make_create_ingredient_request(name="  MUSSARELA  ")

    assert result.name == "Mussarela"


@pytest.mark.parametrize("name", ["", "   "])
def test_create_ingredient_request_rejects_empty_name(name: str) -> None:
    with pytest.raises(ValidationError):
        make_create_ingredient_request(name=name)


@pytest.mark.parametrize("unit", ["INVALID", "kg"])
def test_create_ingredient_request_rejects_invalid_unit(unit: str) -> None:
    with pytest.raises(ValidationError):
        CreateIngredientRequest.model_validate(
            {
                "name": "Mussarela",
                "unit": unit,
                "cost_per_unit": Decimal("1.00"),
            }
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("cost_per_unit", Decimal("-0.01")),
        ("stock_min", Decimal("-0.001")),
        ("stock_quantity", Decimal("-0.001")),
    ],
)
def test_create_ingredient_request_rejects_negative_values(field: str, value: Decimal) -> None:
    payload = make_create_ingredient_request().model_dump()
    payload[field] = value

    with pytest.raises(ValidationError):
        CreateIngredientRequest.model_validate(payload)


def test_update_ingredient_request_accepts_partial_data() -> None:
    result = UpdateIngredientRequest(name="Parmesão")

    assert result.name == "Parmesão"
    assert result.unit is None
    assert result.cost_per_unit is None
