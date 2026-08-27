from fastapi import APIRouter

from app.core.config import settings

from .classes import router as classes_router

router = APIRouter(prefix=settings.api.v1_prefix)
router.include_router(classes_router)

__all__ = ["router"]
