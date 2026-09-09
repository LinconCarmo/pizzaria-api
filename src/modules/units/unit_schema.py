from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


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
    street: str = Field(..., min_length=1, max_length=120)
    number: str = Field(..., min_length=1, max_length=20)
    neighborhood: str = Field(..., min_length=1, max_length=120)
    city: str = Field(..., min_length=1, max_length=120)
    state: str = Field(..., min_length=2, max_length=2)
    zip: str = Field(..., min_length=1, max_length=10)

    @field_validator("cnpj")
    @classmethod
    def validate_cnpj_field(cls, value: str) -> str:
        return validate_cnpj(value)


class UpdateUnitRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    cnpj: str | None = Field(default=None)
    email: EmailStr | None = Field(default=None)
    phone: str | None = Field(default=None, min_length=1, max_length=20)
    street: str | None = Field(default=None, min_length=1, max_length=120)
    number: str | None = Field(default=None, min_length=1, max_length=20)
    neighborhood: str | None = Field(default=None, min_length=1, max_length=120)
    city: str | None = Field(default=None, min_length=1, max_length=120)
    state: str | None = Field(default=None, min_length=2, max_length=2)
    zip: str | None = Field(default=None, min_length=1, max_length=10)
    is_active: bool | None = None

    @field_validator("cnpj")
    @classmethod
    def validate_cnpj_field(cls, value: str | None) -> str | None:
        if value is None:
            return None

        return validate_cnpj(value)


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


class PaginationMeta(BaseModel):
    page: int = Field(..., ge=1, description="Current page number", examples=[1])
    page_size: int = Field(..., ge=1, le=100, description="Items per page", examples=[20])
    total: int = Field(..., ge=0, description="Total matching units", examples=[45])
    total_pages: int = Field(..., ge=0, description="Total number of pages", examples=[3])


class UnitListResponse(BaseModel):
    items: list[UnitResponse] = Field(..., description="Units in current page")
    meta: PaginationMeta = Field(..., description="Pagination metadata")
