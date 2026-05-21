from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserRole(StrEnum):
    CUSTOMER = "CUSTOMER"
    STAFF = "STAFF"
    ADMIN = "ADMIN"


class _BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class CreateUserRequest(BaseModel):
    email: EmailStr
    name: str = Field(..., min_length=1, max_length=120)
    password: str = Field(..., min_length=8, max_length=128)
    role: UserRole = UserRole.CUSTOMER

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "email": "ana@example.com",
                    "name": "Ana Silva",
                    "password": "s3nh@forte",
                    "role": "CUSTOMER",
                },
            ],
        },
    )


class UpdateUserRequest(BaseModel):
    email: EmailStr | None = None
    name: str | None = Field(default=None, min_length=1, max_length=120)
    password: str | None = Field(default=None, min_length=8, max_length=128)
    role: UserRole | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{"name": "Ana Maria"}],
        },
    )


class UserResponse(_BaseSchema):
    id: int = Field(..., gt=0)
    email: EmailStr
    name: str
    role: UserRole
    created_at: datetime
    updated_at: datetime


class PaginationMeta(_BaseSchema):
    page: int = Field(..., ge=1)
    page_size: int = Field(..., ge=1, le=100)
    total: int = Field(..., ge=0)
    total_pages: int = Field(..., ge=0)


class UserListResponse(_BaseSchema):
    items: list[UserResponse]
    meta: PaginationMeta
