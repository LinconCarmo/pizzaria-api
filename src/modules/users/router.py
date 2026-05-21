from fastapi import APIRouter

from src.modules.users.controllers.v1.users import router as users_v1

router = APIRouter()
router.include_router(users_v1)

__all__ = ["router"]
