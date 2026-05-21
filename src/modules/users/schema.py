from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserRole(StrEnum):
    CUSTOMER = "CUSTOMER"
    STAFF = "STAFF"
    ADMIN = "ADMIN"


class _BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class CreateUserRequest(BaseModel):
    email: EmailStr = Field(..., description="User email address", examples=["ana@example.com"])
    name: str = Field(
        ..., min_length=1, max_length=120, description="Full name", examples=["Ana Silva"]
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Plain-text password (hashed before persistence)",
        examples=["s3nh@forte"],
    )
    role: UserRole = Field(
        default=UserRole.CUSTOMER, description="User role", examples=["CUSTOMER"]
    )


class UpdateUserRequest(BaseModel):
    email: EmailStr | None = Field(
        default=None, description="New email address", examples=["ana.maria@example.com"]
    )
    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=120,
        description="New full name",
        examples=["Ana Maria"],
    )
    password: str | None = Field(
        default=None,
        min_length=8,
        max_length=128,
        description="New plain-text password (hashed before persistence)",
        examples=["n0v@s3nh@"],
    )
    role: UserRole | None = Field(default=None, description="New user role", examples=["STAFF"])


class UserResponse(_BaseSchema):
    id: UUID = Field(
        ...,
        description="User ID (UUID)",
        examples=["7c9e6679-7425-40de-944b-e07fc1f90ae7"],
    )
    email: EmailStr = Field(..., description="User email address", examples=["ana@example.com"])
    name: str = Field(..., description="Full name", examples=["Ana Silva"])
    role: UserRole = Field(..., description="User role", examples=["CUSTOMER"])
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class PaginationMeta(_BaseSchema):
    page: int = Field(..., ge=1, description="Current page number", examples=[1])
    page_size: int = Field(..., ge=1, le=100, description="Items per page", examples=[20])
    total: int = Field(..., ge=0, description="Total matching items", examples=[45])
    total_pages: int = Field(..., ge=0, description="Total number of pages", examples=[3])


class UserListResponse(_BaseSchema):
    items: list[UserResponse] = Field(..., description="Users in the current page")
    meta: PaginationMeta = Field(..., description="Pagination metadata")
