from fastapi import APIRouter

from .service import HealthService

router = APIRouter(
    prefix="/health",
    tags=["Health"]
)


@router.get("/")
def health_check():
    return HealthService.check()