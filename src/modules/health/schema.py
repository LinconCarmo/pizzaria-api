from pydantic import BaseModel, ConfigDict


class HealthResponse(BaseModel):
    status: str

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{"status": "ok"}],
        },
    )
