from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from src.shared.types import BaseSchema


class IngredientUnit(StrEnum):
    KG = "KG"
    G = "G"
    L = "L"
    ML = "ML"
    UN = "UN"


def _normalize_ingredient_name(value: str) -> str:
    value = value.strip()

    if not value:
        raise ValueError("Name cannot be empty")

    return value[0].upper() + value[1:].lower()


class CreateIngredientRequest(BaseModel):
    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Ingredient name",
        examples=["Mussarela"],
    )
    unit: IngredientUnit = Field(
        description="Unit of measure used to track the ingredient's stock",
        examples=[IngredientUnit.KG],
    )
    cost_per_unit: Decimal = Field(
        ...,
        ge=0,
        description="Cost per unit of measurement",
        examples=["35.50"],
    )
    stock_min: Decimal = Field(
        default=Decimal("0"),
        ge=0,
        description="Minimum stock quantity",
        examples=["2.000"],
    )
    stock_quantity: Decimal = Field(
        default=Decimal("0"),
        ge=0,
        description="Current stock quantity",
        examples=["10.000"],
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        return _normalize_ingredient_name(value)


class UpdateIngredientRequest(BaseModel):
    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="Updated ingredient name",
        examples=["Mussarela"],
    )
    unit: IngredientUnit | None = Field(
        default=None,
        description="Updated unit of measure",
        examples=[IngredientUnit.KG],
    )
    cost_per_unit: Decimal | None = Field(
        default=None,
        ge=0,
        description="Updated cost per unit of measurement",
        examples=["35.50"],
    )
    stock_min: Decimal | None = Field(
        default=None,
        ge=0,
        description="Updated minimum stock quantity",
        examples=["2.000"],
    )
    stock_quantity: Decimal | None = Field(
        default=None,
        ge=0,
        description="Updated current stock quantity",
        examples=["10.000"],
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _normalize_ingredient_name(value)


_IngredientName = Annotated[
    str, Field(description="Ingredient Name", examples=["Mussarela"], min_length=1, max_length=100)
]
_IngredientCostPerUnit = Annotated[
    Decimal, Field(ge=0, description="Cost per measurement unit", examples=["35.50"])
]
_IngredientStockMin = Annotated[
    Decimal, Field(ge=0, description="Minimum stock quantity", examples=["2.000"])
]
_IngredientStockQuantity = Annotated[
    Decimal, Field(ge=0, description="Current stock quantity", examples=["10.000"])
]


class IngredientResponse(BaseSchema):
    id: UUID = Field(
        ...,
        description="Ingredient ID (UUID)",
        examples=["7c9e6679-7425-40de-944b-e07fc1f90ae7"],
    )
    name: _IngredientName
    unit: IngredientUnit = Field(
        ...,
        description="Unit of measure used to track the ingredient's stock",
        examples=[IngredientUnit.KG],
    )
    unit_id: UUID = Field(
        ...,
        description="Business unit ID (UUID)",
        examples=["7c9e6679-7425-40de-944b-e07fc1f90ae7"],
    )
    cost_per_unit: _IngredientCostPerUnit
    stock_min: _IngredientStockMin
    stock_quantity: _IngredientStockQuantity
    is_active: bool = Field(..., description="Whether ingredient is active", examples=[True])
    created_at: datetime = Field(
        ..., description="Creation timestamp", examples=["2026-05-20T12:00:00Z"]
    )
    updated_at: datetime = Field(
        ..., description="Last update timestamp", examples=["2026-05-20T12:00:00Z"]
    )
