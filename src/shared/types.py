from pydantic import BaseModel, ConfigDict, Field


class _BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class PaginationMeta(_BaseSchema):
    page: int = Field(..., ge=1, description="Current page number", examples=[1])
    page_size: int = Field(..., ge=1, le=100, description="Items per page", examples=[20])
    total: int = Field(..., ge=0, description="Total matching items", examples=[45])
    total_pages: int = Field(..., ge=0, description="Total number of pages", examples=[3])
