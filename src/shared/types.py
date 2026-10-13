from typing import Self

from pydantic import BaseModel, ConfigDict, Field


class BaseSchema(BaseModel):
    """Base dos `*Response`: aceita objetos com atributos além de dicts."""

    model_config = ConfigDict(from_attributes=True)


class PaginationMeta(BaseSchema):
    page: int = Field(..., ge=1, description="Current page number", examples=[1])
    page_size: int = Field(..., ge=1, le=100, description="Items per page", examples=[20])
    total: int = Field(..., ge=0, description="Total matching items", examples=[45])
    total_pages: int = Field(..., ge=0, description="Total number of pages", examples=[3])

    @classmethod
    def build(cls, *, page: int, page_size: int, total: int) -> Self:
        total_pages = (total + page_size - 1) // page_size if total else 0
        return cls(page=page, page_size=page_size, total=total, total_pages=total_pages)
