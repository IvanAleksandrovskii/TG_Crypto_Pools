from core import settings
from .v1 import router as v1_router
from fastapi import APIRouter


api_router = APIRouter()
api_router.include_router(v1_router, prefix=settings.api.v1)
