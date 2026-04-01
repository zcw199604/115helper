"""FastAPI 应用入口，负责启动数据库、注册路由并托管前端静态资源。"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app import models  # noqa: F401
from app.api.router import api_router
from app.core.config import get_settings
from app.db.base import Base
from app.db.compat import ensure_schema_compat
from app.db.session import SessionLocal, engine
from app.models.source import SyncSource
from app.services.scheduler_service import scheduler_service

settings = get_settings()
app = FastAPI(title=settings.app_name)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

frontend_dist = Path(settings.frontend_dist)
frontend_assets = frontend_dist / 'assets'


@app.on_event("startup")
def on_startup() -> None:
    """应用启动时初始化数据库并恢复调度任务。"""

    Base.metadata.create_all(bind=engine)
    ensure_schema_compat(engine)
    db = SessionLocal()
    try:
        sources = db.query(SyncSource).all()
        scheduler_service.sync_source_jobs(sources)
    finally:
        db.close()


@app.get("/healthz")
def healthz() -> dict[str, str]:
    """健康检查接口。"""

    return {"status": "ok"}


app.include_router(api_router, prefix=settings.api_prefix)

if frontend_assets.exists():
    app.mount('/assets', StaticFiles(directory=frontend_assets), name='frontend-assets')


@app.get('/', include_in_schema=False)
def serve_index():
    """返回前端入口页面。"""

    index_file = frontend_dist / 'index.html'
    if index_file.exists():
        return FileResponse(index_file)
    return {"message": "frontend dist not found"}


@app.get('/{full_path:path}', include_in_schema=False)
def serve_spa(full_path: str):
    """为前端路由提供 SPA 回退。"""

    if full_path.startswith(('api/', 'healthz', 'assets/')):
        return {"detail": "Not Found"}
    index_file = frontend_dist / 'index.html'
    if index_file.exists():
        return FileResponse(index_file)
    return {"message": "frontend dist not found"}
