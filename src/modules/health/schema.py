from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    status: str = Field(..., description="Service health status", examples=["ok"])

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{"status": "ok"}],
        },
    )


class RootResponse(BaseModel):
    message: str = Field(..., description="API greeting message", examples=["Pizzaria API"])

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{"message": "Pizzaria API"}],
        },
    )
