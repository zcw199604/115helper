"""任务运行接口。"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.enums import TriggerType
from app.schemas.common import ApiResponse
from app.schemas.run import RunCreateRequest, RunDetail, RunRead
from app.schemas.task_log import TaskLogRead
from app.services.async_run_executor import async_run_executor
from app.services.run_service import RunService
from app.services.scheduler_service import scheduler_service
from app.services.task_log_stream_service import task_log_stream_service

router = APIRouter(tags=['runs'])


@router.post('/tasks/{source_id}/run', response_model=ApiResponse[RunRead])
@router.post('/sources/{source_id}/run', response_model=ApiResponse[RunRead])
def run_source(source_id: int, payload: RunCreateRequest = RunCreateRequest(), db: Session = Depends(get_db)):
    service = RunService(db)
    service.ensure_source_idle(source_id)
    if not scheduler_service.reserve_source(source_id):
        raise RuntimeError('任务预留失败')
    try:
        run = service.create_run(source_id, TriggerType.RETRY if payload.retry_failed_only else TriggerType.MANUAL)
        async_run_executor.submit_run(run.id)
        return ApiResponse(data=service._to_read_model(run))
    except Exception:
        scheduler_service.release_source(source_id)
        raise


@router.get('/runs', response_model=ApiResponse[list[RunRead]])
def list_runs(source_id: int | None = None, db: Session = Depends(get_db)):
    service = RunService(db)
    return ApiResponse(data=service.list_runs(source_id=source_id))


@router.get('/runs/{run_id}', response_model=ApiResponse[RunDetail])
def get_run_detail(run_id: int, db: Session = Depends(get_db)):
    service = RunService(db)
    return ApiResponse(data=service.get_run_detail(run_id))


@router.get('/runs/{run_id}/logs', response_model=ApiResponse[list[TaskLogRead]])
def get_run_logs(run_id: int, db: Session = Depends(get_db)):
    service = RunService(db)
    return ApiResponse(data=service.list_logs(run_id))


@router.get('/runs/{run_id}/logs/stream')
async def stream_run_logs(run_id: int, request: Request, db: Session = Depends(get_db)):
    service = RunService(db)
    service.list_logs(run_id)

    async def event_generator():
        queue = await task_log_stream_service.subscribe(run_id)
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    chunk = await asyncio.wait_for(queue.get(), timeout=10)
                    yield chunk
                except asyncio.TimeoutError:
                    yield f"event: heartbeat\ndata: {{"run_id": {run_id}}}\n\n"
        finally:
            await task_log_stream_service.unsubscribe(run_id, queue)

    return StreamingResponse(event_generator(), media_type='text/event-stream', headers={'Cache-Control': 'no-cache', 'Connection': 'keep-alive', 'X-Accel-Buffering': 'no'})


@router.post('/runs/{run_id}/retry', response_model=ApiResponse[RunRead])
def retry_run(run_id: int, db: Session = Depends(get_db)):
    service = RunService(db)
    retry = service.retry_run_async(run_id)
    async_run_executor.submit_run(retry.id)
    return ApiResponse(data=retry)


@router.post('/runs/{run_id}/cancel', response_model=ApiResponse[RunRead])
def cancel_run(run_id: int, db: Session = Depends(get_db)):
    service = RunService(db)
    return ApiResponse(data=service.cancel_run(run_id))
