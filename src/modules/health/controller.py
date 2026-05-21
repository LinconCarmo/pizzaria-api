from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from src.modules.health.service import HealthService

router = APIRouter(
    prefix="/health",
    tags=["health"],
)


@router.get("/live")
async def live():
    return {
        "status": "alive",
    }


@router.get("")
async def health():
    result = await HealthService.check()

    if result["status"] == "error":
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=result,
        )

    return result