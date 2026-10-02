from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from src.shared.types import PaginationMeta

UF = Literal[
    "AC",
    "AL",
    "AP",
    "AM",
    "BA",
    "CE",
    "DF",
    "ES",
    "GO",
    "MA",
    "MT",
    "MS",
    "MG",
    "PA",
    "PB",
    "PR",
    "PE",
    "PI",
    "RJ",
    "RN",
    "RS",
    "RO",
    "RR",
    "SC",
    "SP",
    "SE",
    "TO",
]


def validate_cnpj(value: str) -> str:
    if len(value) != 14 or not value.isdigit():
        raise ValueError("CNPJ must contain 14 digits")

    if value == value[0] * 14:
        raise ValueError("Invalid CNPJ")

    first_weights = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    second_weights = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]

    first_sum = sum(
        int(digit) * weight for digit, weight in zip(value[:12], first_weights, strict=True)
    )

    first_remainder = first_sum % 11
    first_digit = 0 if first_remainder < 2 else 11 - first_remainder

    if int(value[12]) != first_digit:
        raise ValueError("Invalid CNPJ")

    second_sum = sum(
        int(digit) * weight for digit, weight in zip(value[:13], second_weights, strict=True)
    )

    second_remainder = second_sum % 11
    second_digit = 0 if second_remainder < 2 else 11 - second_remainder

    if int(value[13]) != second_digit:
        raise ValueError("Invalid CNPJ")

    return value


class _BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class CreateUnitRequest(BaseModel):
    name: str = Field(
        ...,
        min_length=1,
        max_length=120,
        description="Unit name",
        examples=["Main Unit"],
    )
    cnpj: str = Field(
        ...,
        description="Unit CNPJ",
        examples=["12345678000195"],
    )
    email: EmailStr = Field(
        ...,
        description="Unit email",
        examples=["contato@pizzaria.com"],
    )
    phone: str = Field(
        ...,
        min_length=1,
        max_length=20,
        description="Unit phone",
        examples=["41999999999"],
    )

    street: str = Field(
        ...,
        min_length=1,
        max_length=120,
        description="Unit street address",
        examples=["Rua XV de Novembro"],
    )
    number: str = Field(
        ...,
        min_length=1,
        max_length=20,
        description="Unit street number",
        examples=["100"],
    )
    neighborhood: str = Field(
        ...,
        min_length=1,
        max_length=120,
        description="Unit neighborhood",
        examples=["Centro"],
    )
    city: str = Field(
        ...,
        min_length=1,
        max_length=120,
        description="Unit city",
        examples=["Curitiba"],
    )
    state: UF = Field(
        ...,
        min_length=2,
        max_length=2,
        description="Unit state (UF)",
        examples=["PR"],
    )
    zip: str = Field(
        ...,
        min_length=1,
        max_length=10,
        description="Unit ZIP code",
        examples=["80000000"],
    )

    @field_validator("cnpj")
    @classmethod
    def validate_cnpj_field(cls, value: str) -> str:
        return validate_cnpj(value)

    @field_validator("zip")
    @classmethod
    def normalize_zip(cls, value: str) -> str:
        return value.replace("-", "")


class UpdateUnitRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = Field(default=None, min_length=1, max_length=120)
    cnpj: str | None = Field(default=None)
    email: EmailStr | None = Field(default=None)
    phone: str | None = Field(default=None, min_length=1, max_length=20)
    street: str | None = Field(
        default=None,
        min_length=1,
        max_length=120,
        description="Unit street address",
        examples=["Rua XV de Novembro"],
    )
    number: str | None = Field(
        default=None,
        min_length=1,
        max_length=20,
        description="Unit street number",
        examples=["100"],
    )
    neighborhood: str | None = Field(
        default=None,
        min_length=1,
        max_length=120,
        description="Unit neighborhood",
        examples=["Centro"],
    )
    city: str | None = Field(
        default=None,
        min_length=1,
        max_length=120,
        description="Unit city",
        examples=["Curitiba"],
    )
    state: UF | None = Field(
        default=None,
        min_length=2,
        max_length=2,
        description="Unit state (UF)",
        examples=["PR"],
    )
    zip: str | None = Field(
        default=None,
        min_length=1,
        max_length=10,
        description="Unit ZIP code",
        examples=["80000000"],
    )
    is_active: bool | None = None

    @field_validator("cnpj")
    @classmethod
    def validate_cnpj_field(cls, value: str | None) -> str | None:
        if value is None:
            return None

        return validate_cnpj(value)

    @field_validator("zip")
    @classmethod
    def normalize_zip(cls, value: str | None) -> str | None:
        if value is None:
            return None

        return value.replace("-", "")


class UnitResponse(_BaseSchema):
    id: UUID
    name: str
    cnpj: str
    email: EmailStr
    phone: str
    street: str
    number: str
    neighborhood: str
    city: str
    state: str
    zip: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class UnitListResponse(BaseModel):
    items: list[UnitResponse] = Field(..., description="Units in current page")
    meta: PaginationMeta = Field(..., description="Pagination metadata")


class UnitSummaryResponse(BaseModel):
    name: str
    phone: str
    street: str
    number: str
    neighborhood: str
    city: str
    state: str
    zip: str
