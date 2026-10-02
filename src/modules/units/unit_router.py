from fastapi import APIRouter

from src.modules.units.controllers.v1.unit_controller import router as units_v1

router = APIRouter()
router.include_router(units_v1)
__all__ = ["router"]
