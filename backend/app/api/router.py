"""聚合所有 API 路由。"""

from fastapi import APIRouter

from app.api.runs import router as runs_router
from app.api.settings import router as settings_router
from app.api.sources import legacy_router as sources_legacy_router
from app.api.sources import router as tasks_router

api_router = APIRouter()
api_router.include_router(tasks_router)
api_router.include_router(sources_legacy_router)
api_router.include_router(runs_router)
api_router.include_router(settings_router)
