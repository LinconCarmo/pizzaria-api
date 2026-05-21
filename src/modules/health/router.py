from fastapi import APIRouter

from src.modules.health.controllers.v1.health import router as health_v1
from src.modules.health.controllers.v1.root import router as root_v1

router = APIRouter()
router.include_router(health_v1)
router.include_router(root_v1)

__all__ = ["router"]
