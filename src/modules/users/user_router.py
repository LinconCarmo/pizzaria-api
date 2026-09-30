from fastapi import APIRouter

from src.modules.auth.auth_controller import router as auth_v1
from src.modules.users.controllers.v1.user_controller import router as users_v1

router = APIRouter()
router.include_router(users_v1)
router.include_router(auth_v1)
__all__ = ["router"]
