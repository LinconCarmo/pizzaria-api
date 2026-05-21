from fastapi import APIRouter

from src.modules.health.schema import RootResponse

router = APIRouter(tags=["Info"])


@router.get("/", summary="API root")
async def root() -> RootResponse:
    return RootResponse(message="Pizzaria API")
