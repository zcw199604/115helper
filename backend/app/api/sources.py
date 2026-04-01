"""同步任务管理接口。"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.common import ApiResponse
from app.schemas.run import RunRead
from app.schemas.source import SourceCreate, SourceRead, SourceUpdate, ToggleTaskRequest
from app.services.run_service import RunService
from app.services.source_service import SourceService

router = APIRouter(prefix="/tasks", tags=["tasks"])
legacy_router = APIRouter(prefix="/sources", tags=["sources"])


def _list_tasks(db: Session):
    service = SourceService(db)
    return ApiResponse(data=service.list_sources())


@router.get("", response_model=ApiResponse[list[SourceRead]])
def list_tasks(db: Session = Depends(get_db)):
    return _list_tasks(db)


@legacy_router.get("", response_model=ApiResponse[list[SourceRead]])
def list_sources(db: Session = Depends(get_db)):
    return _list_tasks(db)


@router.get("/{source_id}", response_model=ApiResponse[SourceRead])
@legacy_router.get("/{source_id}", response_model=ApiResponse[SourceRead])
def get_task(source_id: int, db: Session = Depends(get_db)):
    service = SourceService(db)
    source = service.get_source_or_404(source_id)
    return ApiResponse(data=service._to_read_model(source))


@router.post("", response_model=ApiResponse[SourceRead])
@legacy_router.post("", response_model=ApiResponse[SourceRead])
def create_task(payload: SourceCreate, db: Session = Depends(get_db)):
    service = SourceService(db)
    return ApiResponse(data=service.create_source(payload))


@router.put("/{source_id}", response_model=ApiResponse[SourceRead])
@legacy_router.put("/{source_id}", response_model=ApiResponse[SourceRead])
def update_task(source_id: int, payload: SourceUpdate, db: Session = Depends(get_db)):
    service = SourceService(db)
    return ApiResponse(data=service.update_source(source_id, payload))


@router.post("/{source_id}/toggle", response_model=ApiResponse[SourceRead])
def toggle_task(source_id: int, payload: ToggleTaskRequest, db: Session = Depends(get_db)):
    service = SourceService(db)
    return ApiResponse(data=service.toggle_enabled(source_id, payload.enabled))


@router.delete("/{source_id}", response_model=ApiResponse[dict])
@legacy_router.delete("/{source_id}", response_model=ApiResponse[dict])
def delete_task(source_id: int, db: Session = Depends(get_db)):
    service = SourceService(db)
    service.delete_source(source_id)
    return ApiResponse(data={"deleted": True})


@router.get("/{source_id}/runs", response_model=ApiResponse[list[RunRead]])
def list_task_runs(source_id: int, db: Session = Depends(get_db)):
    service = RunService(db)
    return ApiResponse(data=service.list_runs(source_id=source_id))
